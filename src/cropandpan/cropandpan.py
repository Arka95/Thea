"""Crop and pan without changing source files or playback speed."""

import math
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
from pathlib import Path

from tools.video_meta_strategy import run_ffprobe
from utils.ffmpeg import get_ffmpeg_exe
from utils.metrics import track
from utils.settings import get_cropandpan_dir, resolve_data_dir

_ENCODERS = {
    "h264": "libx264",
    "hevc": "libx265",
    "vp8": "libvpx",
    "vp9": "libvpx-vp9",
    "av1": "libaom-av1",
    "prores": "prores_ks",
}


@dataclass(frozen=True)
class _Video:
    path: Path
    probe: dict
    stream: dict
    width: int
    height: int
    sar: Fraction
    duration: float
    version: tuple


def _version(path: Path) -> tuple:
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


def _number(value, name: str, *, positive: bool = True) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number.")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or (value <= 0 if positive else value < 0):
        raise ValueError(f"{name} must be {'positive' if positive else 'nonnegative'} and finite.")
    return float(value)


def _pixel(value, name: str, *, positive: bool = True) -> int:
    _number(value, name, positive=positive)
    if not isinstance(value, int):
        raise TypeError(f"{name} must be an integer pixel value.")
    return value


def _seconds(value) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0
    return value if math.isfinite(value) and value > 0 else 0


def _read_video(video) -> _Video:
    path = Path(video).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Input video not found: {path}")
    version = _version(path)
    probe = run_ffprobe(str(path))
    streams = probe.get("streams", []) if probe else []
    stream = next(
        (
            item
            for item in streams
            if item.get("codec_type") == "video"
            and not item.get("disposition", {}).get("attached_pic")
        ),
        None,
    )
    if not stream or not stream.get("codec_name") or not stream.get("pix_fmt"):
        raise ValueError(f"Cannot read video codec and frame metadata: {path}")
    width = _pixel(stream.get("width"), "source width")
    height = _pixel(stream.get("height"), "source height")
    try:
        sar = Fraction(str(stream.get("sample_aspect_ratio", "1:1")).replace(":", "/"))
        if sar <= 0:
            sar = Fraction(1)
    except (ValueError, ZeroDivisionError):
        sar = Fraction(1)
    rotation = stream.get("tags", {}).get("rotate", 0)
    for data in stream.get("side_data_list", []):
        if "rotation" in data:
            rotation = data["rotation"]
            break
    try:
        rotation = float(rotation) % 360
    except (TypeError, ValueError):
        raise ValueError("Invalid source rotation metadata.") from None
    if not math.isfinite(rotation) or rotation % 90:
        raise ValueError("Cropping requires source rotation to be a multiple of 90 degrees.")
    if rotation in (90, 270):
        width, height, sar = height, width, 1 / sar
    duration = _seconds(stream.get("duration")) or _seconds(probe.get("format", {}).get("duration"))
    return _Video(path, probe, stream, width, height, sar, duration, version)


def _alignment(source: _Video) -> tuple[int, int]:
    pixel_format = source.stream["pix_fmt"]
    if "420" in pixel_format or pixel_format.startswith(("nv12", "nv21", "p010", "p012", "p016")):
        return 2, 2
    if "422" in pixel_format or pixel_format.startswith(("nv16", "p210", "p216")):
        return 2, 1
    if "440" in pixel_format:
        return 1, 2
    if "411" in pixel_format:
        return 4, 1
    if "410" in pixel_format:
        return 4, 4
    return 1, 1


def _rectangle(source: _Video, width: int, height: int, x: int, y: int):
    _pixel(width, "width")
    _pixel(height, "height")
    _pixel(x, "x", positive=False)
    _pixel(y, "y", positive=False)
    if x + width > source.width or y + height > source.height:
        raise ValueError(
            f"Crop rectangle ({width}x{height} at {x},{y}) is outside "
            f"the {source.width}x{source.height} video frame."
        )


