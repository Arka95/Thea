"""
Unit tests for geocoding without loading the bundled city dataset.
"""

from tools.geocoding import (
    NullGeocoder,
    OfflineReverseGeocoder,
)


def test_null_geocoder_returns_none():
    g = NullGeocoder()
    assert g.country(37.98, 23.72) is None
    assert g.country(None, None) is None


def test_offline_geocoder_missing_coords_returns_none():
    # No lat/lon -> no lookup, no library load required.
    g = OfflineReverseGeocoder()
    assert g.country(None, None) is None
    assert g.country(37.98, None) is None
