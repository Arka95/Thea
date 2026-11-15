"""Catalogue migration, caption preservation and evidence-based search."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from tools.catalogue import (
    enrich_locale,
    import_catalogues,
    merge_video,
    migrate_catalogue,
    save_description,
    search_catalogue,
)
from tools.geocoding import OfflinePlaceGazetteer, PlaceHit
from tools.models.video import Video
from tools.storage.sqlite_store import SQLiteStore
from tools.walkdir import build_video, index_videos

_KEPT_COLUMNS = {
    "path",
    "name",
    "content_hash",
    "directory",
    "extension",
    "size_bytes",
    "creation_time",
    "device",
    "make",
    "model",
    "latitude",
    "longitude",
    "country",
    "state",
    "location",
    "description",
    "tags",
    "width",
    "height",
    "fps",
    "duration_sec",
}


def test_migration_prunes_legacy_columns_preserves_records_and_consolidates_times(catalogue_path):
    with closing(sqlite3.connect(catalogue_path)) as connection, connection:
        connection.execute(
            "CREATE TABLE videos (content_hash PRIMARY KEY, path UNIQUE, name, description, "
            "country, state, latitude, longitude, location, creation_time, created_time, "
            "modified_time, tags, video_codec, audio_codec, channels, format_name, "
            "video_stream_count, audio_stream_count, subtitle_stream_count, data_stream_count, "
            "altitude, location_accuracy_m, location_source, "
            "locale_source, encoder, raw_metadata)"
        )
        connection.executemany(
            "INSERT INTO videos (content_hash,path,name,description,country,state,latitude,"
            "longitude,location,creation_time,created_time,tags,raw_metadata) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    "embedded",
                    "one.mp4",
                    "one.mp4",
                    "Preserve this caption.",
                    "India",
                    "Arunachal Pradesh",
                    27.5,
                    91.8,
                    "+27.5+091.8/",
                    "2025-03-01T10:20:30+05:30",
                    1700000000,
                    '["Tawang Monastery"]',
                    "invalid JSON that must be ignored",
                ),
                (
                    "fallback",
                    "two.mp4",
                    "two.mp4",
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    1700000000,
                    None,
                    None,
                ),
            ],
        )
    result = migrate_catalogue()
    assert set(result["columns"]) == _KEPT_COLUMNS
    assert result["records"] == 2 and result["described"] == 1
    assert {
        "video_codec",
        "audio_codec",
        "raw_metadata",
        "created_time",
        "video_stream_count",
        "audio_stream_count",
        "subtitle_stream_count",
        "data_stream_count",
    } <= set(result["removed_columns"])
    with SQLiteStore(str(catalogue_path)) as store:
        embedded = store.get("videos", "embedded")
        fallback = store.get("videos", "fallback")
    assert embedded["creation_time"] == "2025-03-01T10:20:30+05:30"
    assert embedded["tags"] == ["Tawang Monastery"]
    assert embedded["description"] == "Preserve this caption."
    assert (
        embedded["country"],
        embedded["state"],
        embedded["latitude"],
        embedded["longitude"],
        embedded["location"],
    ) == (
        "India",
        "Arunachal Pradesh",
        27.5,
        91.8,
        "+27.5+091.8/",
    )
    assert fallback["creation_time"] == datetime.fromtimestamp(1700000000, UTC).isoformat()
    assert fallback["tags"] == []
    assert migrate_catalogue()["removed_columns"] == []
    with closing(sqlite3.connect(catalogue_path)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_migration_rolls_back_schema_and_data_if_a_column_cannot_be_dropped(catalogue_path):
    with closing(sqlite3.connect(catalogue_path)) as connection, connection:
        connection.execute(
            "CREATE TABLE videos (content_hash PRIMARY KEY,path,name,creation_time,created_time,"
            "altitude,description)"
        )
        connection.execute(
            "INSERT INTO videos VALUES ('clip','clip.mp4','clip.mp4',NULL,1700000000,400,'Keep.')"
        )
        connection.execute("CREATE INDEX custom_altitude ON videos(altitude)")
    with pytest.raises(sqlite3.OperationalError):
        migrate_catalogue()
    with closing(sqlite3.connect(catalogue_path)) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(videos)")}
        assert "created_time" in columns and "altitude" in columns and "tags" not in columns
        assert connection.execute(
            "SELECT creation_time,created_time,description FROM videos"
        ).fetchone() == (None, 1700000000, "Keep.")


@pytest.mark.parametrize("tags", ['"not an array"', '["valid", 3]', "invalid JSON"])
def test_migration_rejects_invalid_existing_tags_without_losing_data(catalogue_path, tags):
    with closing(sqlite3.connect(catalogue_path)) as connection, connection:
        connection.execute("CREATE TABLE videos (content_hash PRIMARY KEY,path,name,tags,encoder)")
        connection.execute(
            "INSERT INTO videos VALUES ('clip','clip.mp4','clip.mp4',?,'camera')", (tags,)
        )
    with pytest.raises((ValueError, TypeError)):
        migrate_catalogue()
    with closing(sqlite3.connect(catalogue_path)) as connection:
        assert connection.execute("SELECT tags,encoder FROM videos").fetchone() == (tags, "camera")


def test_import_merges_records_preserves_descriptions_and_source_files(tmp_path, catalogue_path):
    sources = [tmp_path / "first.sqlite3", tmp_path / "second.sqlite3"]
    with SQLiteStore(str(sources[0])) as store:
        store.save(
            Video(
                path="first.mp4",
                name="first.mp4",
                content_hash="same",
                description="Mountain landscape",
                tags=["Tawang Monastery"],
                creation_time="2025-03-01T10:20:30+05:30",
            )
        )
    with closing(sqlite3.connect(sources[0])) as connection, connection:
        connection.execute("ALTER TABLE videos ADD COLUMN audio_codec")
        connection.execute("ALTER TABLE videos ADD COLUMN raw_metadata")
        connection.execute("UPDATE videos SET audio_codec='aac',raw_metadata='ignored'")
    with SQLiteStore(str(sources[1])) as store:
        store.save(
            Video(
                path="copy.mp4", name="copy.mp4", content_hash="same", description="Different draft"
            )
        )
        store.save(Video(path="second.mp4", name="second.mp4", content_hash="other"))
    with closing(sqlite3.connect(sources[1])) as connection, connection:
        connection.execute("ALTER TABLE videos ADD COLUMN created_time")
        connection.execute("UPDATE videos SET created_time=1700000000")
    before = [path.read_bytes() for path in sources]

    result = import_catalogues([str(path) for path in sources])
    assert result["processed"] == 3 and result["distinct"] == 2
    assert result["description_conflicts_preserved"] == 1
    with SQLiteStore(str(catalogue_path)) as store:
        row = store.get("videos", "same")
    assert row["description"] == "Mountain landscape"
    assert row["tags"] == ["Tawang Monastery"]
    assert row["creation_time"] == "2025-03-01T10:20:30+05:30"
    assert [path.read_bytes() for path in sources] == before
    assert import_catalogues([str(path) for path in sources])["distinct"] == 2


def test_tags_are_searchable_and_survive_caption_saves(catalogue_path):
    original = Video(
        path="clip.mp4", name="clip.mp4", content_hash="clip", tags=["Tawang Monastery"]
    )
    with SQLiteStore(str(catalogue_path)) as store:
        store.save(original)
    save_description(Video(path="clip.mp4", name="clip.mp4", content_hash="clip"), "A courtyard.")
    result = search_catalogue("Tawang Monastery")
    assert result["total"] == 1
    assert result["results"][0]["tags"] == ["Tawang Monastery"]
    assert set(result["results"][0]) == _KEPT_COLUMNS | {"score", "exists"}


@pytest.mark.parametrize("probe", [False, True])
def test_reindex_preserves_recording_time_when_probe_is_missing(
    tmp_path, monkeypatch, catalogue_path, probe
):
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"synthetic footage")
    original = build_video(str(source))
    original.creation_time = "2024-01-02T03:04:05Z"
    with SQLiteStore(str(catalogue_path)) as store:
        store.save(original)
    monkeypatch.setattr("tools.walkdir.run_ffprobe", lambda path: None)
    index_videos(str(tmp_path), probe=probe)
    with SQLiteStore(str(catalogue_path)) as store:
        assert store.get("videos", original.content_hash)["creation_time"] == original.creation_time


def test_embedded_recording_time_replaces_a_previous_filesystem_fallback(
    tmp_path, monkeypatch, catalogue_path
):
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"synthetic footage")
    index_videos(str(tmp_path))
    monkeypatch.setattr(
        "tools.walkdir.run_ffprobe",
        lambda path: {"format": {"tags": {"creation_time": "2024-01-02T03:04:05Z"}}},
    )
    index_videos(str(tmp_path), probe=True)
    with SQLiteStore(str(catalogue_path)) as store:
        assert store.all("videos")[0]["creation_time"] == "2024-01-02T03:04:05Z"


def test_reindex_preserves_enrichment_but_not_for_changed_content(tmp_path, catalogue_path):
    root = tmp_path / "footage"
    root.mkdir()
    source = root / "clip.mp4"
    source.write_bytes(b"old footage")
    video = build_video(str(source))
    video.description, video.country, video.width = "A mountain.", "India", 3840
    video.tags = ["Tawang Monastery"]
    with SQLiteStore(str(catalogue_path)) as store:
        store.save(video)
    index_videos(str(root))
    with SQLiteStore(str(catalogue_path)) as store:
        same = store.get("videos", video.content_hash)
    assert (same["description"], same["country"], same["width"]) == ("A mountain.", "India", 3840)
    assert same["tags"] == ["Tawang Monastery"]

    source.write_bytes(b"changed footage")
    index_videos(str(root))
    with SQLiteStore(str(catalogue_path)) as store:
        rows = store.all("videos")
    assert len(rows) == 1
    assert rows[0]["content_hash"] != video.content_hash
    assert rows[0]["description"] is None
    assert rows[0]["tags"] == []


def test_search_requires_evidence_for_each_concept_and_ranks_descriptions(catalogue_path):
    with SQLiteStore(str(catalogue_path)) as store:
        for key, path, state, description in [
            (
                "best",
                r"E:\Arunachal\drone\one.mp4",
                "Arunachal Pradesh",
                "Aerial mountain landscape.",
            ),
            ("also", r"E:\Arunachal\drone\two.mp4", "Arunachal Pradesh", "A forest."),
            ("unknown", r"E:\Arunachal\drone\three.mp4", "Arunachal Pradesh", None),
            ("wrong", r"E:\Other\drone\four.mp4", "Kerala", "Aerial mountain landscape."),
        ]:
            store.save(
                Video(
                    path=path,
                    name=path,
                    content_hash=key,
                    state=state,
                    country="India",
                    description=description,
                )
            )
    result = search_catalogue("find me drone footage in Arunachal for nature", limit=1)
    assert result["total"] == 2
    assert [row["content_hash"] for row in result["results"]] == ["best"]
    assert result["results"][0]["exists"] is False
    assert search_catalogue("Arunachal' OR '1'='1")["total"] == 0


def test_import_rejects_unknown_fields_without_discarding_them(tmp_path, catalogue_path):
    source = tmp_path / "legacy.sqlite3"
    with closing(sqlite3.connect(source)) as connection:
        connection.execute("CREATE TABLE videos (content_hash, path, name, custom_caption)")
        connection.commit()
    with pytest.raises(ValueError, match="Unsupported"):
        import_catalogues([str(source)])
    assert not catalogue_path.exists()


def test_import_rejects_same_path_different_content_without_erasing_record(
    tmp_path, catalogue_path
):
    source = tmp_path / "legacy.sqlite3"
    with SQLiteStore(str(catalogue_path)) as store:
        store.save(
            Video(path="same.mp4", name="same.mp4", content_hash="original", description="Keep.")
        )
    with SQLiteStore(str(source)) as store:
        store.save(Video(path="same.mp4", name="same.mp4", content_hash="different"))
    with pytest.raises(ValueError, match="disagree"):
        import_catalogues([str(source)])
    with SQLiteStore(str(catalogue_path)) as store:
        assert store.get("videos", "original")["description"] == "Keep."


def test_folder_locale_fills_state_without_overwriting_gps_or_explicit_country():
    hit = PlaceHit(28, 94, "India", "state", "arunachal pradesh")
    gazetteer = SimpleNamespace(lookup=lambda phrase: hit if phrase == "arunachal" else None)
    video = Video(
        path=r"E:\Arunachal\drone\clip.mp4",
        name="clip.mp4",
        country="India",
        latitude=28.7,
        longitude=94.4,
        location="+28.7+094.4/",
    )
    enriched = enrich_locale(video, gazetteer)
    assert (enriched.country, enriched.state) == ("India", "Arunachal Pradesh")
    assert (enriched.latitude, enriched.longitude, enriched.location) == (
        28.7,
        94.4,
        "+28.7+094.4/",
    )
    conflicting = Video(path=video.path, name=video.name, country="Bhutan")
    assert enrich_locale(conflicting, gazetteer).state is None


def test_reindex_folder_guess_cannot_replace_known_locale_or_gps():
    existing = Video(
        path="clip.mp4",
        name="clip.mp4",
        country="Bhutan",
        state="Paro",
        latitude=27.4,
        longitude=89.4,
        location="+27.4+089.4/",
    )
    incoming = Video(
        path="clip.mp4",
        name="clip.mp4",
        country="India",
        state="Arunachal Pradesh",
        latitude=28,
        longitude=94,
    )
    merged = merge_video(existing.to_dict(), incoming)
    assert (merged.country, merged.state) == ("Bhutan", "Paro")
    assert (merged.latitude, merged.longitude, merged.location) == (27.4, 89.4, "+27.4+089.4/")


def test_shortened_state_lookup_requires_unique_word_prefix(monkeypatch):
    gazetteer = OfflinePlaceGazetteer()
    monkeypatch.setattr(gazetteer, "_ensure_loaded", lambda: True)
    arunachal = PlaceHit(28, 94, "India", "state", "arunachal pradesh")
    gazetteer._states = {
        "arunachal pradesh": arunachal,
        "north carolina": PlaceHit(35, -80, "United States", "state", "north carolina"),
        "north dakota": PlaceHit(47, -100, "United States", "state", "north dakota"),
    }
    assert gazetteer.lookup("Arunachal") == arunachal
    assert gazetteer.lookup("North") is None
    assert gazetteer.lookup("Aruna") is None
