"""Crop/pan behavior with no real probing, encoding, media or hardware."""

import copy
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from src.cropandpan import cropandpan as module


@pytest.fixture
def media(tmp_path, monkeypatch):
    source = tmp_path / "source's video.mp4"
    source.write_bytes(b"untouched source")
    probe = {
        "format": {"duration": "20", "start_time": "0"},
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "hevc",
                "pix_fmt": "yuv420p",
                "width": 3840,
                "height": 2160,
                "sample_aspect_ratio": "1:1",
                "duration": "20",
                "avg_frame_rate": "30/1",
                "start_time": "0",
            },
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
                "sample_rate": "48000",
                "channels": 2,
            },
        ],
    }
    state = SimpleNamespace(
        source=str(source),
        output=str(tmp_path / "result.mp4"),
        data_dir=str(tmp_path / "data"),
        probe=probe,
        output_probe=None,
        commands=[],
        alter_output=lambda probe: None,
    )

    def fake_probe(path):
        return copy.deepcopy(state.probe if path == state.source else state.output_probe)

    def fake_run(command, **kwargs):
        state.commands.append(command)
        video_filter = command[command.index("-vf") + 1]
        width, height = map(int, re.search(r"crop=w=(\d+):h=(\d+)", video_filter).groups())
        state.output_probe = copy.deepcopy(state.probe)
        stream = next(
            item
            for item in state.output_probe["streams"]
            if item["codec_type"] == "video" and not item.get("disposition", {}).get("attached_pic")
        )
        state.output_probe["streams"] = [stream] + [
            item for item in state.output_probe["streams"] if item["codec_type"] == "audio"
        ]
        stream.update(width=width, height=height, tags={}, side_data_list=[])
        stream.setdefault("duration", "20")
        if "-t" in command:
            stream["duration"] = command[command.index("-t") + 1]
            state.output_probe["format"]["duration"] = stream["duration"]
        state.alter_output(state.output_probe)
        Path(command[-1]).write_bytes(b"rendered video")
        return SimpleNamespace(returncode=0, stderr="")

    state.run = fake_run
    monkeypatch.setattr(module, "run_ffprobe", fake_probe)
    monkeypatch.setattr(module, "get_ffmpeg_exe", lambda: "ffmpeg")
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module, "resolve_data_dir", lambda source: state.data_dir)
    return state


def _filter(media):
    command = media.commands[0]
    return command[command.index("-vf") + 1]


def _position_at(media, time):
    x, y = re.search(r":x=(.*?):y=(.*?):exact=1", _filter(media)).groups()
    scope = {"__builtins__": {}, "min": min, "max": max, "t": time}
    return tuple(eval(expression.strip("'"), scope) for expression in (x, y))


def test_crop_uses_width_height_and_top_left_not_center(media):
    result = module.crop(media.source, 1000, 600, 100, 200, output_path=media.output)
    assert _filter(media) == "crop=w=1000:h=600:x=100:y=200:exact=1"
    assert result == media.output
    assert Path(result).read_bytes() == b"rendered video"
    assert Path(media.source).read_bytes() == b"untouched source"
    assert not list(Path(media.output).parent.glob(".thea-cropandpan-*"))


def test_crop_defaults_to_configured_output_directory(media):
    result = module.crop(media.source, 1000, 600, 0, 0)
    assert Path(result).parent == Path(media.data_dir) / "cropandpan"
    assert Path(result).name.startswith("source's video_crop_")


def test_explicit_output_bypasses_configured_unavailable_drive(media, monkeypatch):
    def fail(source):
        raise AssertionError("Should not resolve configured data directory")

    monkeypatch.setattr(module, "resolve_data_dir", fail)
    assert module.crop(media.source, 1000, 600, 0, 0, output_path=media.output) == media.output


def test_center_crop_positions_the_rectangle(media):
    module.centercrop(media.source, 1000, 600, output_path=media.output)
    assert _position_at(media, 0) == (1420, 780)


@pytest.mark.parametrize("size", [(4000, 600), (1000, 2200)])
def test_oversized_center_crop_reports_frame_bounds(media, size):
    with pytest.raises(ValueError, match="outside"):
        module.centercrop(media.source, *size, output_path=media.output)
    assert not media.commands


