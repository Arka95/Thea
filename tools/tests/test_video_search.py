"""
tools/tests/test_video_search.py — VideoSearch over country/year/date/name/path.

Runs against BOTH the in-memory store (Python-filter fallback) and the SQLite
store (indexed SQL) to prove the search is backend-agnostic and both paths
agree. Country is set directly on the records (geocoding happens at ingest and
is not exercised here).
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from tools.models.video import Video
from tools.storage.memory_store import InMemoryStore
from tools.storage.sqlite_store import SQLiteStore
from tools.video_search import VideoSearch


def _v(idx, name, path, country=None, creation_time=None):
    return Video(
        path=path,
        name=name,
        content_hash=f"h{idx}",
        directory=os.path.dirname(path),
        extension=os.path.splitext(path)[1].lower() or None,
        country=country,
        creation_time=creation_time,
    )


SAMPLE = [
    _v(1, "IMG_athens.MOV", "D:/trips/greece/IMG_athens.MOV",
       country="Greece", creation_time="2024-06-10T10:00:00+0300"),
    _v(2, "IMG_paros.MOV", "D:/trips/greece/IMG_paros.MOV",
       country="Greece", creation_time="2023-08-01T09:00:00+0300"),
    _v(3, "PXL_paris.mp4", "D:/trips/france/PXL_paris.mp4",
       country="France", creation_time="2024-06-15T12:00:00+0200"),
    _v(4, "clip.mp4", "D:/misc/clip.mp4", country=None, creation_time=None),
]


@pytest.fixture(params=["memory", "sqlite"])
def search(request):
    store = InMemoryStore() if request.param == "memory" else SQLiteStore(":memory:")
    for v in SAMPLE:
        store.save(v)
    yield VideoSearch(store)
    if hasattr(store, "close"):
        store.close()


def _names(results):
    return {v.name for v in results}


# --------------------------- single criterion ----------------------------- #

def test_by_country(search):
    assert _names(search.by_country("Greece")) == {"IMG_athens.MOV", "IMG_paros.MOV"}
    assert _names(search.by_country("France")) == {"PXL_paris.mp4"}
    assert search.by_country("Japan") == []


def test_by_year_int_and_str(search):
    assert _names(search.by_year(2024)) == {"IMG_athens.MOV", "PXL_paris.mp4"}
    assert _names(search.by_year("2023")) == {"IMG_paros.MOV"}


def test_by_year_accepts_date(search):
    assert _names(search.by_year(datetime.date(2024, 1, 1))) == {
        "IMG_athens.MOV", "PXL_paris.mp4"}


def test_by_date_str_and_date(search):
    assert _names(search.by_date("2024-06-10")) == {"IMG_athens.MOV"}
    assert _names(search.by_date(datetime.date(2024, 6, 15))) == {"PXL_paris.mp4"}


def test_by_name_substring_case_insensitive(search):
    assert _names(search.by_name("paros")) == {"IMG_paros.MOV"}
    assert _names(search.by_name("PAROS")) == {"IMG_paros.MOV"}  # case-insensitive
    assert _names(search.by_name("IMG_")) == {"IMG_athens.MOV", "IMG_paros.MOV"}


def test_by_name_exact(search):
    assert _names(search.by_name("IMG_paros.MOV", exact=True)) == {"IMG_paros.MOV"}
    assert search.by_name("paros", exact=True) == []


def test_by_path_substring(search):
    assert _names(search.by_path("greece")) == {"IMG_athens.MOV", "IMG_paros.MOV"}
    assert _names(search.by_path("france")) == {"PXL_paris.mp4"}


# --------------------------- combined query ------------------------------- #

def test_combined_country_and_year(search):
    # single query, ANDed: Greece AND 2024 -> only Athens clip
    assert _names(search.search(country="Greece", year=2024)) == {"IMG_athens.MOV"}


def test_combined_country_and_name(search):
    assert _names(search.search(country="Greece", name="paros")) == {"IMG_paros.MOV"}


def test_combined_all_fields(search):
    res = search.search(
        country="Greece", year=2024, date="2024-06-10",
        name="athens", path="greece",
    )
    assert _names(res) == {"IMG_athens.MOV"}


def test_combined_no_match(search):
    assert search.search(country="Greece", year=2020) == []


# --------------------------- ordering / limit / empty --------------------- #

def test_order_by_creation_time_default(search):
    res = search.by_country("Greece")  # order_by creation_time asc
    assert [v.name for v in res] == ["IMG_paros.MOV", "IMG_athens.MOV"]  # 2023 before 2024


def test_limit(search):
    assert len(search.search(limit=2)) == 2


def test_empty_search_returns_all(search):
    assert len(search.search()) == len(SAMPLE)


def test_returns_video_objects(search):
    res = search.by_country("France")
    assert all(isinstance(v, Video) for v in res)
    assert res[0].path == "D:/trips/france/PXL_paris.mp4"
