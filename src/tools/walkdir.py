"""
tools/walkdir.py — multithreaded recursive discovery of video files.

Walks every subfolder of a root directory concurrently (up to ``max_threads``
worker threads, capped at 10) and yields only files whose extension is a known
video container. Each discovered directory is a unit of work: a worker lists it
with :func:`os.scandir`, records the video files it contains, and enqueues its
subdirectories for other workers to pick up. This keeps all threads busy on a
deep tree instead of serialising on a single :func:`os.walk`.

Two levels of API:

* :func:`find_video_paths` — just the paths (fast, no stat/hash).
* :func:`walk_and_store` — build :class:`~tools.models.video.Video` records
  (filesystem identity + partial content hash) and dump them into any
  :class:`~tools.storage.interfaces.IStore`.

CLI::

    python -m tools.walkdir [ROOT] [LIMIT]
    python -m tools.walkdir E:\\ --geocode --infer-loc
    python tools/walkdir.py D:\\ 100
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import List, Optional

from tools.catalogue import enrich_locale, merge_video, migrate_catalogue
from tools.geocoding import default_gazetteer, default_geocoder
from tools.models.video import Video, compute_content_hash
from tools.storage.interfaces import IStore
from tools.storage.sqlite_store import SQLiteStore
from tools.video_meta_strategy import populate_video, run_ffprobe
from utils.settings import get_catalogue_path

VIDEO_EXTENSIONS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".mpg",
    ".mpeg",
    ".ts",
    ".m2ts",
    ".3gp",
    ".ogv",
    ".mts",
}

MAX_THREADS = 10


def find_video_paths(
    root: str,
    max_threads: int = MAX_THREADS,
    extensions: Optional[set] = None,
    limit: Optional[int] = None,
    on_file: Optional[Callable[[str], None]] = None,
    on_error: Callable[[str, OSError], None] | None = None,
) -> List[str]:
    """Recursively find video files under ``root`` using worker threads.

    Args:
        root: Directory to walk. Every subfolder is visited.
        max_threads: Number of worker threads (clamped to ``[1, 10]``).
        extensions: Set of lowercase extensions (incl. dot) to keep. Defaults to
            :data:`VIDEO_EXTENSIONS`.
        limit: Stop once this many video files have been collected. Selection
            depends on concurrent traversal order.
        on_file: Optional callback invoked with each video path as it is found.
        on_error: Optional callback for unreadable directories or entries.

    Returns:
        List of absolute video file paths.
    """
    exts = extensions if extensions is not None else VIDEO_EXTENSIONS
    workers = max(1, min(max_threads, MAX_THREADS))

    dir_q: "queue.Queue[Optional[str]]" = queue.Queue()
    dir_q.put(root)

    results: List[str] = []
    results_lock = threading.Lock()
    stop = threading.Event()

    def worker() -> None:
        while True:
            d = dir_q.get()
            try:
                if d is None:  # sentinel
                    return
                if stop.is_set():
                    continue
                try:
                    with os.scandir(d) as it:
                        for entry in it:
                            if stop.is_set():
                                break
                            try:
                                if entry.is_dir(follow_symlinks=False):
                                    dir_q.put(entry.path)
                                elif entry.is_file(follow_symlinks=False):
                                    ext = os.path.splitext(entry.name)[1].lower()
                                    if ext in exts:
                                        with results_lock:
                                            if limit is not None and len(results) >= limit:
                                                stop.set()
                                                break
                                            results.append(entry.path)
                                        if on_file is not None:
                                            on_file(entry.path)
                            except OSError as error:
                                if on_error is not None:
                                    on_error(entry.path, error)
                                continue
                except OSError as error:
                    if on_error is not None:
                        on_error(d, error)
            finally:
                dir_q.task_done()

    threads = [
        threading.Thread(target=worker, name=f"walkdir-{i}", daemon=True) for i in range(workers)
    ]
    for t in threads:
        t.start()

    dir_q.join()  # blocks until every enqueued directory has been processed
    for _ in threads:
        dir_q.put(None)  # release the workers blocked on get()
    for t in threads:
        t.join()

    return results


def build_video(
    path: str,
    compute_hash: bool = True,
    partial: bool = True,
    probe: bool = False,
    geocoder=None,
    place_gazetteer=None,
    on_error: Callable[[str, OSError], None] | None = None,
    store: IStore | None = None,
) -> Optional[Video]:
    """Build a :class:`Video` with filesystem identity fields.

    Returns ``None`` if the file cannot be stat'd. When ``compute_hash`` is
    ``True`` a content hash is computed (partial signature by default) and used
    as the primary key, which is required for storage. When ``probe`` is ``True``
    the file is run through ffprobe and :func:`populate_video` fills device,
    location, resolution, fps and creation-time fields (see
    :mod:`tools.video_meta_strategy`). If ``geocoder`` (a
    :class:`tools.geocoding.Geocoder`) is given, ``country`` is derived from GPS;
    if ``place_gazetteer`` is given, videos without GPS fall back to an
    approximate location inferred from a place name in the folder path.
    With a ``store``, merge existing metadata before falling back to filesystem
    creation time, so an unprobed reindex cannot replace a recording timestamp.
    """
    try:
        st = os.stat(path)
    except OSError as error:
        if on_error is not None:
            on_error(path, error)
        return None

    content_hash = None
    if compute_hash:
        try:
            content_hash = compute_content_hash(path, partial=partial)
        except OSError as error:
            if on_error is not None:
                on_error(path, error)
            return None

    video = Video(
        path=path,
        name=os.path.basename(path),
        content_hash=content_hash,
        directory=os.path.dirname(path),
        extension=os.path.splitext(path)[1].lower() or None,
        size_bytes=st.st_size,
    )

    if probe:
        probe_json = run_ffprobe(path)
        if probe_json:
            populate_video(video, probe_json, geocoder=geocoder, place_gazetteer=place_gazetteer)

    if store is not None:
        video = merge_video(store.get("videos", video.content_hash), video)
    if not video.creation_time:
        video.creation_time = datetime.fromtimestamp(
            getattr(st, "st_birthtime", st.st_ctime), UTC
        ).isoformat()
    return video


def walk_and_store(
    root: str,
    store: IStore,
    max_threads: int = MAX_THREADS,
    limit: Optional[int] = None,
    compute_hash: bool = True,
    partial: bool = True,
    probe: bool = False,
    geocoder=None,
    place_gazetteer=None,
    report: dict | None = None,
) -> int:
    """Walk ``root``, build :class:`Video` records, and dump them into ``store``.

    Returns the number of records saved. Note that the store de-duplicates by
    ``content_hash`` (its primary key), so byte-identical files collapse into a
    single row — the return value counts save attempts of distinct paths. Pass
    ``probe=True`` to also extract device/location/resolution metadata, a
    ``geocoder`` to reverse-geocode ``country`` from GPS, and a
    ``place_gazetteer`` to infer approximate location from folder-path names.
    """
    errors = []
    errors_lock = threading.Lock()

    def record_error(path, error, stage="scan"):
        with errors_lock:
            errors.append({"path": path, "stage": stage, "error_type": type(error).__name__})

    paths = sorted(
        find_video_paths(
            root,
            max_threads=max_threads,
            limit=limit,
            on_error=record_error if report is not None else None,
        )
    )
    saved = 0
    files = []
    directories = {}
    seen_hashes = set()
    for p in paths:
        if report is not None:
            directory = directories.setdefault(
                os.path.dirname(p), {"discovered": 0, "saved": 0, "skipped": 0}
            )
            directory["discovered"] += 1
        video = build_video(
            p,
            compute_hash=compute_hash,
            partial=partial,
            probe=probe,
            geocoder=geocoder,
            place_gazetteer=place_gazetteer,
            on_error=(
                (lambda path, error: record_error(path, error, "read"))
                if report is not None
                else None
            ),
            store=store,
        )
        if video is None:
            if report is not None:
                directory["skipped"] += 1
                files.append({"path": p, "status": "skipped"})
            continue
        if place_gazetteer is not None:
            video = enrich_locale(video, place_gazetteer)
        store.save(video)
        saved += 1
        if report is not None:
            directory["saved"] += 1
            files.append(
                {
                    "path": p,
                    "status": "saved",
                    "content_hash": video.content_hash,
                    "duplicate_in_scan": video.content_hash in seen_hashes,
                }
            )
            seen_hashes.add(video.content_hash)
    if report is not None:
        report.update(
            discovered=len(paths),
            saved=saved,
            skipped=len(paths) - saved,
            unique_contents=len(seen_hashes),
            duplicates=saved - len(seen_hashes),
            complete=not errors and saved == len(paths),
            error_count=len(errors),
            errors=errors,
            directories=[
                {"directory": path, **counts} for path, counts in sorted(directories.items())
            ],
            files=files,
        )
    return saved


def add_index_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the shared ``thea index`` / ``thea-index`` arguments."""
    parser.add_argument("root", nargs="?", default="D:\\")
    parser.add_argument("limit", nargs="?", type=int)
    parser.add_argument(
        "--report-path", help="Write a new JSON audit with every discovered path and outcome."
    )
    parser.add_argument("--probe", action="store_true", help="Read embedded metadata with ffprobe.")
    parser.add_argument("--geocode", action="store_true", help="Resolve GPS to country offline.")
    parser.add_argument(
        "--infer-loc", action="store_true", help="Infer missing GPS from folder names."
    )