@pytest.mark.parametrize(
    "width,height,x,y",
    [
        (0, 600, 0, 0),
        (-2, 600, 0, 0),
        (1000.0, 600, 0, 0),
        (True, 600, 0, 0),
        (1000, None, 0, 0),
        (1000, 600, -1, 0),
        (1000, 600, 0, -1),
        (1000, 600, 0.5, 0),
        (1000, 600, float("inf"), 0),
        (1000, 600, 10**400, 0),
        (1000, 600, 2841, 0),
        (1000, 600, 0, 1561),
        (4000, 600, 0, 0),
        (1001, 600, 0, 0),
    ],
)
def test_invalid_rectangles_are_rejected_before_encoding(media, width, height, x, y):
    with pytest.raises((TypeError, ValueError)):
        module.crop(media.source, width, height, x, y, output_path=media.output)
    assert not media.commands
    assert not Path(media.output).exists()


@pytest.mark.parametrize("operation", ["crop", "center", "ratio", "pan"])
def test_no_op_returns_original_without_creating_output(media, monkeypatch, operation):
    def fail(source):
        raise AssertionError("A no-op must not resolve the data directory")

    monkeypatch.setattr(module, "resolve_data_dir", fail)
    calls = {
        "crop": lambda: module.crop(media.source, 3840, 2160, 0, 0, output_path=media.output),
        "center": lambda: module.centercrop(media.source, 3840, 2160),
        "ratio": lambda: module.ratiocrop(media.source, 16, 9),
        "pan": lambda: module.pan(media.source, ratiox=16, ratioy=9),
    }
    assert calls[operation]() == media.source
    assert not media.commands
    assert not Path(media.output).exists()


@pytest.mark.parametrize(
    "ratiox,ratioy,expected_size,expected_position",
    [(1, 1, (2160, 2160), (840, 0)), (9, 16, (1206, 2144), (1317, 8))],
)
def test_ratio_crop_fits_exact_codec_aligned_dimensions(
    media, ratiox, ratioy, expected_size, expected_position
):
    module.ratiocrop(media.source, ratiox, ratioy, output_path=media.output)
    assert f"w={expected_size[0]}:h={expected_size[1]}" in _filter(media)
    assert _position_at(media, 0) == expected_position
    assert expected_size[0] * ratioy == expected_size[1] * ratiox


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, None, "9"])
def test_invalid_ratio_is_rejected(media, value):
    with pytest.raises((TypeError, ValueError)):
        module.ratiocrop(media.source, value, 16, output_path=media.output)
    assert not media.commands


def test_ratio_that_cannot_fit_is_rejected(media):
    with pytest.raises(ValueError, match="cannot fit"):
        module.ratiocrop(media.source, 10000, 1, output_path=media.output)
    assert not media.commands


def test_display_aspect_ratio_includes_sample_aspect_ratio(media):
    media.probe["streams"][0].update(width=1440, height=1080, sample_aspect_ratio="4:3")
    assert module.ratiocrop(media.source, 16, 9) == media.source
    module.ratiocrop(media.source, 1, 1, output_path=media.output)
    assert "w=810:h=1080" in _filter(media)
    assert _position_at(media, 0) == (315, 0)


def test_crop_uses_autorotated_frame_dimensions(media):
    media.probe["streams"][0]["side_data_list"] = [{"rotation": -90}]
    module.centercrop(media.source, 1080, 1920, output_path=media.output)
    assert _position_at(media, 0) == (540, 960)
    assert "-noautorotate" not in media.commands[0]


def test_rotated_sample_aspect_ratio_is_inverted(media):
    media.probe["streams"][0].update(
        width=1440, height=1080, sample_aspect_ratio="4:3", tags={"rotate": "90"}
    )
    assert module.ratiocrop(media.source, 9, 16) == media.source
    assert not media.commands


def test_default_pan_traverses_portrait_viewport_for_video_duration(media):
    module.pan(media.source, output_path=media.output)
    assert "w=1206:h=2144" in _filter(media)
    assert _position_at(media, 0) == (0, 8)
    assert _position_at(media, 10) == (1317, 8)
    assert _position_at(media, 20) == (2634, 8)
    command = media.commands[0]
    assert command[command.index("-t") + 1] == "20"


def test_duration_only_pan_trims_output_without_respeeding(media):
    module.pan(media.source, duration=5, output_path=media.output)
    assert _position_at(media, 5) == (2634, 8)
    command = media.commands[0]
    assert command[command.index("-t") + 1] == "5"
    assert "-r" not in command and "setpts" not in _filter(media)
    assert command[command.index("-fps_mode") + 1] == "passthrough"


