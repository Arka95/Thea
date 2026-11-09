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
    python -m tools.walkdir E:\\ --db E:\\Thea\\videos.sqlite3 --geocode --infer-loc
    python tools/walkdir.py D:\\ 100
"""

from __future__ import annotations

import argparse
import os
import queue
import threading
from contextlib import nullcontext
from typing import Callable, List, Optional

from tools.geocoding import default_gazetteer, default_geocoder
from tools.models.video import Video, compute_content_hash
from tools.storage.interfaces import IStore
from tools.storage.memory_store import InMemoryStore
from tools.storage.sqlite_store import SQLiteStore
from tools.video_meta_strategy import populate_video, run_ffprobe

VIDEO_EXTENSIONS = {
    ".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".ts", ".m2ts", ".3gp", ".ogv", ".mts",
}

MAX_THREADS = 10


def find_video_paths(
    root: str,
    max_threads: int = MAX_THREADS,
    extensions: Optional[set] = None,
    limit: Optional[int] = None,
    on_file: Optional[Callable[[str], None]] = None,
) -> List[str]:
    """Recursively find video files under ``root`` using worker threads.

    Args:
        root: Directory to walk. Every subfolder is visited.
        max_threads: Number of worker threads (clamped to ``[1, 10]``).
        extensions: Set of lowercase extensions (incl. dot) to keep. Defaults to
            :data:`VIDEO_EXTENSIONS`.
        limit: Stop once this many video files have been collected (approximate
            under concurrency — may return a few more than ``limit``).
        on_file: Optional callback invoked with each video path as it is found.

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
                            except OSError:
                                continue
                except OSError:
                    pass
            finally:
                dir_q.task_done()

    threads = [threading.Thread(target=worker, name=f"walkdir-{i}", daemon=True)
               for i in range(workers)]
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
    """
    try:
        st = os.stat(path)
    except OSError:
        return None

    content_hash = None
    if compute_hash:
        try:
            content_hash = compute_content_hash(path, partial=partial)
        except OSError:
            return None

    video = Video(
        path=path,
        name=os.path.basename(path),
        content_hash=content_hash,
        directory=os.path.dirname(path),
        extension=os.path.splitext(path)[1].lower() or None,
        size_bytes=st.st_size,
        modified_time=st.st_mtime,
        created_time=st.st_ctime,
    )

    if probe:
        probe_json = run_ffprobe(path)
        if probe_json:
            populate_video(video, probe_json, geocoder=geocoder,
                           place_gazetteer=place_gazetteer)

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
) -> int:
    """Walk ``root``, build :class:`Video` records, and dump them into ``store``.

    Returns the number of records saved. Note that the store de-duplicates by
    ``content_hash`` (its primary key), so byte-identical files collapse into a
    single row — the return value counts save attempts of distinct paths. Pass
    ``probe=True`` to also extract device/location/resolution metadata, a
    ``geocoder`` to reverse-geocode ``country`` from GPS, and a
    ``place_gazetteer`` to infer approximate location from folder-path names.
    """
    paths = find_video_paths(root, max_threads=max_threads, limit=limit)
    saved = 0
    for p in paths:
        video = build_video(p, compute_hash=compute_hash, partial=partial,
                            probe=probe, geocoder=geocoder,
                            place_gazetteer=place_gazetteer)
        if video is None:
            continue
        store.save(video)
        saved += 1
    return saved


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Index video metadata recursively without modifying source videos."
    )
    parser.add_argument("root", nargs="?", default="D:\\")
    parser.add_argument("limit", nargs="?", type=int)
    parser.add_argument("--db", help="Persist the index in this SQLite database.")
    parser.add_argument("--probe", action="store_true", help="Read embedded metadata with ffprobe.")
    parser.add_argument("--geocode", action="store_true", help="Resolve GPS to country offline.")
    parser.add_argument(
        "--infer-loc", action="store_true", help="Infer missing GPS from folder names."
    )
    args = parser.parse_args(argv)
    probe = args.probe or args.geocode or args.infer_loc
    geocoder = default_geocoder() if args.geocode else None
    place_gazetteer = default_gazetteer() if args.infer_loc else None

    if args.db:
        os.makedirs(os.path.dirname(os.path.abspath(args.db)), exist_ok=True)
        store_context = SQLiteStore(args.db)
    else:
        store_context = nullcontext(InMemoryStore())

    with store_context as store:
        print(
            f"Walking {args.root} (up to {MAX_THREADS} threads, limit={args.limit}, "
            f"probe={probe}, geocode={args.geocode}, infer_loc={args.infer_loc}) ...",
            flush=True,
        )
        print(f"Index storage     : {args.db or 'in-memory (not persisted)'}")
        saved = walk_and_store(
            args.root,
            store,
            limit=args.limit,
            probe=probe,
            geocoder=geocoder,
            place_gazetteer=place_gazetteer,
        )
        rows = store.all("videos")
        print(f"Discovered & saved : {saved} videos")
        print(f"Distinct in store  : {len(rows)} (after content_hash de-dup)")

        for row in rows[:8]:
            loc = ""
            if row.get("country"):
                src = row.get("location_source") or ""
                loc = (
                    f"  {row['country']} ({src})"
                    if src.startswith("path")
                    else f"  {row['country']}"
                )
            elif row.get("latitude") is not None:
                loc = f"  @({row['latitude']},{row['longitude']})"
            res = f"{row.get('width')}x{row.get('height')}" if row.get("width") else "?"
            print(f"  - {row['name'][:34]:34s} {res:>10s}  dev={row.get('device')}{loc}")


if __name__ == "__main__":
    main()
