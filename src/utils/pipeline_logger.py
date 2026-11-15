"""
utils/pipeline_logger.py — CSV logging for pipeline execution stats and video metadata.

Maintains two CSV files in the data_dir:
  - video_meta.csv: motion assessment results per video
  - pipeline_stats.csv: timing stats per pipeline run
"""

import csv
import os
import json
import logging
from pathlib import Path

from utils.settings import get_video_meta_path, get_pipeline_stats_path, is_data_collection_enabled

logger = logging.getLogger("thea")


def _ensure_csv(path: str, headers: list):
    """Create CSV with headers only if file doesn't exist. Appends otherwise."""
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)


VIDEO_META_HEADERS = [
    "video_name",
    "video_path",
    "video_duration_sec",
    "resolution",
    "fps",
    "good_window_slices",
    "overall_assessment",
    "mean_motion",
    "max_motion",
    "optical_flow_config",
]

PIPELINE_STATS_HEADERS = [
    "video_path",
    "video_duration_sec",
    "downscaler_time_sec",
    "motion_assessment_time_sec",
    "slicing_time_sec",
    "total_time_sec",
    "timestamp",
]


def log_video_meta(data_dir: str, video_path: str, result: dict, windows: list, config: dict):
    """Append a row to video_meta.csv. No-op if data_collection is disabled.

    Args:
        data_dir: Root data directory.
        video_path: Path to the source video.
        result: Output from compute_motion_scores().
        windows: Detected stable windows.
        config: Config dict used.
    """
    if not is_data_collection_enabled():
        return

    csv_path = get_video_meta_path(data_dir)
    _ensure_csv(csv_path, VIDEO_META_HEADERS)

    vi = result["video_info"]
    ms = result["motion_stats"]
    from motion_assessment.assessment import MotionAssessment
    overall = MotionAssessment.from_score(ms["mean"], config["analysis"]["max_width"])

    # Format windows as compact JSON array of [start, end] pairs
    window_slices = json.dumps([[w["start_sec"], w["end_sec"]] for w in windows])
    flow_config = json.dumps(config.get("optical_flow", {}))

    row = [
        os.path.basename(video_path),
        video_path,
        round(vi.get("duration_sec", vi.get("total_frames", 0) / vi.get("fps", 1)), 2),
        f"{vi['width']}x{vi['height']}",
        vi["fps"],
        window_slices,
        overall.value,
        round(ms["mean"], 4),
        round(ms["max"], 4),
        flow_config,
    ]

    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)

    logger.debug(f"Logged video meta: {os.path.basename(video_path)}")


def log_pipeline_stats(
    data_dir: str,
    video_path: str,
    video_duration_sec: float,
    downscaler_time: float,
    motion_assessment_time: float,
    slicing_time: float,
    total_time: float,
):
    """Append a row to pipeline_stats.csv. No-op if data_collection is disabled.

    Args:
        data_dir: Root data directory.
        video_path: Source video path.
        video_duration_sec: Video duration.
        downscaler_time: Time spent downscaling (0 if skipped).
        motion_assessment_time: Time for motion analysis.
        slicing_time: Time for slicing.
        total_time: Total pipeline time.
    """
    if not is_data_collection_enabled():
        return

    from datetime import datetime
    csv_path = get_pipeline_stats_path(data_dir)
    _ensure_csv(csv_path, PIPELINE_STATS_HEADERS)

    row = [
        video_path,
        round(video_duration_sec, 2),
        round(downscaler_time, 3),
        round(motion_assessment_time, 3),
        round(slicing_time, 3),
        round(total_time, 3),
        datetime.now().isoformat(),
    ]

    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)

    logger.debug(f"Logged pipeline stats: {os.path.basename(video_path)}")
