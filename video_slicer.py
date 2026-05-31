"""
video_slicer.py — Main entry point for Thea video extraction tool.

Orchestrates the pipeline: load config -> compute optical flow -> detect windows -> slice video.
Outputs metadata JSON alongside the sliced clips.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime

import cv2

from video_processing import compute_motion_scores, detect_stable_windows, slice_video


# ---------------------------------------------------------------------------
# Config loading & validation
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config(config_path: str = None) -> dict:
    """Load and validate configuration from JSON file."""
    path = config_path or DEFAULT_CONFIG_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        config = json.load(f)

    _validate_config(config)
    return config


def _validate_config(config: dict):
    """Validate config values, raising ValueError on issues."""
    errors = []

    # Required sections
    for section in ("analysis", "optical_flow", "window_detection", "output", "gpu"):
        if section not in config:
            errors.append(f"Missing config section: '{section}'")

    if errors:
        raise ValueError("Config validation failed:\n  " + "\n  ".join(errors))

    # Optical flow
    algo = config["optical_flow"].get("algorithm", "")
    if algo not in ("farneback",):
        errors.append(f"Unsupported algorithm: '{algo}'. Supported: farneback")
    elif algo not in config["optical_flow"]:
        errors.append(f"Algorithm '{algo}' selected but no parameters section found")

    # Analysis
    if config["analysis"].get("max_width", 0) <= 0:
        errors.append("analysis.max_width must be > 0")
    if config["analysis"].get("motion_smoothing_sigma", 0) < 0:
        errors.append("analysis.motion_smoothing_sigma must be >= 0")

    # Window detection
    wd = config["window_detection"]
    if wd.get("min_duration_sec", 0) <= 0:
        errors.append("window_detection.min_duration_sec must be > 0")
    if wd.get("motion_threshold", -1) < 0:
        errors.append("window_detection.motion_threshold must be >= 0")
    if wd.get("merge_gap_sec", -1) < 0:
        errors.append("window_detection.merge_gap_sec must be >= 0")

    # Farneback specifics
    if algo == "farneback" and "farneback" in config["optical_flow"]:
        fb = config["optical_flow"]["farneback"]
        if fb.get("winsize", 0) < 1:
            errors.append("farneback.winsize must be >= 1")
        if fb.get("levels", 0) < 1:
            errors.append("farneback.levels must be >= 1")
        if fb.get("iterations", 0) < 1:
            errors.append("farneback.iterations must be >= 1")

    if errors:
        raise ValueError("Config validation failed:\n  " + "\n  ".join(errors))


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(log_file: str = None):
    """Configure logging to console and optionally a file."""
    logger = logging.getLogger("thea")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler (optional)
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


# ---------------------------------------------------------------------------
# System info
# ---------------------------------------------------------------------------

def get_system_info(config: dict) -> dict:
    """Gather system/environment info for metadata."""
    info = {
        "opencv_version": cv2.__version__,
        "opencv_path": os.path.dirname(cv2.__file__),
        "python_version": sys.version.split()[0],
        "cuda_available": cv2.cuda.getCudaEnabledDeviceCount() > 0,
        "cuda_device_count": cv2.cuda.getCudaEnabledDeviceCount(),
        "cuda_in_build": "CUDA" in cv2.getBuildInformation(),
        "timestamp": datetime.now().isoformat(),
        "platform": sys.platform,
    }
    return info


# ---------------------------------------------------------------------------
# Metadata output
# ---------------------------------------------------------------------------

def write_metadata(metadata: dict, output_path: str):
    """Write run metadata to a JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main(video_path: str = "sample.MP4", config_path: str = None):
    """Run the full Thea extraction pipeline."""
    # Setup
    config = load_config(config_path)
    logger = setup_logging()
    total_start = time.perf_counter()

    # Print system info
    sys_info = get_system_info(config)
    logger.info("=" * 60)
    logger.info("THEA - Video Stock-Footage Extractor")
    logger.info("=" * 60)
    logger.info(f"  OpenCV:      {sys_info['opencv_version']}")
    logger.info(f"  Python:      {sys_info['python_version']}")
    logger.info(f"  CUDA:        {'YES (' + str(sys_info['cuda_device_count']) + ' device(s))' if sys_info['cuda_available'] else 'NO'}")
    logger.info(f"  Algorithm:   {config['optical_flow']['algorithm']}")
    logger.info(f"  Config:      {config_path or DEFAULT_CONFIG_PATH}")
    logger.info("=" * 60)

    # Step 1: Compute motion scores
    logger.info(f"\n[1/3] Computing optical flow for: {video_path}")
    flow_result = compute_motion_scores(video_path, config)

    video_info = flow_result["video_info"]
    motion_stats = flow_result["motion_stats"]
    processing = flow_result["processing"]

    logger.info(f"\n  Motion Statistics:")
    logger.info(f"    Mean:   {motion_stats['mean']:.4f}")
    logger.info(f"    Median: {motion_stats['median']:.4f}")
    logger.info(f"    Max:    {motion_stats['max']:.4f}")
    logger.info(f"    Std:    {motion_stats['std']:.4f}")
    logger.info(f"    P25:    {motion_stats['p25']:.4f}  P75: {motion_stats['p75']:.4f}  P95: {motion_stats['p95']:.4f}")
    logger.info(f"    Throughput: {processing['fps_throughput']} frames/sec")

    # Step 2: Detect stable windows
    logger.info(f"\n[2/3] Detecting stable windows (threshold={config['window_detection']['motion_threshold']}, min={config['window_detection']['min_duration_sec']}s, merge_gap={config['window_detection']['merge_gap_sec']}s)")
    windows = detect_stable_windows(
        flow_result["motion_scores"],
        video_info["fps"],
        config,
    )

    if windows:
        logger.info(f"\n  Found {len(windows)} stable window(s):")
        for i, w in enumerate(windows):
            logger.info(f"    [{i+1}] {w['start_sec']:.1f}s - {w['end_sec']:.1f}s ({w['duration_sec']:.1f}s, avg_motion={w['avg_motion']:.3f})")
    else:
        logger.info("\n  No stable windows found with current settings.")
        logger.info(f"  Suggestion: try increasing motion_threshold (current={config['window_detection']['motion_threshold']}) or decreasing min_duration_sec")

    # Step 3: Slice video
    output_files = []
    if windows:
        logger.info(f"\n[3/3] Slicing video into {len(windows)} clip(s)...")
        output_files = slice_video(video_path, windows, config)
    else:
        logger.info("\n[3/3] Skipping slice (no windows detected).")

    # Total time
    total_elapsed = time.perf_counter() - total_start
    logger.info(f"\nTotal pipeline time: {total_elapsed:.2f}s")

    # Build and write metadata
    metadata = {
        "thea_version": "0.2.0",
        "system": sys_info,
        "config_used": config,
        "video": video_info,
        "processing": processing,
        "motion_stats": motion_stats,
        "flow_calculator_stats": flow_result["flow_calculator_stats"],
        "windows_detected": windows,
        "output_files": output_files,
        "total_pipeline_time_sec": round(total_elapsed, 3),
    }

    if config["output"].get("write_metadata", True):
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        meta_path = f"{base_name}_metadata.json"
        write_metadata(metadata, meta_path)
        logger.info(f"Metadata written to: {meta_path}")

    logger.info("Done.")
    return metadata


if __name__ == "__main__":
    # Simple CLI: python video_slicer.py [video_path] [config_path]
    video = sys.argv[1] if len(sys.argv) > 1 else "sample.MP4"
    cfg = sys.argv[2] if len(sys.argv) > 2 else None
    main(video_path=video, config_path=cfg)