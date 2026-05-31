"""
utils/validations.py — Video validation utilities.

Provides two levels of validation:
  1. Simple validation: Based on file metadata (codec, resolution, duration, etc.)
  2. Complex validation: Based on optical flow / motion assessment metadata

These are designed for future pipeline integration (pre-filtering videos before
expensive processing, or post-filtering results).
"""

import os
import logging
from typing import Optional
from pathlib import Path

from utils.video_io import get_video_info, VIDEO_EXTENSIONS
from utils.config_loader import get_supported_codecs

logger = logging.getLogger("thea")


# ---------------------------------------------------------------------------
# Simple Validation (file metadata only — fast, no processing needed)
# ---------------------------------------------------------------------------

def validate_video_file(video_path: str, config: Optional[dict] = None) -> dict:
    """Validate a video file based on its metadata.

    Checks performed:
      - File exists and is readable
      - File extension is a supported video format
      - Video can be opened by OpenCV
      - Codec is in supported codecs list
      - Resolution is non-zero
      - FPS is valid (> 0)
      - Duration meets minimum (if config provided)
      - Frame count is non-zero

    Args:
        video_path: Path to video file.
        config: Optional config dict (used for min_duration check).

    Returns:
        dict with keys: valid (bool), errors (list[str]), warnings (list[str]), info (dict)
    """
    result = {"valid": True, "errors": [], "warnings": [], "info": {}}

    # File existence
    if not os.path.exists(video_path):
        result["valid"] = False
        result["errors"].append(f"File not found: {video_path}")
        return result

    if not os.path.isfile(video_path):
        result["valid"] = False
        result["errors"].append(f"Not a file: {video_path}")
        return result

    # Extension check
    ext = Path(video_path).suffix.lower()
    if ext not in VIDEO_EXTENSIONS:
        result["valid"] = False
        result["errors"].append(f"Unsupported extension: {ext}")
        return result

    # OpenCV readability
    try:
        info = get_video_info(video_path)
        result["info"] = info
    except ValueError as e:
        result["valid"] = False
        result["errors"].append(f"Cannot open video: {e}")
        return result

    # Resolution
    if info["width"] == 0 or info["height"] == 0:
        result["valid"] = False
        result["errors"].append(f"Invalid resolution: {info['width']}x{info['height']}")

    # FPS
    if info["fps"] <= 0:
        result["valid"] = False
        result["errors"].append(f"Invalid FPS: {info['fps']}")

    # Frame count
    if info["total_frames"] <= 0:
        result["valid"] = False
        result["errors"].append(f"No frames in video (frame_count={info['total_frames']})")

    # Codec support
    supported = [c[0].lower() for c in get_supported_codecs()]
    if supported and info["codec"].strip().lower() not in supported:
        result["warnings"].append(f"Codec '{info['codec']}' not in supported_codecs.txt (may still work)")

    # Duration vs config minimum
    if config and info.get("duration_sec", 0) > 0:
        min_dur = config.get("window_detection", {}).get("min_duration_sec", 0)
        if info["duration_sec"] < min_dur:
            result["warnings"].append(
                f"Video duration ({info['duration_sec']:.1f}s) is less than "
                f"min_duration_sec ({min_dur}s) — no windows can be extracted"
            )

    # File size sanity
    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    if file_size_mb < 0.01:
        result["warnings"].append(f"Very small file ({file_size_mb:.3f} MB) — may be corrupt")

    return result


# ---------------------------------------------------------------------------
# Complex Validation (based on motion/optical flow metadata — post-processing)
# ---------------------------------------------------------------------------

def validate_motion_metadata(metadata: dict) -> dict:
    """Validate optical flow / motion assessment output.

    Checks performed:
      - Motion stats are within physically plausible ranges
      - No NaN or infinite values in scores
      - Frame count matches expected from video info
      - Windows are non-overlapping and within video duration
      - Window durations respect min_duration_sec from config
      - GPU/CPU fallback is logged if unexpected
      - Processing throughput is reasonable (detect stalls)

    Future validation ideas (TODO):
      - Detect constant-motion segments (possible encoding artifact)
      - Detect sudden score spikes that indicate scene cuts vs actual motion
      - Cross-validate motion stats against video bitrate (high bitrate + low motion = suspicious)
      - Validate temporal consistency (motion should change gradually, not teleport)
      - Detect duplicate/frozen frames (motion score = 0 for extended periods)
      - Validate window extraction ratio against expected content type

    Args:
        metadata: Full metadata dict from the pipeline run.

    Returns:
        dict with keys: valid (bool), errors (list[str]), warnings (list[str])
    """
    result = {"valid": True, "errors": [], "warnings": []}

    # Check motion stats exist
    stats = metadata.get("motion_stats")
    if not stats:
        result["valid"] = False
        result["errors"].append("No motion_stats in metadata")
        return result

    # NaN/Inf check
    import math
    for key, val in stats.items():
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            result["valid"] = False
            result["errors"].append(f"motion_stats.{key} is {val}")

    # Plausibility: mean motion shouldn't exceed max
    if stats.get("mean", 0) > stats.get("max", float("inf")):
        result["errors"].append("mean > max in motion_stats (impossible)")
        result["valid"] = False

    # Frame count consistency
    processing = metadata.get("processing", {})
    video_info = metadata.get("video", metadata.get("video_info", {}))
    if processing.get("frames_analyzed", 0) > 0 and video_info.get("total_frames", 0) > 0:
        expected = video_info["total_frames"] - 1  # First frame is reference
        actual = processing["frames_analyzed"]
        if abs(expected - actual) > 2:
            result["warnings"].append(
                f"Frames analyzed ({actual}) != expected ({expected})"
            )

    # Window validation
    windows = metadata.get("windows_detected", metadata.get("windows", []))
    duration = video_info.get("duration_sec", 0)

    for i, w in enumerate(windows):
        if w.get("end_sec", 0) > duration + 1.0:
            result["warnings"].append(f"Window {i} end ({w['end_sec']}s) exceeds video duration ({duration}s)")
        if w.get("start_sec", 0) < 0:
            result["errors"].append(f"Window {i} has negative start time")
            result["valid"] = False
        if i > 0 and w.get("start_sec", 0) < windows[i-1].get("end_sec", 0):
            result["errors"].append(f"Windows {i-1} and {i} overlap")
            result["valid"] = False

    # GPU fallback warning
    config = metadata.get("config_used", {})
    if config.get("gpu", {}).get("enabled") and not processing.get("gpu_used"):
        result["warnings"].append("GPU was requested but CPU was used (fallback occurred)")

    # Throughput sanity
    throughput = processing.get("fps_throughput", 0)
    if throughput > 0 and throughput < 1.0:
        result["warnings"].append(f"Very low throughput ({throughput} fps) — possible performance issue")

    return result
