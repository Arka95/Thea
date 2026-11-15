"""Merge compatible videos in order using FFmpeg stream copy."""

import math
import os
import subprocess
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path

from tools.video_meta_strategy import run_ffprobe
from utils.ffmpeg import get_ffmpeg_exe
from utils.metrics import track


def read_video_manifest(manifest_path: str) -> list[str]:
    """Read UTF-8 paths, one per line; resolve relative paths beside the manifest."""
    manifest = Path(manifest_path).resolve()
    paths = []
    for line in manifest.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        path = Path(line.strip()).expanduser()
        if not path.is_absolute():
            path = manifest.parent / path
        paths.append(str(path.resolve()))
    return paths


def _file_version(path: Path) -> tuple:
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


def _probe_video(path: Path) -> dict:
    probe = run_ffprobe(str(path))
    if not probe or not any(
        stream.get("codec_type") == "video" for stream in probe.get("streams", [])
    ):
        raise ValueError(f"Cannot read video metadata: {path}")
    return probe


def _stream_signature(probe: dict) -> tuple:
    common = ("codec_type", "codec_name", "profile", "time_base")
    video = ("width", "height", "pix_fmt", "sample_aspect_ratio", "field_order")
    audio = ("sample_rate", "channels", "channel_layout")
    signatures = []
    for stream in probe["streams"]:
        fields = common
        if stream.get("codec_type") == "video":
            fields += video
        elif stream.get("codec_type") == "audio":
            fields += audio
        signatures.append(tuple(stream.get(field) for field in fields))
    return tuple(signatures)


def _duration(probe: dict) -> float:
    try:
        value = float(probe.get("format", {}).get("duration", 0))
    except (TypeError, ValueError):
        return 0
    return value if math.isfinite(value) and value > 0 else 0


@track()
def merge_videos(video_paths: Sequence[str], output_path: str) -> dict:
    """Merge two or more compatible videos without re-encoding or overwriting.

    There is no clip-count cap. Input order and all streams are preserved.
    Incompatible codecs, stream layouts, dimensions or time bases are rejected.
    """
    if isinstance(video_paths, (str, bytes)) or len(video_paths) < 2:
        raise ValueError("Provide at least two video paths to merge.")
    inputs = [Path(path).expanduser().resolve() for path in video_paths]
    output = Path(output_path).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists; refusing to overwrite: {output}")
    if not output.suffix:
        raise ValueError("The output path needs a container extension, such as .mp4.")
    for path in inputs:
        if not path.is_file():
            raise FileNotFoundError(f"Input video not found: {path}")
    versions = [_file_version(path) for path in inputs]
    started = time.perf_counter()
    probes = [_probe_video(path) for path in inputs]
    signature = _stream_signature(probes[0])
    for path, probe in zip(inputs[1:], probes[1:]):
        if _stream_signature(probe) != signature:
            raise ValueError(
                f"Incompatible streams for lossless merging: {path}. "
                "Use clips with matching codecs, stream layouts, dimensions and time bases."
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".thea-merge-", dir=output.parent) as temporary:
        temporary = Path(temporary)
        manifest = temporary / "inputs.ffconcat"
        lines = ["ffconcat version 1.0"]
        for path in inputs:
            escaped = str(path).replace("'", "'\\''")
            lines.append(f"file '{escaped}'")
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        merged = temporary / f"merged{output.suffix}"
        command = [
            get_ffmpeg_exe(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-n",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest),
            "-map",
            "0",
            "-c",
            "copy",
            str(merged),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode:
            raise RuntimeError(
                f"FFmpeg merge failed (exit {result.returncode}): {result.stderr[-1000:]}"
            )
        if not merged.is_file() or merged.stat().st_size == 0:
            raise RuntimeError("FFmpeg did not produce a nonempty merged video.")
        final_probe = _probe_video(merged)
        first_video = next(
            stream for stream in probes[0]["streams"] if stream["codec_type"] == "video"
        )
        video = next(stream for stream in final_probe["streams"] if stream["codec_type"] == "video")
        if any(video.get(key) != first_video.get(key) for key in ("codec_name", "width", "height")):
            raise RuntimeError("Merged output changed the video codec or resolution.")
        duration = _duration(final_probe)
        if duration == 0 or len(final_probe["streams"]) != len(probes[0]["streams"]):
            raise RuntimeError("Merged output failed stream or duration validation.")
        source_durations = [_duration(probe) for probe in probes]
        if all(source_durations):
            expected = sum(source_durations)
            if abs(duration - expected) > max(1.0, expected * 0.01):
                raise RuntimeError("Merged duration does not match the input videos.")
        if versions != [_file_version(path) for path in inputs]:
            raise RuntimeError("An input changed during merging; output was discarded.")
        # Reserve the destination exclusively before publishing the completed file.
        with output.open("xb"):
            pass
        try:
            os.replace(merged, output)
        except BaseException:
            output.unlink()
            raise
    return {
        "output": str(output),
        "input_count": len(inputs),
        "mode": "copy",
        "duration_sec": duration,
        "width": video.get("width"),
        "height": video.get("height"),
        "video_codec": video.get("codec_name"),
        "time_sec": round(time.perf_counter() - started, 3),
    }
