"""
tools/video_meta_strategy.py — pluggable strategies that derive *device* and
*location* for a video from its ffprobe metadata.

Why a strategy module? A real scan of ``D:\\`` showed that no single tag reliably
identifies the capture device or GPS position — each vendor stores it somewhere
different, and some (Pixel) don't store a device tag at all:

    Device
    ------
    Apple    -> format tag  com.apple.quicktime.make / .model   (explicit)
    GoPro    -> stream handler_name / encoder contains "GoPro"   (e.g. "GoPro H.265")
    DJI      -> stream handler_name starts "DJI."                (e.g. "DJI.AVC")
    Samsung  -> format tag  com.samsung.android.*                (no make/model)
    Pixel    -> filename prefix "PXL_"                           (only reliable signal)
    Other    -> generic make/model tag (LG, ...) or com.android.version + VID_ name

    Location (all ISO-6709: "+lat+lon[+alt]/")
    ------------------------------------------
    Apple    -> com.apple.quicktime.location.ISO6709  (+ .accuracy.horizontal, has altitude)
    Android  -> location / location-eng               (lat+lon only, "-eng" is a duplicate)

Each concern is a prioritised list of small strategy objects; the first that
matches wins. :func:`populate_video` runs them plus the resolution/fps/date
extraction and writes the results onto a :class:`~tools.models.video.Video`.
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------- #
# Probe context — normalises an ffprobe JSON blob for the strategies.
# --------------------------------------------------------------------------- #


@dataclass
class ProbeContext:
    """Normalised view over one ffprobe result."""

    path: str
    filename: str
    format_tags: Dict[str, str]          # original-case format-level tags
    stream_handlers: List[str]           # every stream handler_name
    stream_encoders: List[str]           # every stream/encoder value
    video_stream: Dict[str, Any]         # first video stream (or {})
    format: Dict[str, Any]               # format section
    _ftags_lower: Dict[str, str]

    def ftag(self, key: str) -> Optional[str]:
        """Case-insensitive lookup of a format-level tag."""
        return self._ftags_lower.get(key.lower())

    def has_ftag_prefix(self, prefix: str) -> bool:
        prefix = prefix.lower()
        return any(k.startswith(prefix) for k in self._ftags_lower)

    def handlers_lower(self) -> List[str]:
        return [h.lower() for h in self.stream_handlers]

    def encoders_lower(self) -> List[str]:
        return [e.lower() for e in self.stream_encoders]


def build_context(probe_json: Dict[str, Any], path: str) -> ProbeContext:
    fmt = probe_json.get("format") or {}
    ftags = dict(fmt.get("tags") or {})
    streams = probe_json.get("streams") or []

    handlers: List[str] = []
    encoders: List[str] = []
    for s in streams:
        t = s.get("tags") or {}
        if t.get("handler_name"):
            handlers.append(str(t["handler_name"]))
        if t.get("encoder"):
            encoders.append(str(t["encoder"]))

    vstream = next((s for s in streams if s.get("codec_type") == "video"), {})
    vt = vstream.get("tags") or {}
    if vt.get("encoder"):
        encoders.append(str(vt["encoder"]))

    return ProbeContext(
        path=path,
        filename=_normalise_filename(os.path.basename(path)),
        format_tags=ftags,
        stream_handlers=handlers,
        stream_encoders=encoders,
        video_stream=vstream,
        format=fmt,
        _ftags_lower={k.lower(): v for k, v in ftags.items()},
    )


# Android's trash bin renames files to ".trashed-<epoch>-<original>"; strip it so
# device filename heuristics still see the real name (e.g. "PXL_...").
_TRASH_PREFIX = re.compile(r"^\.trashed-\d+-", re.IGNORECASE)


def _normalise_filename(name: str) -> str:
    return _TRASH_PREFIX.sub("", name)


# --------------------------------------------------------------------------- #
# Device strategies.
# --------------------------------------------------------------------------- #


@dataclass
class DeviceInfo:
    device: Optional[str] = None   # unified label, e.g. "Apple iPhone 15 Plus"
    make: Optional[str] = None
    model: Optional[str] = None


class DeviceStrategy(ABC):
    """Detect the capture device from a :class:`ProbeContext`."""

    name: str = "device"

    @abstractmethod
    def detect(self, ctx: ProbeContext) -> Optional[DeviceInfo]:
        ...


class AppleDeviceStrategy(DeviceStrategy):
    name = "apple"

    def detect(self, ctx: ProbeContext) -> Optional[DeviceInfo]:
        make = ctx.ftag("com.apple.quicktime.make")
        model = ctx.ftag("com.apple.quicktime.model")
        if make or model:
            label = " ".join(x for x in (make, model) if x) or "Apple"
            return DeviceInfo(device=label, make=make or "Apple", model=model)
        return None


class GoProDeviceStrategy(DeviceStrategy):
    name = "gopro"
    _FILENAME = re.compile(r"^(gx|gh|gopr|gp)\d", re.IGNORECASE)

    def detect(self, ctx: ProbeContext) -> Optional[DeviceInfo]:
        if any("gopro" in h for h in ctx.handlers_lower()) \
                or any("gopro" in e for e in ctx.encoders_lower()) \
                or self._FILENAME.match(ctx.filename):
            return DeviceInfo(device="GoPro", make="GoPro")
        return None


class DJIDeviceStrategy(DeviceStrategy):
    name = "dji"
    _FILENAME = re.compile(r"^dji_", re.IGNORECASE)

    def detect(self, ctx: ProbeContext) -> Optional[DeviceInfo]:
        if any(h.startswith("dji.") or "dji" in h for h in ctx.handlers_lower()) \
                or self._FILENAME.match(ctx.filename):
            return DeviceInfo(device="DJI", make="DJI")
        return None


class SamsungDeviceStrategy(DeviceStrategy):
    name = "samsung"

    def detect(self, ctx: ProbeContext) -> Optional[DeviceInfo]:
        if ctx.has_ftag_prefix("com.samsung"):
            return DeviceInfo(device="Samsung", make="Samsung")
        return None


class MakeModelDeviceStrategy(DeviceStrategy):
    """Generic: honour explicit container make/model tags (older phones, LG...)."""

    name = "make_model"

    def detect(self, ctx: ProbeContext) -> Optional[DeviceInfo]:
        make = ctx.ftag("make")
        model = ctx.ftag("model")
        if make or model:
            label = " ".join(x for x in (make, model) if x)
            return DeviceInfo(device=label, make=make, model=model)
        return None


class PixelDeviceStrategy(DeviceStrategy):
    name = "pixel"
    _FILENAME = re.compile(r"^pxl_", re.IGNORECASE)

    def detect(self, ctx: ProbeContext) -> Optional[DeviceInfo]:
        if self._FILENAME.match(ctx.filename):
            return DeviceInfo(device="Google Pixel", make="Google")
        return None


class AndroidDeviceStrategy(DeviceStrategy):
    """Fallback: a generic Android capture (com.android.* present)."""

    name = "android"

    def detect(self, ctx: ProbeContext) -> Optional[DeviceInfo]:
        if ctx.has_ftag_prefix("com.android"):
            return DeviceInfo(device="Android", make="Android")
        return None


# Priority order: explicit brand tags first, generic make/model next,
# filename/heuristic fallbacks last.
DEVICE_STRATEGIES: List[DeviceStrategy] = [
    AppleDeviceStrategy(),
    GoProDeviceStrategy(),
    DJIDeviceStrategy(),
    SamsungDeviceStrategy(),
    MakeModelDeviceStrategy(),
    PixelDeviceStrategy(),
    AndroidDeviceStrategy(),
]


def detect_device(ctx: ProbeContext) -> DeviceInfo:
    """Return the first matching :class:`DeviceInfo`, or an empty one."""
    for strat in DEVICE_STRATEGIES:
        info = strat.detect(ctx)
        if info is not None:
            return info
    return DeviceInfo()


# --------------------------------------------------------------------------- #
# Location strategies.
# --------------------------------------------------------------------------- #

# ISO-6709: "+DD.DDDD+DDD.DDDD[+AAA.AAA]/"  (signed lat, lon, optional altitude)
_ISO6709 = re.compile(r"([+-]\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)?/?")


def parse_iso6709(value: Optional[str]) -> Optional[Dict[str, Optional[float]]]:
    """Parse an ISO-6709 string into lat/lon/alt floats, or ``None``."""
    if not value:
        return None
    m = _ISO6709.match(value.strip())
    if not m:
        return None
    return {
        "latitude": float(m.group(1)),
        "longitude": float(m.group(2)),
        "altitude": float(m.group(3)) if m.group(3) else None,
    }


@dataclass
class LocationInfo:
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    accuracy_m: Optional[float] = None
    raw: Optional[str] = None
    source: Optional[str] = None
    country: Optional[str] = None   # set only by name-based fallbacks (e.g. path)


class LocationStrategy(ABC):
    name: str = "location"

    @abstractmethod
    def extract(self, ctx: ProbeContext) -> Optional[LocationInfo]:
        ...


class AppleLocationStrategy(LocationStrategy):
    """iPhone: ISO-6709 with altitude + horizontal accuracy."""

    name = "apple"

    def extract(self, ctx: ProbeContext) -> Optional[LocationInfo]:
        raw = ctx.ftag("com.apple.quicktime.location.iso6709")
        parsed = parse_iso6709(raw)
        if not parsed:
            return None
        acc = ctx.ftag("com.apple.quicktime.location.accuracy.horizontal")
        return LocationInfo(
            latitude=parsed["latitude"],
            longitude=parsed["longitude"],
            altitude=parsed["altitude"],
            accuracy_m=float(acc) if acc else None,
            raw=raw,
            source="apple",
        )


class AndroidLocationStrategy(LocationStrategy):
    """Android / Pixel / Samsung: `location` tag (`location-eng` is a duplicate)."""

    name = "android"

    def extract(self, ctx: ProbeContext) -> Optional[LocationInfo]:
        raw = ctx.ftag("location") or ctx.ftag("location-eng")
        parsed = parse_iso6709(raw)
        if not parsed:
            return None
        return LocationInfo(
            latitude=parsed["latitude"],
            longitude=parsed["longitude"],
            altitude=parsed["altitude"],
            raw=raw,
            source="android",
        )


# Apple first (richer: altitude + accuracy), then the generic Android tag.
LOCATION_STRATEGIES: List[LocationStrategy] = [
    AppleLocationStrategy(),
    AndroidLocationStrategy(),
]


class PathLocationStrategy(LocationStrategy):
    """Last-resort fallback: infer an *approximate* location from a country or
    state name in the video's folder path when no GPS tag is present.

    The coordinates are the averaged centroid of the matched place (see
    :class:`tools.geocoding.OfflinePlaceGazetteer`), so precision is coarse —
    ``source`` is stamped ``"path:<kind>:<name>"`` to mark the value as inferred.
    Folder segments are scanned deepest-first (most specific), and longer name
    phrases win over shorter ones (e.g. "West Bengal" beats "West").
    """

    name = "path"
    _MAX_NGRAM = 4
    _WORD = re.compile(r"[a-z]+")

    def __init__(self, gazetteer) -> None:
        self._gazetteer = gazetteer

    def extract(self, ctx: ProbeContext) -> Optional[LocationInfo]:
        for segment in self._segments(ctx.path):
            words = self._WORD.findall(segment.lower())
            for n in range(min(self._MAX_NGRAM, len(words)), 0, -1):
                for i in range(len(words) - n + 1):
                    phrase = " ".join(words[i:i + n])
                    hit = self._gazetteer.lookup(phrase)
                    if hit is not None:
                        return LocationInfo(
                            latitude=hit.latitude,
                            longitude=hit.longitude,
                            country=hit.country,
                            source=f"path:{hit.kind}:{hit.matched}",
                        )
        return None

    @staticmethod
    def _segments(path: str) -> List[str]:
        directory = os.path.dirname(path)
        parts = [p for p in re.split(r"[\\/]+", directory) if p]
        return list(reversed(parts))  # deepest folder first (most specific)


def extract_location(ctx: ProbeContext, extra_strategies=None) -> LocationInfo:
    strategies = LOCATION_STRATEGIES
    if extra_strategies:
        strategies = [*LOCATION_STRATEGIES, *extra_strategies]
    for strat in strategies:
        info = strat.extract(ctx)
        if info is not None:
            return info
    return LocationInfo()


# --------------------------------------------------------------------------- #
# Resolution / fps / date — plain stream extraction (no strategy needed).
# --------------------------------------------------------------------------- #


def _fraction_to_float(value: Optional[str]) -> Optional[float]:
    if not value or value in ("0/0", "N/A"):
        return None
    try:
        num, den = value.split("/")
        den = float(den)
        return float(num) / den if den else None
    except (ValueError, ZeroDivisionError):
        return None


def extract_resolution_fps(ctx: ProbeContext) -> Dict[str, Optional[float]]:
    """Width/height from the video stream; fps from avg_frame_rate → r_frame_rate."""
    vs = ctx.video_stream or {}
    width = vs.get("width")
    height = vs.get("height")
    fps = _fraction_to_float(vs.get("avg_frame_rate")) \
        or _fraction_to_float(vs.get("r_frame_rate"))
    return {
        "width": int(width) if width else None,
        "height": int(height) if height else None,
        "fps": fps,
    }


def extract_creation_time(ctx: ProbeContext) -> Optional[str]:
    """Best embedded recording timestamp (Apple's is timezone-aware)."""
    return (
        ctx.ftag("com.apple.quicktime.creationdate")
        or ctx.ftag("creation_time")
    )


# --------------------------------------------------------------------------- #
# Orchestration — populate a Video from an ffprobe blob.
# --------------------------------------------------------------------------- #


def populate_video(video, probe_json: Dict[str, Any], geocoder=None,
                   place_gazetteer=None) -> None:
    """Apply every strategy and write the results onto ``video`` in place.

    If a ``geocoder`` (a :class:`tools.geocoding.Geocoder`) is supplied and the
    video has a GPS position, ``video.country`` is reverse-geocoded from it. If a
    ``place_gazetteer`` (a :class:`tools.geocoding.PlaceGazetteer`) is supplied
    and the video has *no* GPS tag, an approximate location is inferred from a
    country/state name in the folder path (``video.location_source`` records the
    provenance, e.g. ``"apple"``, ``"android"`` or ``"path:country:greece"``).
    """
    ctx = build_context(probe_json, video.path)

    dev = detect_device(ctx)
    video.device = dev.device
    video.make = dev.make
    video.model = dev.model

    extra = [PathLocationStrategy(place_gazetteer)] if place_gazetteer is not None else None
    loc = extract_location(ctx, extra)
    video.latitude = loc.latitude
    video.longitude = loc.longitude
    video.altitude = loc.altitude
    video.location_accuracy_m = loc.accuracy_m
    video.location_source = loc.source
    if loc.raw:
        video.location = loc.raw

    country = loc.country
    if country is None and geocoder is not None \
            and loc.latitude is not None and loc.longitude is not None:
        country = geocoder.country(loc.latitude, loc.longitude)
    video.country = country

    res = extract_resolution_fps(ctx)
    video.width = res["width"]
    video.height = res["height"]
    video.fps = res["fps"]

    ct = extract_creation_time(ctx)
    if ct:
        video.creation_time = ct

    dur = (ctx.format or {}).get("duration")
    if dur:
        try:
            video.duration_sec = float(dur)
        except (TypeError, ValueError):
            pass


# --------------------------------------------------------------------------- #
# ffprobe runner (lazy — only import static_ffmpeg when actually probing).
# --------------------------------------------------------------------------- #


def run_ffprobe(path: str, timeout: int = 60) -> Optional[Dict[str, Any]]:
    """Run ffprobe on ``path`` and return the parsed JSON, or ``None`` on failure."""
    import json
    import shutil
    import subprocess

    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        try:
            import static_ffmpeg
            static_ffmpeg.add_paths()
            ffprobe = shutil.which("ffprobe")
        except Exception:
            ffprobe = None
    if ffprobe is None:
        return None

    try:
        out = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", path],
            capture_output=True, text=True, timeout=timeout,
        )
        if out.returncode != 0 or not out.stdout:
            return None
        return json.loads(out.stdout)
    except Exception:
        return None
