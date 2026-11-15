"""Opt-in integration tests using bundled geocoding datasets."""

import pytest

from tools.geocoding import (
    OfflinePlaceGazetteer,
    OfflineReverseGeocoder,
    default_gazetteer,
    default_geocoder,
)


class TestOfflineReverseGeocoderReal:
    @pytest.fixture(autouse=True)
    def _require_libs(self):
        pytest.importorskip("reverse_geocoder")
        pytest.importorskip("pycountry")

    def test_athens_resolves_to_greece(self):
        g = OfflineReverseGeocoder()
        assert g.country(37.9838, 23.7275) == "Greece"

    def test_paris_resolves_to_france(self):
        g = OfflineReverseGeocoder()
        assert g.country(48.8566, 2.3522) == "France"

    def test_result_is_cached(self):
        g = OfflineReverseGeocoder()
        first = g.country(37.9838, 23.7275)
        assert (round(37.9838, 3), round(23.7275, 3)) in g._cache
        assert g.country(37.9838, 23.7275) == first  # served from cache

    def test_default_geocoder_is_singleton(self):
        assert default_geocoder() is default_geocoder()


class TestOfflinePlaceGazetteerReal:
    @pytest.fixture(autouse=True)
    def _require_libs(self):
        pytest.importorskip("reverse_geocoder")
        pytest.importorskip("pycountry")

    def test_country_centroid(self):
        hit = OfflinePlaceGazetteer().lookup("Greece")
        assert hit is not None
        assert hit.kind == "country"
        assert hit.country == "Greece"
        assert 34 < hit.latitude < 42 and 19 < hit.longitude < 30  # inside Greece

    def test_country_case_insensitive_and_alpha3(self):
        g = OfflinePlaceGazetteer()
        assert g.lookup("greece") is not None
        assert g.lookup("USA") is not None  # alpha-3 code
        assert g.lookup("USA").kind == "country"

    def test_state_centroid_has_parent_country(self):
        hit = OfflinePlaceGazetteer().lookup("West Bengal")
        assert hit is not None
        assert hit.kind == "state"
        assert hit.country == "India"
        assert 20 < hit.latitude < 27 and 85 < hit.longitude < 90

    def test_unknown_place_returns_none(self):
        assert OfflinePlaceGazetteer().lookup("Nowhereland") is None
        assert OfflinePlaceGazetteer().lookup("") is None

    def test_default_gazetteer_is_singleton(self):
        assert default_gazetteer() is default_gazetteer()
