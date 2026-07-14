"""
tools/tests/test_walkdir.py — Tests for the multithreaded video walker and its
round-trip into the in-memory store.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

import tools.walkdir as walkdir
from tools.walkdir import find_video_paths, build_video, walk_and_store, MAX_THREADS
from tools.storage.memory_store import InMemoryStore


def _make_tree(root, n_videos=100, fanout=5, noise_per_dir=1):
    """Create a nested tree with ``n_videos`` uniquely-sized video files.

    Files are spread across subfolders (``fanout`` per level). Each video gets a
    distinct byte payload so its partial content hash is unique (no accidental
    de-dup). A few non-video files are scattered in as noise.
    """
    made = []
    for i in range(n_videos):
        # deterministic nesting: level0/levelA/... to force recursion + threads
        sub = os.path.join(root, f"d{i % fanout}", f"s{(i // fanout) % fanout}")
        os.makedirs(sub, exist_ok=True)
        ext = [".mp4", ".mkv", ".mov", ".avi", ".webm"][i % 5]
        p = os.path.join(sub, f"video_{i:04d}{ext}")
        with open(p, "wb") as f:
            f.write(f"payload-{i}-".encode() + b"\0" * (i + 1))  # unique content+size
        made.append(p)
        if i % max(1, n_videos // noise_per_dir // 10 or 1) == 0:
            with open(os.path.join(sub, f"note_{i}.txt"), "w") as f:
                f.write("not a video")
    return made


def test_finds_only_videos(tmp_path):
    made = _make_tree(str(tmp_path), n_videos=100)
    found = find_video_paths(str(tmp_path))
    assert len(found) == len(made) == 100
    assert set(found) == set(made)
    assert all(os.path.splitext(p)[1].lower() != ".txt" for p in found)


def test_respects_thread_cap(tmp_path):
    _make_tree(str(tmp_path), n_videos=30)
    # requesting more than the cap must not error and must still find everything
    found = find_video_paths(str(tmp_path), max_threads=50)
    assert len(found) == 30


def test_limit_stops_early(tmp_path):
    _make_tree(str(tmp_path), n_videos=100)
    found = find_video_paths(str(tmp_path), limit=25)
    # approximate under concurrency, but must never exceed by more than a scandir batch
    assert 25 <= len(found) <= 100
    assert len(found) < 100


def test_empty_tree(tmp_path):
    assert find_video_paths(str(tmp_path)) == []


def test_walk_and_store_dumps_100_videos(tmp_path):
    made = _make_tree(str(tmp_path), n_videos=100)
    store = InMemoryStore()
    saved = walk_and_store(str(tmp_path), store, limit=None)

    assert saved == 100
    rows = store.all("videos")
    assert len(rows) == 100  # unique content => no de-dup collapse
    # every stored row is a real video with identity fields populated
    names = {r["name"] for r in rows}
    assert names == {os.path.basename(p) for p in made}
    for r in rows:
        assert r["content_hash"] is not None
        assert r["content_hash"].startswith("p:")  # partial signature
        assert r["size_bytes"] is not None
        assert r["directory"] and r["extension"]


def test_build_video_missing_file(tmp_path):
    assert build_video(str(tmp_path / "nope.mp4")) is None


# --------------------------------------------------------------------------- #
# Integration: the walker must actually apply video_meta_strategy when
# probe=True. Real ffprobe can't read the synthetic test files, so we
# monkeypatch run_ffprobe to return device/location/resolution-shaped blobs
# keyed by filename, then assert those fields land on the stored Video rows.
# --------------------------------------------------------------------------- #

_APPLE_PROBE = {
    "format": {
        "duration": "12.34",
        "tags": {
            "com.apple.quicktime.make": "Apple",
            "com.apple.quicktime.model": "iPhone 15 Plus",
            "com.apple.quicktime.location.ISO6709": "+17.2546+078.6767+509.629/",
            "com.apple.quicktime.location.accuracy.horizontal": "3.8",
            "com.apple.quicktime.creationdate": "2024-09-14T11:48:10+0530",
        },
    },
    "streams": [{
        "codec_type": "video", "width": 3840, "height": 2160,
        "avg_frame_rate": "30000/1001", "r_frame_rate": "30000/1001",
        "tags": {"handler_name": "Core Media Video"},
    }],
}

_PIXEL_PROBE = {
    "format": {
        "duration": "5.0",
        "tags": {
            "com.android.version": "14",
            "location": "+22.6188+88.4170/",
            "location-eng": "+22.6188+88.4170/",
        },
    },
    "streams": [{
        "codec_type": "video", "width": 1920, "height": 1080,
        "avg_frame_rate": "60/1", "r_frame_rate": "60/1", "tags": {},
    }],
}


def _fake_ffprobe_factory(paths):
    """Return a run_ffprobe replacement: Apple blob for the first path (by
    basename), Pixel blob for a 'PXL_'-named path, else None."""
    apple_name = os.path.basename(paths[0])

    def fake_run_ffprobe(path, timeout=60):
        base = os.path.basename(path)
        if base == apple_name:
            return _APPLE_PROBE
        if base.startswith("PXL_"):
            return _PIXEL_PROBE
        return None

    return fake_run_ffprobe


def test_build_video_probe_applies_strategy(tmp_path, monkeypatch):
    made = _make_tree(str(tmp_path), n_videos=3)
    monkeypatch.setattr(walkdir, "run_ffprobe", _fake_ffprobe_factory(made))

    v = build_video(made[0], probe=True)
    assert v is not None
    # strategy-derived fields populated through the walker's build path
    assert v.device == "Apple iPhone 15 Plus"
    assert v.make == "Apple"
    assert v.latitude == 17.2546 and v.longitude == 78.6767 and v.altitude == 509.629
    assert v.location_accuracy_m == pytest.approx(3.8)
    assert v.width == 3840 and v.height == 2160
    assert v.fps == pytest.approx(29.97, abs=0.01)
    assert v.creation_time == "2024-09-14T11:48:10+0530"
    assert v.duration_sec == pytest.approx(12.34)
    # filesystem identity still intact alongside the probed metadata
    assert v.content_hash and v.content_hash.startswith("p:")


def test_build_video_probe_false_skips_strategy(tmp_path, monkeypatch):
    made = _make_tree(str(tmp_path), n_videos=1)
    # even if ffprobe would return data, probe=False must not touch the strategy
    monkeypatch.setattr(walkdir, "run_ffprobe", lambda *a, **k: _APPLE_PROBE)

    v = build_video(made[0], probe=False)
    assert v is not None
    assert v.device is None
    assert v.latitude is None and v.longitude is None
    assert v.width is None and v.height is None and v.fps is None


def test_walk_and_store_probe_populates_strategy_fields(tmp_path, monkeypatch):
    # a Pixel-named file plus generic ones; only the Pixel gets a location blob
    made = _make_tree(str(tmp_path), n_videos=4)
    pixel_dir = os.path.dirname(made[0])
    pixel_path = os.path.join(pixel_dir, "PXL_20240101_101010.mp4")
    with open(pixel_path, "wb") as f:
        f.write(b"pixel-unique-payload")

    monkeypatch.setattr(walkdir, "run_ffprobe", _fake_ffprobe_factory(made))

    store = InMemoryStore()
    saved = walk_and_store(str(tmp_path), store, probe=True)
    assert saved >= 5

    rows = {r["name"]: r for r in store.all("videos")}
    pixel = rows["PXL_20240101_101010.mp4"]
    assert pixel["device"] == "Google Pixel"
    assert pixel["latitude"] == 22.6188 and pixel["longitude"] == 88.417
    assert pixel["width"] == 1920 and pixel["height"] == 1080
    assert pixel["fps"] == pytest.approx(60.0)

    # a non-Apple, non-Pixel file gets no probe data -> strategy fields stay empty
    apple_name = os.path.basename(made[0])
    plain = next(r for n, r in rows.items()
                 if n not in (apple_name, "PXL_20240101_101010.mp4"))
    assert plain["device"] is None
    assert plain["latitude"] is None
