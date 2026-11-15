"""Keep catalogue operations and optional locale datasets isolated in units."""

from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def catalogue_path(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr("utils.settings.resolve_data_dir", lambda source: str(data))
    monkeypatch.setattr(
        "tools.catalogue.default_gazetteer", lambda: SimpleNamespace(lookup=lambda name: None)
    )
    return data / "video-index.sqlite3"
