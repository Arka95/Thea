"""
tools/tests/test_video_meta_strategy.py — device + location extraction strategies.

Uses synthetic ffprobe-shaped dicts modelled on real D:\\ samples (Apple, Pixel,
GoPro, DJI, Samsung, LG/other-Android) so no real files are needed.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from tools.models.video import Video
from tools.video_meta_strategy import (
    build_context,
    detect_device,
    extract_location,
    extract_resolution_fps,
    parse_iso6709,
    populate_video,
)


def probe(fmt_tags=None, streams=None, duration=None):
    fmt = {"tags": fmt_tags or {}}
    if duration is not None:
        fmt["duration"] = duration
    return {"format": fmt, "streams": streams or []}


def vstream(w=1920, h=1080, avg="30000/1001", r="30000/1001", tags=None):
    return {"codec_type": "video", "width": w, "height": h,
            "avg_frame_rate": avg, "r_frame_rate": r, "tags": tags or {}}


# --------------------------- device detection ----------------------------- #

def test_device_apple():
    p = probe(fmt_tags={
        "com.apple.quicktime.make": "Apple",
        "com.apple.quicktime.model": "iPhone 15 Plus",
    }, streams=[vstream(tags={"handler_name": "Core Media Video", "encoder": "HEVC"})])
    d = detect_device(build_context(p, "IMG_6324.MOV"))
    assert d.make == "Apple"
    assert d.model == "iPhone 15 Plus"
    assert d.device == "Apple iPhone 15 Plus"


def test_device_gopro_by_handler():
    p = probe(streams=[vstream(tags={"handler_name": "GoPro H.265", "encoder": "GoPro H.265 encoder"})])
    d = detect_device(build_context(p, "GX010939.MP4"))
    assert d.device == "GoPro"


def test_device_gopro_by_filename_only():
    d = detect_device(build_context(probe(), "GX011300.mp4"))
    assert d.device == "GoPro"


def test_device_dji_by_handler():
    p = probe(streams=[vstream(tags={"handler_name": "DJI.AVC"})])
    d = detect_device(build_context(p, "DJI_0308.MP4"))
    assert d.device == "DJI"


def test_device_samsung_by_tag():
    p = probe(fmt_tags={"com.android.version": "16", "com.samsung.android.utc_offset": "+0800"})
    d = detect_device(build_context(p, "20260222_192541.mp4"))
    assert d.device == "Samsung"


def test_device_pixel_by_filename():
    p = probe(fmt_tags={"com.android.capture.fps": "30.000000"})
    d = detect_device(build_context(p, "PXL_20211002_114353463.mp4"))
    assert d.device == "Google Pixel"
    assert d.make == "Google"


def test_device_pixel_survives_android_trash_prefix():
    # Android trash bin renames to ".trashed-<epoch>-<original>"; Pixel must still win
    p = probe(fmt_tags={"com.android.version": "12", "com.android.capture.fps": "60"})
    d = detect_device(build_context(p, ".trashed-1637330870-PXL_20211020_101010.mp4"))
    assert d.device == "Google Pixel"


def test_device_generic_make_model_lg():
    p = probe(fmt_tags={"make": "LG_Electronics", "model": "KF240"})
    d = detect_device(build_context(p, "1006111047-00.3gp"))
    assert d.make == "LG_Electronics"
    assert d.model == "KF240"
    assert d.device == "LG_Electronics KF240"


def test_device_other_android():
    p = probe(fmt_tags={"com.android.version": "6.0.1"})
    d = detect_device(build_context(p, "VID_20170518_065346.mp4"))
    assert d.device == "Android"


def test_device_unknown():
    d = detect_device(build_context(probe(), "clip.mp4"))
    assert d.device is None


def test_device_priority_apple_beats_filename():
    # Apple tags present but filename looks like GoPro -> Apple wins (higher priority)
    p = probe(fmt_tags={"com.apple.quicktime.make": "Apple",
                        "com.apple.quicktime.model": "iPhone 13"})
    d = detect_device(build_context(p, "GX010001.mp4"))
    assert d.make == "Apple"


# --------------------------- location extraction -------------------------- #

def test_parse_iso6709_variants():
    assert parse_iso6709("+22.6188+88.4170/") == {
        "latitude": 22.6188, "longitude": 88.417, "altitude": None}
    assert parse_iso6709("+17.2546+078.6767+509.629/") == {
        "latitude": 17.2546, "longitude": 78.6767, "altitude": 509.629}
    assert parse_iso6709("-33.8568+151.2153/")["latitude"] == -33.8568
    assert parse_iso6709(None) is None
    assert parse_iso6709("garbage") is None


@pytest.mark.parametrize(
    "value",
    [
        "+0.0000+0.0000",
        "-0.0+000.0/",
        "+91.0+000.0/",
        "+00.0-181.0/",
        "+22.6188+88.4170/garbage",
    ],
)
def test_parse_iso6709_rejects_unusable_camera_gps(value):
    assert parse_iso6709(value) is None


@pytest.mark.parametrize(
    "value,latitude,longitude",
    [
        ("+0.0+15.0/", 0.0, 15.0),
        ("+17.0+0.0/", 17.0, 0.0),
        ("-90.0+180.0/", -90.0, 180.0),
    ],
)
def test_parse_iso6709_preserves_valid_boundary_coordinates(value, latitude, longitude):
    parsed = parse_iso6709(value)
    assert parsed["latitude"] == latitude
    assert parsed["longitude"] == longitude


def test_location_apple_with_altitude_and_accuracy():
    p = probe(fmt_tags={
        "com.apple.quicktime.location.ISO6709": "+17.2546+078.6767+509.629/",
        "com.apple.quicktime.location.accuracy.horizontal": "4.683887",
    })
    loc = extract_location(build_context(p, "IMG.MOV"))
    assert loc.latitude == 17.2546
    assert loc.longitude == 78.6767
    assert loc.altitude == 509.629
    assert loc.accuracy_m == pytest.approx(4.683887)
    assert loc.source == "apple"


def test_location_android_location_tag():
    p = probe(fmt_tags={"location": "+22.6188+88.4170/", "location-eng": "+22.6188+88.4170/"})
    loc = extract_location(build_context(p, "PXL.mp4"))
    assert loc.latitude == 22.6188
    assert loc.longitude == 88.417
    assert loc.altitude is None
    assert loc.source == "android"


def test_location_absent():
    loc = extract_location(build_context(probe(), "clip.mp4"))
    assert loc.latitude is None and loc.longitude is None


# --------------------------- resolution / fps ----------------------------- #

def test_resolution_and_fps():
    p = probe(streams=[vstream(w=3840, h=2160, avg="30000/1001", r="30000/1001")])
    res = extract_resolution_fps(build_context(p, "4k.mp4"))
    assert res["width"] == 3840
    assert res["height"] == 2160
    assert res["fps"] == pytest.approx(29.97, abs=0.01)


def test_fps_prefers_avg_over_r():
    p = probe(streams=[vstream(avg="141400/9591", r="179/12")])
    res = extract_resolution_fps(build_context(p, "vfr.3gp"))
    assert res["fps"] == pytest.approx(14.74, abs=0.05)


def test_fps_handles_zero_rate():
    p = probe(streams=[vstream(avg="0/0", r="30/1")])
    res = extract_resolution_fps(build_context(p, "x.mp4"))
    assert res["fps"] == pytest.approx(30.0)


# --------------------------- full populate -------------------------------- #

def test_populate_video_end_to_end():
    p = probe(
        fmt_tags={
            "com.apple.quicktime.make": "Apple",
            "com.apple.quicktime.model": "iPhone 15 Plus",
            "com.apple.quicktime.location.ISO6709": "+17.2546+078.6767+509.629/",
            "com.apple.quicktime.location.accuracy.horizontal": "3.8",
            "com.apple.quicktime.creationdate": "2024-09-14T11:48:10+0530",
        },
        streams=[vstream(w=3840, h=2160, tags={"handler_name": "Core Media Video"})],
        duration="12.34",
    )
    v = Video(path="D:/IMG_6324.MOV", name="IMG_6324.MOV")
    populate_video(v, p)

    assert v.device == "Apple iPhone 15 Plus"
    assert v.make == "Apple"
    assert v.latitude == 17.2546 and v.longitude == 78.6767 and v.altitude == 509.629
    assert v.location_accuracy_m == pytest.approx(3.8)
    assert v.location == "+17.2546+078.6767+509.629/"
    assert v.width == 3840 and v.height == 2160
    assert v.creation_time == "2024-09-14T11:48:10+0530"
    assert v.duration_sec == pytest.approx(12.34)


# --------------------------- geocoding wiring ----------------------------- #

class _FakeGeocoder:
    """Records calls; returns a fixed country without loading any dataset."""

    def __init__(self, result="Greece"):
        self.result = result
        self.calls = []

    def country(self, latitude, longitude):
        self.calls.append((latitude, longitude))
        return self.result


def test_populate_video_geocodes_country_when_located():
    p = probe(fmt_tags={"location": "+37.9838+023.7275/"})
    v = Video(path="D:/clip.mp4", name="clip.mp4")
    geo = _FakeGeocoder("Greece")
    populate_video(v, p, geocoder=geo)
    assert v.country == "Greece"
    assert geo.calls == [(37.9838, 23.7275)]


def test_populate_video_skips_geocoding_without_coords():
    p = probe(fmt_tags={"com.apple.quicktime.make": "Apple"})  # no location
    v = Video(path="D:/clip.mp4", name="clip.mp4")
    geo = _FakeGeocoder("Greece")
    populate_video(v, p, geocoder=geo)
    assert v.country is None
    assert geo.calls == []  # geocoder never invoked


@pytest.mark.parametrize("tag", ["location", "com.apple.quicktime.location.ISO6709"])
def test_populate_video_does_not_geocode_zero_placeholders(tag):
    video = Video(path="clip.mp4", name="clip.mp4")
    geocoder = _FakeGeocoder("Ghana")
    populate_video(video, probe(fmt_tags={tag: "+0.0000+0.0000"}), geocoder=geocoder)
    assert video.latitude is None and video.longitude is None
    assert video.country is None
    assert geocoder.calls == []


def test_populate_video_no_geocoder_leaves_country_none():
    p = probe(fmt_tags={"location": "+37.9838+023.7275/"})
    v = Video(path="D:/clip.mp4", name="clip.mp4")
    populate_video(v, p)  # geocoder omitted
    assert v.country is None


# --------------------------- path location fallback ----------------------- #

from tools.geocoding import PlaceHit


class _FakeGazetteer:
    """Name -> PlaceHit table; records lookups. No dataset loaded."""

    def __init__(self, table):
        self.table = {k.lower(): v for k, v in table.items()}
        self.calls = []

    def lookup(self, name):
        self.calls.append(name)
        return self.table.get(name.lower())


def test_path_fallback_infers_country_from_folder():
    gaz = _FakeGazetteer({"greece": PlaceHit(38.9, 23.2, "Greece", "country", "Greece")})
    v = Video(path="D:/Videos/Trip to Greece/clip.mp4", name="clip.mp4")
    populate_video(v, probe(), place_gazetteer=gaz)  # empty probe -> no GPS
    assert v.latitude == 38.9 and v.longitude == 23.2
    assert v.country == "Greece"
    assert v.location_source == "path:country:Greece"


def test_path_fallback_state_sets_parent_country():
    gaz = _FakeGazetteer(
        {"west bengal": PlaceHit(23.49, 88.12, "India", "state", "West Bengal")})
    v = Video(path="D:/India/West Bengal/clip.mp4", name="clip.mp4")
    populate_video(v, probe(), place_gazetteer=gaz)
    assert (v.latitude, v.longitude) == (23.49, 88.12)
    assert v.country == "India"
    assert v.location_source == "path:state:West Bengal"


def test_gps_location_beats_path_fallback():
    gaz = _FakeGazetteer({"greece": PlaceHit(38.9, 23.2, "Greece", "country", "Greece")})
    p = probe(fmt_tags={"location": "+12.9716+077.5946/"})  # real GPS present
    v = Video(path="D:/Greece/clip.mp4", name="clip.mp4")
    populate_video(v, p, place_gazetteer=gaz)
    assert v.latitude == 12.9716  # GPS wins, not the centroid
    assert v.location_source == "android"
    assert gaz.calls == []  # path fallback never consulted when GPS exists


@pytest.mark.parametrize("tag", ["location", "com.apple.quicktime.location.ISO6709"])
@pytest.mark.parametrize("value", ["+0.0000+0.0000", "+91.0+023.0/"])
def test_unusable_gps_allows_labelled_folder_fallback(tag, value):
    gazetteer = _FakeGazetteer(
        {
            "greece": PlaceHit(38.9, 23.2, "Greece", "country", "Greece"),
        }
    )
    geocoder = _FakeGeocoder("Ghana")
    video = Video(path="D:/Greece/clip.mp4", name="clip.mp4")
    populate_video(
        video,
        probe(fmt_tags={tag: value}),
        geocoder=geocoder,
        place_gazetteer=gazetteer,
    )
    assert video.country == "Greece"
    assert (video.latitude, video.longitude) == (38.9, 23.2)
    assert video.location_source == "path:country:Greece"
    assert geocoder.calls == []


def test_path_fallback_no_match_leaves_location_empty():
    gaz = _FakeGazetteer({"greece": PlaceHit(38.9, 23.2, "Greece", "country", "Greece")})
    v = Video(path="D:/RandomFolder/holiday/clip.mp4", name="clip.mp4")
    populate_video(v, probe(), place_gazetteer=gaz)
    assert v.latitude is None and v.country is None
    assert v.location_source is None


def test_no_gazetteer_means_no_path_inference():
    v = Video(path="D:/Greece/clip.mp4", name="clip.mp4")
    populate_video(v, probe())  # no gazetteer
    assert v.latitude is None and v.country is None
    assert v.location_source is None