@pytest.mark.parametrize(
    "start,end",
    [
        ((0, 780), (2840, 780)),
        ((2840, 780), (0, 780)),
        ((1420, 1560), (1420, 0)),
        ((0, 0), (2840, 1560)),
        ((2840, 1560), (0, 0)),
    ],
)
def test_pan_directions_and_diagonals_interpolate_both_axes(media, start, end):
    module.pan(media.source, 1000, 600, *start, *end, 5, output_path=media.output)
    assert _position_at(media, 0) == start
    assert _position_at(media, 2.5) == tuple((first + last) / 2 for first, last in zip(start, end))
    assert _position_at(media, 5) == end


def test_y_only_pan_keeps_x_centered(media):
    module.pan(media.source, 1000, 600, starty=1560, endy=0, duration=5, output_path=media.output)
    assert _position_at(media, 0) == (1420, 1560)
    assert _position_at(media, 5) == (1420, 0)


def test_default_pan_uses_vertical_travel_for_a_tall_source(media):
    media.probe["streams"][0].update(width=1080, height=2400)
    module.pan(media.source, output_path=media.output)
    assert "w=1080:h=1920" in _filter(media)
    assert _position_at(media, 0) == (0, 0)
    assert _position_at(media, 20) == (0, 480)


def test_pan_accepts_ratio_instead_of_pixel_dimensions(media):
    module.pan(media.source, ratiox=1, ratioy=1, duration=5, output_path=media.output)
    assert "w=2160:h=2160" in _filter(media)
    assert _position_at(media, 5) == (1680, 0)


@pytest.mark.parametrize(
    "options",
    [
        {"resolutionx": 1000},
        {"resolutiony": 600},
        {"ratiox": 9},
        {"ratioy": 16},
        {"resolutionx": 1000, "resolutiony": 600, "ratiox": 1, "ratioy": 1},
        {"startx": -1},
        {"endx": 3000},
        {"endy": 2000},
        {"duration": 0},
        {"duration": -1},
        {"duration": float("inf")},
        {"duration": float("nan")},
        {"duration": True},
        {"duration": 21},
    ],
)
def test_invalid_pan_options_are_rejected_before_encoding(media, options):
    with pytest.raises((TypeError, ValueError)):
        module.pan(media.source, output_path=media.output, **options)
    assert not media.commands


def test_pan_needs_known_duration_but_static_crop_does_not(media):
    media.probe["format"].pop("duration")
    media.probe["streams"][0].pop("duration")
    with pytest.raises(ValueError, match="known positive"):
        module.pan(media.source, output_path=media.output)
    module.crop(media.source, 1000, 600, 0, 0, output_path=media.output)
    assert "-t" not in media.commands[0]


def test_pan_uses_video_duration_not_a_longer_audio_container_duration(media):
    media.probe["format"]["duration"] = "30"
    with pytest.raises(ValueError, match="exceed"):
        module.pan(media.source, duration=25, output_path=media.output)


def test_pan_time_is_relative_to_video_start_on_common_timestamp_origin(media):
    media.probe["format"]["start_time"] = "10"
    media.probe["streams"][0]["start_time"] = "10.5"
    module.pan(media.source, duration=5, output_path=media.output)
    assert _position_at(media, 0.5) == (0, 8)
    assert _position_at(media, 3) == (1317, 8)
    assert "-copyts" in media.commands[0] and "-start_at_zero" in media.commands[0]
    assert media.commands[0][media.commands[0].index("-ss") + 1] == "0.5"


def test_full_frame_pan_with_shorter_duration_still_trims(media):
    module.pan(media.source, ratiox=16, ratioy=9, duration=5, output_path=media.output)
    assert Path(media.output).exists()
    assert media.commands[0][media.commands[0].index("-t") + 1] == "5"


@pytest.mark.parametrize("rate", [None, "N/A", "0/0"])
def test_missing_frame_rate_does_not_prevent_cropping(media, rate):
    media.probe["streams"][0]["avg_frame_rate"] = rate
    module.crop(media.source, 1000, 600, 0, 0, output_path=media.output)
    assert Path(media.output).exists()


