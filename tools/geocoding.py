"""
tools/geocoding.py — pluggable reverse geocoding (lat/lon -> country name).

Geocoding is deliberately behind a small :class:`Geocoder` abstraction so the
rest of the tool never talks to a specific library. The country is resolved
*once at ingest time* and persisted on the :class:`~tools.models.video.Video`
row, which means callers can later query by country name directly — no
coordinates or geocoding at query time (see :mod:`tools.video_search`).

Implementations:

* :class:`OfflineReverseGeocoder` — fully offline, no API keys or network. Uses
  ``reverse_geocoder`` (nearest-city lookup over a bundled dataset) to get an
  ISO-3166 alpha-2 code, then ``pycountry`` to map it to a country name. Results
  are cached and the libraries are imported lazily, so importing this module is
  cheap and environments without the optional deps degrade to ``None``.
* :class:`NullGeocoder` — always returns ``None`` (disable geocoding / tests).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


class Geocoder(ABC):
    """Resolve a coordinate to a country. The single seam for all geocoding."""

    @abstractmethod
    def country(self, latitude: Optional[float], longitude: Optional[float]) -> Optional[str]:
        """Return the country name for ``(latitude, longitude)``, or ``None``."""


class NullGeocoder(Geocoder):
    """A geocoder that resolves nothing (used to disable geocoding)."""

    def country(self, latitude: Optional[float], longitude: Optional[float]) -> Optional[str]:
        return None


class OfflineReverseGeocoder(Geocoder):
    """Offline lat/lon -> country name via ``reverse_geocoder`` + ``pycountry``.

    Libraries are imported lazily on first use; if either is unavailable the
    geocoder simply returns ``None`` instead of raising. Lookups are cached by
    rounded coordinate so repeat/near-identical positions are free.
    """

    def __init__(self, cache_precision: int = 3) -> None:
        self._cache_precision = cache_precision
        self._cache: Dict[Tuple[float, float], Optional[str]] = {}
        self._rg = None
        self._pycountry = None
        self._loaded = False

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return self._rg is not None
        self._loaded = True
        try:
            import reverse_geocoder
            import pycountry
            self._rg = reverse_geocoder
            self._pycountry = pycountry
        except Exception:
            self._rg = None
            self._pycountry = None
        return self._rg is not None

    def _code_to_name(self, code: Optional[str]) -> Optional[str]:
        if not code:
            return None
        try:
            match = self._pycountry.countries.get(alpha_2=code)
            return match.name if match is not None else code
        except Exception:
            return code

    def country(self, latitude: Optional[float], longitude: Optional[float]) -> Optional[str]:
        if latitude is None or longitude is None:
            return None
        if not self._ensure_loaded():
            return None

        key = (round(latitude, self._cache_precision), round(longitude, self._cache_precision))
        if key in self._cache:
            return self._cache[key]

        code: Optional[str] = None
        try:
            # mode=1 => single-threaded (no multiprocessing pool per call).
            results = self._rg.search((latitude, longitude), mode=1)
            if results:
                code = results[0].get("cc")
        except Exception:
            code = None

        name = self._code_to_name(code)
        self._cache[key] = name
        return name


_DEFAULT_GEOCODER: Optional[Geocoder] = None


def default_geocoder() -> Geocoder:
    """Return a process-wide :class:`OfflineReverseGeocoder` (dataset loads once)."""
    global _DEFAULT_GEOCODER
    if _DEFAULT_GEOCODER is None:
        _DEFAULT_GEOCODER = OfflineReverseGeocoder()
    return _DEFAULT_GEOCODER


# --------------------------------------------------------------------------- #
# Forward gazetteer: place name -> approximate (averaged) centroid.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PlaceHit:
    """An approximate location resolved from a country/state *name*."""

    latitude: float
    longitude: float
    country: Optional[str]   # country name (for a state hit, its parent country)
    kind: str                # "country" or "state"
    matched: str             # the name that matched


class PlaceGazetteer(ABC):
    """Resolve a country/state name to an approximate centroid."""

    @abstractmethod
    def lookup(self, name: str) -> Optional[PlaceHit]:
        """Return a :class:`PlaceHit` for ``name`` (case-insensitive), or ``None``."""


class OfflinePlaceGazetteer(PlaceGazetteer):
    """Name -> averaged centroid, built offline from the ``reverse_geocoder``
    city dataset.

    The centroid of a country/state is the arithmetic mean of its member cities'
    coordinates ("average out a lat/lon"). Countries are keyed by every
    ``pycountry`` name variant plus the alpha-3 code; states by their ``admin1``
    name. Precision is coarse — this is a deliberate last-resort fallback for
    videos that carry no GPS tag. Data is loaded lazily and cached; if the
    optional libraries are unavailable the gazetteer resolves nothing.
    """

    _MIN_KEY_LEN = 3  # avoid matching very short, ambiguous tokens

    def __init__(self) -> None:
        self._loaded = False
        self._countries: Dict[str, PlaceHit] = {}
        self._states: Dict[str, PlaceHit] = {}

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return bool(self._countries or self._states)
        self._loaded = True
        try:
            import csv
            import os
            import reverse_geocoder
            import pycountry
        except Exception:
            return False

        path = os.path.join(os.path.dirname(reverse_geocoder.__file__), "rg_cities1000.csv")
        cc_acc: Dict[str, list] = {}
        state_acc: Dict[str, list] = {}
        try:
            with open(path, encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    try:
                        lat = float(row["lat"])
                        lon = float(row["lon"])
                    except (TypeError, ValueError, KeyError):
                        continue
                    cc = (row.get("cc") or "").strip()
                    if cc:
                        acc = cc_acc.setdefault(cc, [0.0, 0.0, 0])
                        acc[0] += lat
                        acc[1] += lon
                        acc[2] += 1
                    admin1 = (row.get("admin1") or "").strip().lower()
                    if len(admin1) >= self._MIN_KEY_LEN and any(c.isalpha() for c in admin1):
                        acc = state_acc.setdefault(admin1, [0.0, 0.0, 0, {}])
                        acc[0] += lat
                        acc[1] += lon
                        acc[2] += 1
                        acc[3][cc] = acc[3].get(cc, 0) + 1
        except OSError:
            return False

        self._build_countries(cc_acc, pycountry)
        self._build_states(state_acc, pycountry)
        return bool(self._countries or self._states)

    def _build_countries(self, cc_acc: Dict[str, list], pycountry) -> None:
        centroids = {cc: (s[0] / s[2], s[1] / s[2]) for cc, s in cc_acc.items() if s[2]}
        for country in pycountry.countries:
            centroid = centroids.get(country.alpha_2)
            if centroid is None:
                continue
            hit = PlaceHit(round(centroid[0], 4), round(centroid[1], 4),
                           country.name, "country", country.name)
            names = [country.name, getattr(country, "common_name", None),
                     getattr(country, "official_name", None), country.alpha_3]
            for raw in names:
                if not raw:
                    continue
                key = raw.strip().lower()
                if len(key) >= self._MIN_KEY_LEN:
                    self._countries.setdefault(key, hit)

    def _build_states(self, state_acc: Dict[str, list], pycountry) -> None:
        for name, acc in state_acc.items():
            if not acc[2]:
                continue
            top_cc = max(acc[3], key=acc[3].get) if acc[3] else None
            country_name = None
            if top_cc:
                match = pycountry.countries.get(alpha_2=top_cc)
                country_name = match.name if match is not None else None
            self._states[name] = PlaceHit(
                round(acc[0] / acc[2], 4), round(acc[1] / acc[2], 4),
                country_name, "state", name,
            )

    def lookup(self, name: str) -> Optional[PlaceHit]:
        if not name:
            return None
        if not self._ensure_loaded():
            return None
        key = name.strip().lower()
        # Countries take precedence over like-named states (e.g. "Georgia").
        return self._countries.get(key) or self._states.get(key)


_DEFAULT_GAZETTEER: Optional[PlaceGazetteer] = None


def default_gazetteer() -> PlaceGazetteer:
    """Return a process-wide :class:`OfflinePlaceGazetteer` (dataset loads once)."""
    global _DEFAULT_GAZETTEER
    if _DEFAULT_GAZETTEER is None:
        _DEFAULT_GAZETTEER = OfflinePlaceGazetteer()
    return _DEFAULT_GAZETTEER
