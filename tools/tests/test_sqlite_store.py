"""
tools/tests/test_sqlite_store.py — Round-trip tests for dumping Video metadata
to and from the SQLite store.
"""

import os
import sqlite3
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from tools.models.video import Video
from tools.storage.sqlite_store import SQLiteStore


def make_video(idx: int = 0, content_hash: str = None) -> Video:
    return Video(
        path=f"D:/clips/video_{idx}.mp4",
        name=f"video_{idx}.mp4",
        content_hash=content_hash or f"hash{idx:04d}",
        directory="D:/clips",
        extension=".mp4",
        size_bytes=1024 * (idx + 1),
        duration_sec=12.5 + idx,
        width=1920,
        height=1080,
        fps=29.97,
        video_codec="h264",
        audio_codec="aac",
        channels=2,
        creation_time="2026-01-01T00:00:00.000000Z",
        raw_metadata={"format": {"nb_streams": 2}, "streams": [{"index": 0}]},
    )


class TestSQLiteRoundTrip:
    def test_save_and_get_memory(self):
        store = SQLiteStore(":memory:")
        v = make_video(1)
        store.save(v)
        row = store.get(v.storage_name, v.content_hash)
        assert row is not None
        assert row["path"] == v.path
        assert row["name"] == v.name
        assert row["width"] == 1920
        assert row["fps"] == pytest.approx(29.97)
        store.close()

    def test_dump_to_and_from_file(self, tmp_path):
        db = str(tmp_path / "videos.db")
        # -- dump TO the db --
        with SQLiteStore(db) as store:
            for i in range(5):
                store.save(make_video(i))
        assert os.path.exists(db)

        # -- read FROM a freshly opened db (persisted across connections) --
        with SQLiteStore(db) as store:
            rows = store.all("videos")
            assert len(rows) == 5
            videos = [Video.from_dict(r) for r in rows]
            names = sorted(v.name for v in videos)
            assert names == [f"video_{i}.mp4" for i in range(5)]

    def test_video_object_roundtrip_fidelity(self, tmp_path):
        db = str(tmp_path / "v.db")
        original = make_video(42)
        with SQLiteStore(db) as store:
            store.save(original)
        with SQLiteStore(db) as store:
            row = store.get("videos", original.content_hash)
        restored = Video.from_dict(row)
        assert restored == original

    def test_raw_metadata_json_roundtrip(self):
        store = SQLiteStore(":memory:")
        v = make_video(7)
        store.save(v)
        row = store.get("videos", v.content_hash)
        assert row["raw_metadata"] == {"format": {"nb_streams": 2}, "streams": [{"index": 0}]}
        assert isinstance(row["raw_metadata"], dict)
        store.close()

    def test_upsert_by_primary_key(self):
        store = SQLiteStore(":memory:")
        v = make_video(1, content_hash="same")
        store.save(v)
        v2 = make_video(1, content_hash="same")
        v2.name = "renamed.mp4"
        store.save(v2)
        rows = store.all("videos")
        assert len(rows) == 1
        assert rows[0]["name"] == "renamed.mp4"
        store.close()

    def test_schema_evolves_for_sparse_records(self):
        """A later object with new fields should add columns, not fail."""
        store = SQLiteStore(":memory:")
        minimal = Video(path="D:/a.mp4", name="a.mp4", content_hash="h1")
        store.save(minimal)
        rich = make_video(2, content_hash="h2")
        store.save(rich)
        row = store.get("videos", "h2")
        assert row["width"] == 1920
        # earlier minimal record still present and readable
        assert store.get("videos", "h1")["name"] == "a.mp4"
        store.close()

    def test_missing_key_returns_none(self):
        store = SQLiteStore(":memory:")
        assert store.get("videos", "nope") is None
        assert store.all("videos") == []
        store.close()

    def test_none_primary_key_rejected(self):
        store = SQLiteStore(":memory:")
        v = Video(path="D:/x.mp4", name="x.mp4", content_hash=None)
        with pytest.raises(ValueError):
            store.save(v)
        store.close()

    def test_concurrent_saves_are_threadsafe(self, tmp_path):
        db = str(tmp_path / "concurrent.db")
        store = SQLiteStore(db)

        def worker(start):
            for i in range(start, start + 25):
                store.save(make_video(i, content_hash=f"h{i}"))

        threads = [threading.Thread(target=worker, args=(s,)) for s in (0, 25, 50, 75)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(store.all("videos")) == 100
        store.close()


class TestSQLiteIndexing:
    def _indexes(self, store):
        """Map index name -> (is_unique, indexed_column) from the live db."""
        cur = store._conn.execute(
            "SELECT name, \"unique\" FROM pragma_index_list('videos')"
        )
        out = {}
        for row in cur.fetchall():
            cols = store._conn.execute(
                f"SELECT name FROM pragma_index_info('{row['name']}')"
            ).fetchall()
            out[row["name"]] = (bool(row["unique"]), [c["name"] for c in cols])
        return out

    def test_secondary_indexes_created(self):
        store = SQLiteStore(":memory:")
        store.save(make_video(1))
        idx = self._indexes(store)
        for field in ("name", "directory", "latitude", "longitude", "country",
                      "creation_time", "device"):
            name = f"idx_videos_{field}"
            assert name in idx, f"missing index for {field}"
            is_unique, cols = idx[name]
            assert is_unique is False
            assert cols == [field]
        store.close()

    def test_unique_index_on_path(self):
        store = SQLiteStore(":memory:")
        store.save(make_video(1))
        idx = self._indexes(store)
        assert "uix_videos_path" in idx
        is_unique, cols = idx["uix_videos_path"]
        assert is_unique is True
        assert cols == ["path"]
        store.close()

    def test_unique_path_dedups_on_replace(self):
        store = SQLiteStore(":memory:")
        # same path under a new content hash: INSERT OR REPLACE resolves the
        # UNIQUE(path) conflict by replacing the old row (one row per path).
        store.save(Video(path="D:/dup.mp4", name="dup.mp4", content_hash="h1"))
        store.save(Video(path="D:/dup.mp4", name="renamed.mp4", content_hash="h2"))
        rows = store.all("videos")
        assert len(rows) == 1
        assert rows[0]["content_hash"] == "h2"
        assert rows[0]["name"] == "renamed.mp4"
        assert store.get("videos", "h1") is None  # old row replaced
        store.close()

    def test_indexes_are_idempotent_across_saves(self):
        store = SQLiteStore(":memory:")
        for i in range(3):
            store.save(make_video(i, content_hash=f"h{i}"))
        idx = self._indexes(store)
        # exactly one index per declared field (no duplicates from re-saving)
        assert sum(1 for n in idx if n.startswith("idx_videos_")) == 7
        assert sum(1 for n in idx if n.startswith("uix_videos_")) == 1
        store.close()

    def test_indexes_persist_across_connections(self, tmp_path):
        db = str(tmp_path / "idx.db")
        with SQLiteStore(db) as store:
            store.save(make_video(1))
        # reopen: indexes were committed to the file
        with SQLiteStore(db) as store:
            idx = self._indexes(store)
            assert "uix_videos_path" in idx
            assert "idx_videos_directory" in idx

    def test_directory_index_used_by_planner(self):
        store = SQLiteStore(":memory:")
        for i in range(20):
            store.save(make_video(i, content_hash=f"h{i}"))
        plan = store._conn.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM videos WHERE directory = ?",
            ("D:/clips",),
        ).fetchall()
        detail = " ".join(str(r["detail"]) for r in plan)
        assert "idx_videos_directory" in detail
        store.close()


class TestVideoModel:
    def test_path_and_name_required(self):
        with pytest.raises(TypeError):
            Video()  # missing required path/name

    def test_storable_contract(self):
        v = make_video(0)
        assert v.storage_name == "videos"
        assert v.primary_key == "content_hash"
        assert v.key_value() == v.content_hash
        assert "video_0.mp4" in str(v)
        assert v.to_dict()["path"] == v.path
