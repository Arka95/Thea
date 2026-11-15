"""
tools/_explore_metadata.py — one-shot exploration script (NOT part of the tool).

Recursively walks a root directory, samples up to N video files, runs ffprobe on
each, and reports the de-duplicated union of every metadata key seen (format-level,
stream-level, and container tags). Also reports whether any embedded hash/checksum
tag exists, to inform the primary-key decision.
"""

import os
import sys
import json
import subprocess
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import static_ffmpeg
static_ffmpeg.add_paths()
import shutil

FFPROBE = shutil.which("ffprobe")

VIDEO_EXTENSIONS = {
    ".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".ts", ".m2ts", ".3gp", ".ogv", ".mts",
}

HASH_HINTS = ("hash", "md5", "sha", "crc", "checksum", "digest")


def find_videos(root, limit):
    found = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS:
                found.append(os.path.join(dirpath, f))
                if len(found) >= limit:
                    return found
    return found


def ffprobe_json(path):
    try:
        out = subprocess.run(
            [FFPROBE, "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", path],
            capture_output=True, text=True, timeout=60,
        )
        if out.returncode != 0 or not out.stdout:
            return None
        return json.loads(out.stdout)
    except Exception:
        return None


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "D:\\"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 1000

    print(f"Walking {root} for up to {limit} videos ...", flush=True)
    videos = find_videos(root, limit)
    print(f"Found {len(videos)} video files.", flush=True)
    if not videos:
        return

    format_keys = Counter()
    stream_keys_by_type = defaultdict(Counter)
    format_tag_keys = Counter()
    stream_tag_keys = Counter()
    hash_examples = []
    ok = 0

    def work(p):
        return p, ffprobe_json(p)

    with ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 4) * 2)) as ex:
        futures = [ex.submit(work, p) for p in videos]
        for i, fut in enumerate(as_completed(futures), 1):
            p, data = fut.result()
            if not data:
                continue
            ok += 1
            fmt = data.get("format", {})
            for k in fmt:
                if k != "tags":
                    format_keys[k] += 1
            for tk, tv in (fmt.get("tags") or {}).items():
                format_tag_keys[tk.lower()] += 1
                if any(h in tk.lower() for h in HASH_HINTS) and len(hash_examples) < 10:
                    hash_examples.append((os.path.basename(p), tk, str(tv)[:60]))
            for st in data.get("streams", []):
                ctype = st.get("codec_type", "unknown")
                for k in st:
                    if k != "tags":
                        stream_keys_by_type[ctype][k] += 1
                for tk, tv in (st.get("tags") or {}).items():
                    stream_tag_keys[tk.lower()] += 1
                    if any(h in tk.lower() for h in HASH_HINTS) and len(hash_examples) < 10:
                        hash_examples.append((os.path.basename(p), tk, str(tv)[:60]))
            if i % 200 == 0:
                print(f"  probed {i}/{len(videos)} ...", flush=True)

    print(f"\nSuccessfully probed: {ok}/{len(videos)}\n")

    def dump(title, counter):
        print(f"=== {title} ({len(counter)} distinct) ===")
        for k, c in counter.most_common():
            print(f"  {c:5d}  {k}")
        print()

    dump("FORMAT-LEVEL KEYS", format_keys)
    for ctype, counter in stream_keys_by_type.items():
        dump(f"STREAM KEYS [codec_type={ctype}]", counter)
    dump("FORMAT TAG KEYS", format_tag_keys)
    dump("STREAM TAG KEYS", stream_tag_keys)

    print("=== EMBEDDED HASH/CHECKSUM TAGS FOUND ===")
    if hash_examples:
        for fn, tk, tv in hash_examples:
            print(f"  {fn}: {tk} = {tv}")
    else:
        print("  NONE - no video carried an embedded hash/checksum tag.")
    print()

    result = {
        "root": root,
        "sampled": len(videos),
        "probed_ok": ok,
        "format_keys": dict(format_keys),
        "stream_keys_by_type": {k: dict(v) for k, v in stream_keys_by_type.items()},
        "format_tag_keys": dict(format_tag_keys),
        "stream_tag_keys": dict(stream_tag_keys),
        "hash_examples": hash_examples,
    }
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_metadata_union.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Wrote union report -> {out_path}")


if __name__ == "__main__":
    main()
