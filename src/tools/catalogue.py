"""Shared video catalogue, locale enrichment, imports and ranked text search."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from tools.geocoding import default_gazetteer
from tools.models.video import Video
from tools.storage.sqlite_store import SQLiteStore
from tools.video_meta_strategy import PathLocationStrategy, build_context
from utils.settings import get_catalogue_path

# Accepted only for migrating/importing older catalogues, never as Video fields.
_RETIRED_FIELDS = {
    "modified_time",
    "created_time",
    "altitude",
    "location_accuracy_m",
    "location_source",
    "locale_source",
    "format_name",
    "format_long_name",
    "bit_rate",
    "nb_streams",
    "start_time",
    "probe_score",
    "video_stream_count",
    "audio_stream_count",
    "subtitle_stream_count",
    "data_stream_count",
    "video_codec",
    "video_codec_long",
    "video_profile",
    "coded_width",
    "coded_height",
    "pix_fmt",
    "level",
    "video_bit_rate",
    "avg_frame_rate",
    "r_frame_rate",
    "nb_frames",
    "has_b_frames",
    "sample_aspect_ratio",
    "display_aspect_ratio",
    "color_range",
    "color_space",
    "color_transfer",
    "color_primaries",
    "field_order",
    "bits_per_raw_sample",
    "audio_codec",
    "audio_codec_long",
    "audio_profile",
    "sample_rate",
    "channels",
    "channel_layout",
    "sample_fmt",
    "audio_bit_rate",
    "audio_bits_per_sample",
    "major_brand",
    "encoder",
    "android_version",
    "capture_fps",
    "raw_metadata",
}


def migrate_catalogue() -> dict:
    """Atomically prune retired columns and consolidate timestamps in the active DB."""
    db = Path(get_catalogue_path())
    db.parent.mkdir(parents=True, exist_ok=True)
    desired = set(Video.__dataclass_fields__)
    with closing(sqlite3.connect(db)) as connection, connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("CREATE TABLE IF NOT EXISTS videos (content_hash PRIMARY KEY)")
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(videos)")}
        unknown = columns - desired - _RETIRED_FIELDS
        if unknown:
            raise ValueError(f"Unsupported video fields: {sorted(unknown)}")
        before = connection.execute("SELECT count(*) FROM videos").fetchone()[0]
        removed = sorted(columns & _RETIRED_FIELDS)
        if columns != desired:
            for name in Video.__dataclass_fields__:
                if name not in columns:
                    suffix = " TEXT NOT NULL DEFAULT '[]'" if name == "tags" else ""
                    connection.execute(f'ALTER TABLE videos ADD COLUMN "{name}"{suffix}')
            selected = "content_hash,path,name,creation_time,tags"
            if "created_time" in columns:
                selected += ",created_time"
            for row in connection.execute(f"SELECT {selected} FROM videos").fetchall():
                video = Video.from_dict(dict(row))
                tags = json.dumps(video.tags, ensure_ascii=False)
                if video.creation_time != row["creation_time"] or tags != row["tags"]:
                    connection.execute(
                        "UPDATE videos SET creation_time=?,tags=? WHERE content_hash IS ?",
                        (video.creation_time, tags, video.content_hash),
                    )
            for name in removed:
                connection.execute(f'ALTER TABLE videos DROP COLUMN "{name}"')
        actual = [row["name"] for row in connection.execute("PRAGMA table_info(videos)")]
        after = connection.execute("SELECT count(*) FROM videos").fetchone()[0]
        if set(actual) != desired or after != before:
            raise RuntimeError("Catalogue schema migration did not preserve the retained records.")
        described = connection.execute(
            "SELECT count(*) FROM videos WHERE description IS NOT NULL AND trim(description) != ''"
        ).fetchone()[0]
    return {"columns": actual, "removed_columns": removed, "records": after, "described": described}


def open_catalogue() -> SQLiteStore:
    """Open the canonical writable catalogue after its idempotent schema migration."""
    migrate_catalogue()
    return SQLiteStore(get_catalogue_path())


def merge_video(existing: dict | None, incoming: Video) -> Video:
    """Retain stored enrichment when a fresh filesystem/probe field is absent."""
    values = dict(existing or {})
    updates = {key: value for key, value in incoming.to_dict().items() if value is not None}
    if existing:
        for field in ("country", "state"):
            if existing.get(field):
                updates.pop(field, None)
        if (
            existing.get("country")
            and incoming.country
            and (existing["country"].casefold() != incoming.country.casefold())
        ):
            updates.pop("state", None)
        if not incoming.location:
            for field in ("latitude", "longitude"):
                if existing.get(field) is not None:
                    updates.pop(field, None)
        updates["tags"] = list(dict.fromkeys([*Video.from_dict(existing).tags, *incoming.tags]))
    values.update(updates)
    return Video.from_dict(values)


def enrich_locale(video: Video, gazetteer=None) -> Video:
    """Fill missing region names from offline folder matching, never GPS coordinates."""
    if video.country and video.state:
        return video
    location = PathLocationStrategy(
        gazetteer if gazetteer is not None else default_gazetteer()
    ).extract(build_context({}, video.path))
    if location is None:
        return video
    if (
        video.country
        and location.country
        and video.country.casefold() != location.country.casefold()
    ):
        return video
    for field in ("country", "state"):
        if not getattr(video, field) and getattr(location, field):
            setattr(video, field, getattr(location, field))
    return video


def save_description(video: Video, description: str) -> dict:
    """Persist a successful caption without replacing unrelated indexed metadata."""
    if not description.strip():
        raise ValueError("Description must not be empty.")
    db = get_catalogue_path()
    with open_catalogue() as store:
        merged = merge_video(store.get("videos", video.content_hash), video)
        merged.description = description.strip()
        store.save(merged)
    return {"db": db, "content_hash": video.content_hash}


def import_catalogues(paths: list[str]) -> dict:
    """Merge read-only legacy videos tables into the configured catalogue."""
    if not paths:
        raise ValueError("At least one source catalogue is required.")
    db = Path(get_catalogue_path()).resolve()
    sources = []
    known = set(Video.__dataclass_fields__) | _RETIRED_FIELDS
    for name in paths:
        source = Path(name).expanduser().resolve()
        if source == db:
            raise ValueError("The active catalogue cannot be imported into itself.")
        if not source.is_file():
            raise FileNotFoundError(f"Source catalogue not found: {source}")
        if source not in sources:
            with closing(sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True)) as connection:
                columns = {row[1] for row in connection.execute("PRAGMA table_info(videos)")}
                if not {"content_hash", "path", "name"} <= columns:
                    raise ValueError(f"Not a compatible video catalogue: {source}")
                if columns - known:
                    raise ValueError(
                        f"Unsupported video fields in {source}: {sorted(columns - known)}"
                    )
                if connection.execute(
                    "SELECT 1 FROM videos WHERE content_hash IS NULL OR path IS NULL OR name IS NULL LIMIT 1"
                ).fetchone():
                    raise ValueError(f"Catalogue has records without video identity: {source}")
            sources.append(source)
    imported = 0
    conflicts = 0
    with open_catalogue() as store:
        before = len(store.all("videos"))
        for source in sources:
            with closing(sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True)) as connection:
                connection.row_factory = sqlite3.Row
                for row in connection.execute("SELECT * FROM videos ORDER BY path"):
                    values = dict(row)
                    existing = store.get("videos", values["content_hash"])
                    incoming = Video.from_dict(values)
                    if (
                        existing
                        and not values.get("creation_time")
                        and existing.get("creation_time")
                    ):
                        incoming.creation_time = existing["creation_time"]
                    same_path = store.query("videos", [("path", "=", incoming.path)], limit=1)
                    if same_path and same_path[0]["content_hash"] != incoming.content_hash:
                        raise ValueError(
                            "Source catalogues disagree about the content at one path."
                        )
                    if existing and existing.get("description"):
                        if incoming.description and incoming.description != existing["description"]:
                            conflicts += 1
                        incoming.description = existing["description"]
                    store.save(merge_video(existing, incoming))
                    imported += 1
        after = len(store.all("videos"))
    return {
        "db": str(db),
        "sources": [str(path) for path in sources],
        "processed": imported,
        "before": before,
        "distinct": after,
        "description_conflicts_preserved": conflicts,
    }


_SEARCH_FIELDS = {
    "description": 5,
    "tags": 4,
    "state": 4,
    "country": 3,
    "name": 2,
    "path": 1,
    "device": 1,
}
_STOPWORDS = {
    "find",
    "me",
    "show",
    "get",
    "footage",
    "video",
    "videos",
    "clip",
    "clips",
    "in",
    "for",
    "of",
    "the",
    "a",
    "an",
    "and",
    "from",
    "with",
    "please",
}
_CONCEPTS = {
    "nature": (
        "nature",
        "natural",
        "landscape",
        "forest",
        "mountain",
        "river",
        "lake",
        "waterfall",
    ),
    "drone": ("drone", "aerial", "bird's-eye", "overhead"),
}


def search_catalogue(query: str, limit: int = 20) -> dict:
    """Search indexed descriptions and metadata; never infer uncaptured visual content."""
    if not 1 <= limit <= 100:
        raise ValueError("Search limit must be between 1 and 100.")
    terms = list(
        dict.fromkeys(
            term for term in re.findall(r"\w+", query.casefold()) if term not in _STOPWORDS
        )
    )
    if not terms:
        raise ValueError("Search query must contain a descriptive or location term.")
    if len(terms) > 8:
        raise ValueError("Search query must contain at most eight meaningful terms.")
    db = Path(get_catalogue_path())
    if not db.is_file():
        return {"db": str(db), "query": query, "total": 0, "results": []}
    clauses, scoring, filter_values, score_values = [], [], [], []
    for term in terms:
        alternatives = _CONCEPTS.get(term, (term,))
        matches = []
        for field, weight in _SEARCH_FIELDS.items():
            field_matches = []
            for alternative in alternatives:
                field_matches.append(f"lower(coalesce({field}, '')) LIKE ? ESCAPE '\\'")
                escaped = alternative.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                filter_values.append(f"%{escaped}%")
                score_values.append(f"%{escaped}%")
            condition = "(" + " OR ".join(field_matches) + ")"
            matches.append(condition)
            scoring.append(f"CASE WHEN {condition} THEN {weight} ELSE 0 END")
        clauses.append("(" + " OR ".join(matches) + ")")
    where, score = " AND ".join(clauses), " + ".join(scoring)
    with closing(sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        if not connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='videos'"
        ).fetchone():
            return {"db": str(db), "query": query, "total": 0, "results": []}
        columns = {row[1] for row in connection.execute("PRAGMA table_info(videos)")}
        if not set(Video.__dataclass_fields__) <= columns or columns & _RETIRED_FIELDS:
            raise ValueError("Catalogue schema needs migration; run index or importindex first.")
        total = connection.execute(
            f"SELECT count(*) FROM videos WHERE {where}", filter_values
        ).fetchone()[0]
        rows = connection.execute(
            f"SELECT {','.join(Video.__dataclass_fields__)},({score}) AS score "
            f"FROM videos WHERE {where} "
            "ORDER BY score DESC, path LIMIT ?",
            [*score_values, *filter_values, limit],
        ).fetchall()
    results = [
        {
            **Video.from_dict(dict(row)).to_dict(),
            "score": row["score"],
            "exists": Path(row["path"]).is_file(),
        }
        for row in rows
    ]
    return {"db": str(db), "query": query, "total": total, "results": results}
