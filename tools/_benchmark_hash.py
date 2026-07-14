"""
tools/_benchmark_hash.py — one-shot benchmark (NOT part of the tool).

Answers a single design question: can the fast *partial signature* used by
:func:`tools.models.video.compute_content_hash` shrink its head/tail window from
1 MiB to 256 KiB without losing de-duplication accuracy — and how much faster is
it on real files?

Only *partial* signatures (``size + head + tail``) are ever computed — the full
file is never read. For each configured window size it reports:

* wall-clock time, throughput, bytes read (smaller window => less I/O), and
* collision safety: number of distinct signatures vs. number of files. The
  largest window (1 MiB) is used as the reference identity; a *new merge* is any
  group of files that the smaller 256 KiB window collapses into one signature but
  the 1 MiB window keeps apart. Zero new merges => 256 KiB is as accurate as
  1 MiB on this dataset.

Usage::

    python -m tools._benchmark_hash [ROOT] [LIMIT]
    python tools/_benchmark_hash.py D:\\ 999
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections import defaultdict

VIDEO_EXTENSIONS = {
    ".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".ts", ".m2ts", ".3gp", ".ogv", ".mts",
}

KIB = 1 << 10
MIB = 1 << 20

# Candidate head/tail window sizes to compare (largest is the reference).
CHUNK_SIZES = {
    "256KiB": 256 * KIB,
    "1MiB": 1 * MIB,
}
REFERENCE_LABEL = "1MiB"


def find_videos(root, limit):
    found = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS:
                found.append(os.path.join(dirpath, f))
                if len(found) >= limit:
                    return found
    return found


def partial_hash(path, size, chunk, algorithm="sha256"):
    """Mirror of compute_content_hash(partial=True) with a configurable window.

    Returns ``(digest, bytes_read)``. The full file is never read.
    """
    h = hashlib.new(algorithm)
    h.update(str(size).encode())
    read = 0
    with open(path, "rb") as f:
        head = f.read(chunk)
        h.update(head)
        read += len(head)
        if size > chunk * 2:
            f.seek(-chunk, os.SEEK_END)
            tail = f.read(chunk)
            h.update(tail)
            read += len(tail)
    return "p:" + h.hexdigest(), read


def groups_of(sig_by_path):
    """Map signature -> list of paths sharing it."""
    groups = defaultdict(list)
    for path, sig in sig_by_path.items():
        groups[sig].append(path)
    return groups


def new_merges_vs_reference(sig_by_path, ref_sig_by_path):
    """Files the small window collapses that the reference window keeps apart.

    Returns ``(new_merge_groups, examples)``. A new merge is a small-window
    duplicate group whose members do NOT all share one reference signature.
    """
    count = 0
    examples = []
    for sig, paths in groups_of(sig_by_path).items():
        if len(paths) < 2:
            continue
        ref_ids = {ref_sig_by_path[p] for p in paths}
        if len(ref_ids) > 1:
            count += 1
            if len(examples) < 5:
                examples.append([os.path.basename(p) for p in paths])
    return count, examples


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "D:\\"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 999

    print(f"Walking {root} for up to {limit} videos ...", flush=True)
    videos = find_videos(root, limit)
    print(f"Found {len(videos)} video files.\n", flush=True)
    if not videos:
        return

    sizes = {}
    ok = []
    for p in videos:
        try:
            sizes[p] = os.path.getsize(p)
            ok.append(p)
        except OSError:
            pass
    total_bytes = sum(sizes.values())
    print(f"Readable: {len(ok)} files, {total_bytes / MIB:,.0f} MiB total on disk.\n")

    # -- compute every window, largest first so we have the reference ready --
    labels_by_size = sorted(CHUNK_SIZES.items(), key=lambda kv: kv[1], reverse=True)
    sig_maps = {}
    results = {}
    for label, chunk in labels_by_size:
        print(f"--- partial window = {label} ({chunk} bytes) ---", flush=True)
        t0 = time.perf_counter()
        sig_by_path = {}
        read_total = 0
        for p in ok:
            try:
                sig, read = partial_hash(p, sizes[p], chunk)
            except OSError:
                sig, read = f"__err__{p}", 0
            sig_by_path[p] = sig
            read_total += read
        secs = time.perf_counter() - t0
        sig_maps[label] = sig_by_path

        groups = groups_of(sig_by_path)
        distinct = len(groups)
        dup_groups = sum(1 for ps in groups.values() if len(ps) > 1)
        thru = (read_total / MIB / secs) if secs else 0.0
        results[label] = {
            "chunk_bytes": chunk,
            "seconds": round(secs, 4),
            "bytes_read": read_total,
            "mib_read": round(read_total / MIB, 1),
            "read_mib_per_s": round(thru, 1),
            "ms_per_file": round(secs / len(ok) * 1000, 3),
            "distinct_signatures": distinct,
            "duplicate_groups": dup_groups,
        }
        print(
            f"  time    : {secs:.3f}s  ({secs / len(ok) * 1000:.2f} ms/file)\n"
            f"  read     : {read_total / MIB:,.1f} MiB  ({thru:,.0f} MiB/s)\n"
            f"  distinct : {distinct} of {len(ok)} files "
            f"({dup_groups} duplicate group(s))\n"
        )

    # -- collision safety of 256KiB relative to the 1MiB reference --
    ref = sig_maps.get(REFERENCE_LABEL)
    for label in results:
        if label == REFERENCE_LABEL or ref is None:
            results[label]["new_merges_vs_1MiB"] = 0
            continue
        n, ex = new_merges_vs_reference(sig_maps[label], ref)
        results[label]["new_merges_vs_1MiB"] = n
        results[label]["new_merge_examples"] = ex
        print(f"--- {label} collision check vs {REFERENCE_LABEL} reference ---")
        print(f"  new merges (files {label} collapses but {REFERENCE_LABEL} keeps apart): {n}")
        for grp in ex:
            print(f"      ! {grp}")
        print()

    # -- verdict --
    a, b = "256KiB", "1MiB"
    if a in results and b in results:
        speedup = results[b]["seconds"] / results[a]["seconds"] if results[a]["seconds"] else 0
        io_ratio = results[b]["bytes_read"] / results[a]["bytes_read"] if results[a]["bytes_read"] else 0
        same_distinct = results[a]["distinct_signatures"] == results[b]["distinct_signatures"]
        no_new_merges = results[a]["new_merges_vs_1MiB"] == 0
        print("=== VERDICT ===")
        print(f"  256KiB is {speedup:.2f}x faster and reads {io_ratio:.1f}x less data than 1MiB.")
        print(f"  Same distinct-identity count as 1MiB : {same_distinct}")
        print(f"  256KiB introduces no new merges      : {no_new_merges}")
        if same_distinct and no_new_merges:
            print("  => SAFE to switch to 256KiB for this dataset.")
        else:
            print("  => NOT safe: 256KiB loses de-dup accuracy on this dataset.")
        print()

    out = {
        "root": root,
        "files": len(ok),
        "total_disk_mib": round(total_bytes / MIB, 1),
        "reference_window": REFERENCE_LABEL,
        "windows": results,
    }
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_benchmark_hash.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote report -> {out_path}")


if __name__ == "__main__":
    main()