def index_videos(
    root: str,
    limit: int | None = None,
    probe: bool = False,
    geocode: bool = False,
    infer_loc: bool = False,
    report_path: str | None = None,
) -> dict:
    """Index videos, reporting this scan separately from existing catalogue rows."""
    root = os.path.abspath(root)
    if not os.path.exists(root):
        raise FileNotFoundError(f"Index root does not exist: {root}")
    if not os.path.isdir(root):
        raise NotADirectoryError(f"Index root is not a directory: {root}")
    if limit is not None and limit <= 0:
        raise ValueError("Index limit must be positive.")
    db = get_catalogue_path()
    if report_path:
        report_path = os.path.abspath(report_path)
        if db and os.path.normcase(report_path) == os.path.normcase(os.path.abspath(db)):
            raise ValueError("Index database and audit report must have different paths.")
        if os.path.exists(report_path):
            raise FileExistsError(f"Index audit already exists: {report_path}")
    probe = probe or geocode or infer_loc
    geocoder = default_geocoder() if geocode else None
    place_gazetteer = default_gazetteer() if infer_loc else None

    scan = {
        "root": root,
        "limit": limit,
        "limited": limit is not None,
        "probe": probe,
        "started_at": datetime.now(UTC).isoformat(),
    }
    schema = migrate_catalogue()
    with SQLiteStore(db) as store:
        saved = walk_and_store(
            root,
            store,
            limit=limit,
            probe=probe,
            geocoder=geocoder,
            place_gazetteer=place_gazetteer,
            report=scan,
        )
        rows = store.all("videos")
    scan["finished_at"] = datetime.now(UTC).isoformat()
    scan["distinct_in_store"] = len(rows)
    if report_path:
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "x", encoding="utf-8") as output:
            json.dump(scan, output, indent=2, ensure_ascii=False)
    summary = {key: value for key, value in scan.items() if key != "files"}
    summary["errors"] = scan["errors"][:8]
    return {
        "saved": saved,
        "distinct": len(rows),
        "db": db,
        "samples": rows[:8],
        "scan": summary,
        "report_path": report_path,
        "schema": schema,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Index video metadata recursively without modifying source videos."
    )
    add_index_arguments(parser)
    args = parser.parse_args(argv)
    probe = args.probe or args.geocode or args.infer_loc
    print(
        f"Walking {args.root} (up to {MAX_THREADS} threads, limit={args.limit}, "
        f"probe={probe}, geocode={args.geocode}, infer_loc={args.infer_loc}) ...",
        flush=True,
    )
    print(f"Index storage     : {get_catalogue_path()}")
    from main import run_command, setup_logging
    from utils.metrics import reset_default_collector

    setup_logging()
    reset_default_collector()
    result = run_command("index", **vars(args))
    saved, rows = result["saved"], result["samples"]
    distinct = result["distinct"]
    scan = result["scan"]
    print(f"Discovered paths   : {scan['discovered']}")
    print(f"Saved paths        : {saved}")
    print(f"Unique this scan   : {scan['unique_contents']}")
    print(f"Skipped paths      : {scan['skipped']}")
    print(f"Scan/read errors   : {scan['error_count']}")
    print(f"Distinct in store  : {distinct} (after content_hash de-dup)")
    print(f"Scan complete      : {scan['complete']} (limited={scan['limited']})")
    if result["report_path"]:
        print(f"Audit report       : {result['report_path']}")

    for row in rows:
        loc = ""
        if row.get("country"):
            loc = f"  {row['country']}"
        elif row.get("latitude") is not None:
            loc = f"  @({row['latitude']},{row['longitude']})"
        res = f"{row.get('width')}x{row.get('height')}" if row.get("width") else "?"
        print(f"  - {row['name'][:34]:34s} {res:>10s}  dev={row.get('device')}{loc}")


if __name__ == "__main__":
    main()