def _ratio_size(source: _Video, ratiox, ratioy) -> tuple[int, int]:
    ratio = Fraction(str(ratiox)) / Fraction(str(ratioy)) / source.sar
    if Fraction(source.width, source.height) == ratio:
        return source.width, source.height
    width, height = ratio.numerator, ratio.denominator
    step_x, step_y = _alignment(source)
    multiple = math.lcm(step_x // math.gcd(width, step_x), step_y // math.gcd(height, step_y))
    scale = min(source.width // width, source.height // height) // multiple * multiple
    if scale == 0:
        raise ValueError("Aspect ratio cannot fit a codec-compatible rectangle inside this video.")
    return width * scale, height * scale


def _audio_signature(probe: dict) -> list:
    return [
        tuple(stream.get(key) for key in ("codec_name", "sample_rate", "channels"))
        for stream in probe.get("streams", [])
        if stream.get("codec_type") == "audio"
    ]


def _start_offset(source: _Video) -> float:
    try:
        offset = float(source.stream.get("start_time", 0)) - float(
            source.probe.get("format", {}).get("start_time", 0)
        )
    except (TypeError, ValueError):
        offset = 0
    return max(offset, 0) if math.isfinite(offset) else 0


def _position(start: int, end: int, duration: float, source: _Video) -> str:
    if start == end:
        return str(start)
    offset = _start_offset(source)
    return f"'{start}+({end-start})*min(max((t-({offset:.12g}))/{duration:.12g},0),1)'"


def _render(source, width, height, start, end, duration, operation, output_path) -> str:
    _rectangle(source, width, height, *start)
    _rectangle(source, width, height, *end)
    if (width, height) == (source.width, source.height) and start == end == (0, 0):
        container_duration = _seconds(source.probe.get("format", {}).get("duration"))
        if duration is None or duration == source.duration == container_duration:
            return str(source.path)
    step_x, step_y = _alignment(source)
    if width % step_x or height % step_y:
        raise ValueError(
            f"Dimensions must be multiples of {step_x}x{step_y} "
            f"for source pixel format {source.stream['pix_fmt']}; dimensions are not rounded."
        )
    if output_path is None:
        folder = Path(get_cropandpan_dir(resolve_data_dir(str(source.path))))
        name = f"{source.path.stem}_{operation}_{datetime.now().astimezone():%Y%m%d_%H%M%S_%f}"
        output = folder / f"{name}{source.path.suffix or '.mkv'}"
    else:
        output = Path(output_path).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists; refusing to overwrite: {output}")
    if not output.suffix:
        raise ValueError("The output path needs a video container extension.")
    output.parent.mkdir(parents=True, exist_ok=True)
    x = _position(start[0], end[0], duration, source)
    y = _position(start[1], end[1], duration, source)
    video_filter = f"crop=w={width}:h={height}:x={x}:y={y}:exact=1"
    codec = source.stream["codec_name"]
    with tempfile.TemporaryDirectory(prefix=".thea-cropandpan-", dir=output.parent) as temporary:
        rendered = Path(temporary) / f"result{output.suffix}"
        command = [
            get_ffmpeg_exe(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-n",
            "-copyts",
            "-start_at_zero",
            "-i",
            str(source.path),
            "-map",
            f"0:{source.stream.get('index', 0)}",
            "-map",
            "0:a?",
            "-map_metadata",
            "0",
            "-vf",
            video_filter,
            "-c:v",
            _ENCODERS.get(codec, codec),
            "-pix_fmt",
            f"+{source.stream['pix_fmt']}",
            "-c:a",
            "copy",
            "-fps_mode",
            "passthrough",
        ]
        if duration is not None:
            offset = _start_offset(source)
            if offset:
                command.extend(["-ss", f"{offset:.12g}"])
            command.extend(["-t", f"{duration:.12g}"])
        command.append(str(rendered))
        result = subprocess.run(
            command, capture_output=True, encoding="utf-8", errors="replace", check=False
        )
        if result.returncode:
            raise RuntimeError(
                f"FFmpeg {operation} failed for source codec {codec}; the encoder, pixel format "
                f"and output container must be compatible: {result.stderr[-1000:]}"
            )
        if not rendered.is_file() or rendered.stat().st_size == 0:
            raise RuntimeError("FFmpeg did not produce a nonempty video.")
        final = _read_video(rendered)
        if (final.width, final.height, final.stream["codec_name"]) != (width, height, codec):
            raise RuntimeError("Output dimensions or video codec do not match the requested crop.")
        if final.stream["pix_fmt"] != source.stream["pix_fmt"]:
            raise RuntimeError("Output pixel format does not match the source.")
        if final.sar != source.sar:
            raise RuntimeError("Output sample aspect ratio does not match the source.")
        if _audio_signature(final.probe) != _audio_signature(source.probe):
            raise RuntimeError("Output did not preserve the source audio streams.")
        expected = source.duration if duration is None else duration
        try:
            fps = float(Fraction(source.stream.get("avg_frame_rate", "0/1")))
        except (TypeError, ValueError, ZeroDivisionError):
            fps = 0
        tolerance = max(0.1, 2 / fps) if fps > 0 else 0.1
        if final.duration <= 0 or (expected and abs(final.duration - expected) > tolerance):
            raise RuntimeError("Output duration does not match the requested duration.")
        if _version(source.path) != source.version:
            raise RuntimeError("The source changed during processing; output was discarded.")
        with output.open("xb") as reservation:
            reserved = os.fstat(reservation.fileno())
        try:
            os.replace(rendered, output)
        except BaseException:
            if output.exists() and output.stat().st_ino == reserved.st_ino:
                output.unlink()
            raise
    return str(output)


@track()
def crop(video, width: int, height: int, x: int, y: int, *, output_path=None) -> str:
    """Crop width/height pixels at top-left (x, y), following FFmpeg conventions."""
    _pixel(width, "width")
    _pixel(height, "height")
    _pixel(x, "x", positive=False)
    _pixel(y, "y", positive=False)
    source = _read_video(video)
    return _render(source, width, height, (x, y), (x, y), None, "crop", output_path)


@track()
def centercrop(video, width: int, height: int, *, output_path=None) -> str:
    """Crop a rectangle centered in the displayed source frame."""
    _pixel(width, "width")
    _pixel(height, "height")
    source = _read_video(video)
    start = ((source.width - width) // 2, (source.height - height) // 2)
    return _render(source, width, height, start, start, None, "centercrop", output_path)


@track()
def ratiocrop(video, ratiox, ratioy, *, output_path=None) -> str:
    """Center the largest exact, codec-aligned display-aspect-ratio crop."""
    _number(ratiox, "ratiox")
    _number(ratioy, "ratioy")
    source = _read_video(video)
    width, height = _ratio_size(source, ratiox, ratioy)
    start = ((source.width - width) // 2, (source.height - height) // 2)
    return _render(source, width, height, start, start, None, "ratiocrop", output_path)


@track()
def pan(
    video,
    resolutionx=None,
    resolutiony=None,
    startx=None,
    starty=None,
    endx=None,
    endy=None,
    duration=None,
    *,
    ratiox=None,
    ratioy=None,
    output_path=None,
) -> str:
    """Linearly move a fixed crop between top-left endpoints, trimming to duration.

    With no dimensions/ratio, use 9:16. With no coordinates, pan horizontally
    across the frame, or vertically if only vertical travel is available.
    Explicit coordinates on just one axis keep the other axis centered.
    Duration defaults to the full video; playback speed is never changed.
    """
    dimensions = resolutionx is not None or resolutiony is not None
    ratio = ratiox is not None or ratioy is not None
    if dimensions and ratio:
        raise ValueError("Provide pixel dimensions or an aspect ratio, not both.")
    if dimensions:
        _pixel(resolutionx, "resolutionx")
        _pixel(resolutiony, "resolutiony")
    else:
        ratiox, ratioy = (ratiox, ratioy) if ratio else (9, 16)
        _number(ratiox, "ratiox")
        _number(ratioy, "ratioy")
    for name, value in (("startx", startx), ("starty", starty), ("endx", endx), ("endy", endy)):
        if value is not None:
            _pixel(value, name, positive=False)
    if duration is not None:
        duration = _number(duration, "duration")
    source = _read_video(video)
    if source.duration <= 0:
        raise ValueError("Panning requires a known positive source video duration.")
    duration = source.duration if duration is None else duration
    if duration > source.duration:
        raise ValueError("Pan duration cannot exceed the source video duration.")
    width, height = (
        (resolutionx, resolutiony) if dimensions else _ratio_size(source, ratiox, ratioy)
    )
    _rectangle(source, width, height, 0, 0)
    max_x, max_y = source.width - width, source.height - height
    has_x = startx is not None or endx is not None
    has_y = starty is not None or endy is not None
    horizontal = has_x or (not has_y and max_x > 0)
    sx, ex = (0, max_x) if horizontal else (max_x // 2, max_x // 2)
    sy, ey = (0, max_y) if has_y or not horizontal else (max_y // 2, max_y // 2)
    start = (sx if startx is None else startx, sy if starty is None else starty)
    end = (ex if endx is None else endx, ey if endy is None else endy)
    return _render(source, width, height, start, end, duration, "pan", output_path)