@pytest.mark.parametrize(
    "codec,encoder",
    [("hevc", "libx265"), ("h264", "libx264"), ("vp9", "libvpx-vp9"), ("ffv1", "ffv1")],
)
def test_encoding_preserves_source_codec_pixel_format_and_audio(media, codec, encoder):
    media.probe["streams"][0]["codec_name"] = codec
    module.crop(media.source, 1000, 600, 0, 0, output_path=media.output)
    command = media.commands[0]
    assert command[command.index("-c:v") + 1] == encoder
    assert command[command.index("-pix_fmt") + 1] == "+yuv420p"
    assert command[command.index("-c:a") + 1] == "copy"
    assert "0:a?" in command


def test_audio_free_video_is_supported(media):
    media.probe["streams"] = media.probe["streams"][:1]
    module.crop(media.source, 1000, 600, 0, 0, output_path=media.output)
    assert Path(media.output).exists()


@pytest.mark.parametrize("target", ["existing_output", "source"])
def test_existing_destination_or_source_is_never_overwritten(media, target):
    output = Path(media.source if target == "source" else media.output)
    if target == "existing_output":
        output.write_bytes(b"existing destination")
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        module.crop(media.source, 1000, 600, 0, 0, output_path=output)
    assert output.read_bytes() == before
    assert not media.commands


def test_ffmpeg_failure_removes_partial_output(media, monkeypatch):
    def fail(command, **kwargs):
        Path(command[-1]).write_bytes(b"partial output")
        return SimpleNamespace(returncode=1, stderr="Unknown encoder")

    monkeypatch.setattr(module.subprocess, "run", fail)
    with pytest.raises(RuntimeError, match="source codec hevc"):
        module.pan(media.source, duration=5, output_path=media.output)
    assert not Path(media.output).exists()
    assert not list(Path(media.output).parent.glob(".thea-cropandpan-*"))


@pytest.mark.parametrize("invalid", ["width", "codec", "pixel_format", "sar", "audio", "duration"])
def test_bad_encoded_output_is_discarded(media, invalid):
    def alter(probe):
        stream = probe["streams"][0]
        if invalid == "width":
            stream["width"] = 1020
        elif invalid == "codec":
            stream["codec_name"] = "h264"
        elif invalid == "pixel_format":
            stream["pix_fmt"] = "yuv420p10le"
        elif invalid == "sar":
            stream["sample_aspect_ratio"] = "4:3"
        elif invalid == "audio":
            probe["streams"].pop()
        else:
            stream["duration"] = "2"

    media.alter_output = alter
    with pytest.raises(RuntimeError):
        module.pan(media.source, duration=5, output_path=media.output)
    assert not Path(media.output).exists()
    assert not list(Path(media.output).parent.glob(".thea-cropandpan-*"))


def test_source_change_discards_output(media, monkeypatch):
    def change(command, **kwargs):
        result = media.run(command, **kwargs)
        Path(media.source).write_bytes(b"external source change")
        return result

    monkeypatch.setattr(module.subprocess, "run", change)
    with pytest.raises(RuntimeError, match="source changed"):
        module.crop(media.source, 1000, 600, 0, 0, output_path=media.output)
    assert not Path(media.output).exists()


def test_concurrently_created_destination_is_preserved(media, monkeypatch):
    def race(command, **kwargs):
        result = media.run(command, **kwargs)
        Path(media.output).write_bytes(b"another writer")
        return result

    monkeypatch.setattr(module.subprocess, "run", race)
    with pytest.raises(FileExistsError):
        module.crop(media.source, 1000, 600, 0, 0, output_path=media.output)
    assert Path(media.output).read_bytes() == b"another writer"


def test_missing_input_is_a_clear_error(media):
    with pytest.raises(FileNotFoundError):
        module.crop(str(Path(media.source).with_name("missing.mp4")), 1000, 600, 0, 0)


def test_audio_only_input_is_rejected(media):
    media.probe["streams"] = media.probe["streams"][1:]
    with pytest.raises(ValueError, match="video codec and frame"):
        module.pan(media.source, output_path=media.output)
    assert not media.commands


def test_cover_art_is_not_selected_as_the_video(media):
    stream = media.probe["streams"][0]
    stream["index"] = 2
    media.probe["streams"].insert(
        0, {"index": 0, "codec_type": "video", "disposition": {"attached_pic": 1}}
    )
    module.crop(media.source, 1000, 600, 0, 0, output_path=media.output)
    assert media.commands[0][media.commands[0].index("-map") + 1] == "0:2"
