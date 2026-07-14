"""
tools/tests/test_memory_store.py — Tests for the in-memory dict store, and
interchangeability with the SQLite store via the IStore interface.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from tools.models.video import Video
from tools.storage.memory_store import InMemoryStore
from tools.storage.sqlite_store import SQLiteStore
from tools.storage.interfaces import IStore


def make_video(idx: int) -> Video:
    return Video(
        path=f"D:/clips/video_{idx}.mp4",
        name=f"video_{idx}.mp4",
        content_hash=f"hash{idx:04d}",
        width=1280,
        height=720,
        video_codec="hevc",
    )


class TestInMemoryStore:
    def test_save_and_get(self):
        store = InMemoryStore()
        v = make_video(1)
        store.save(v)
        assert store.get("videos", v.content_hash)["name"] == "video_1.mp4"

    def test_save_many_and_all(self):
        store = InMemoryStore()
        store.save_many([make_video(i) for i in range(3)])
        assert len(store.all("videos")) == 3
        assert len(store) == 3

    def test_get_returns_copy(self):
        store = InMemoryStore()
        store.save(make_video(1))
        row = store.get("videos", "hash0001")
        row["name"] = "mutated"
        assert store.get("videos", "hash0001")["name"] == "video_1.mp4"

    def test_none_key_rejected(self):
        store = InMemoryStore()
        with pytest.raises(ValueError):
            store.save(Video(path="D:/x.mp4", name="x.mp4", content_hash=None))


@pytest.mark.parametrize("factory", [InMemoryStore, lambda: SQLiteStore(":memory:")])
def test_backends_are_interchangeable(factory):
    """Both stores honour the same IStore contract and round-trip identically."""
    store: IStore = factory()
    v = make_video(9)
    store.save(v)
    row = store.get("videos", v.content_hash)
    assert Video.from_dict(row).name == v.name
    if hasattr(store, "close"):
        store.close()
