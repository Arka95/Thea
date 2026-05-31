"""
utils/settings.py — Global pipeline settings with concrete directory structure.

The only user-configurable value is `data_dir` in config/settings/settings.json.
If empty (""), the data directory is resolved from the video source path:
  - If source is a directory: source_dir/Thea/
  - If source is a file: file_parent_dir/Thea/

Directory structure (constants, not configurable):
  data_dir/
    downsampled/    — downscaled videos for analysis
    sliced/         — extracted stable clips
    video_meta.csv  — motion assessment results per video
    pipeline_stats.csv — timing stats per pipeline run

Usage:
    from utils.settings import resolve_data_dir, DOWNSAMPLED_DIR, SLICED_DIR, ...

    data_dir = resolve_data_dir(source_path)
    downsampled = os.path.join(data_dir, DOWNSAMPLED_DIR)
"""

import json
import os
import logging
from pathlib import Path

logger = logging.getLogger("thea")

# ---------------------------------------------------------------------------
# Constants — directory structure (never changes)
# ---------------------------------------------------------------------------

DOWNSAMPLED_DIR = "downsampled"
SLICED_DIR = "sliced"
VIDEO_META_CSV = "video_meta.csv"
PIPELINE_STATS_CSV = "pipeline_stats.csv"
DATA_ROOT_NAME = "Thea"

# ---------------------------------------------------------------------------
# Settings file location
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SETTINGS_FILE = _PROJECT_ROOT / "config" / "settings" / "settings.json"


def _load_raw_settings() -> dict:
    """Load raw settings.json. Returns dict with 'data_dir' key."""
    if not _SETTINGS_FILE.exists():
        return {"data_dir": ""}
    with open(_SETTINGS_FILE, "r") as f:
        return json.load(f)


def is_data_collection_enabled() -> bool:
    """Check if CSV data collection is enabled in settings.

    Returns False if setting is missing or explicitly false.
    """
    settings = _load_raw_settings()
    return settings.get("data_collection", False) is True


def resolve_data_dir(source_path: str) -> str:
    """Resolve the data directory for a pipeline run.

    Logic:
        1. If settings.json has a non-empty data_dir, use it.
        2. Otherwise, derive from source_path:
           - source is a directory -> source_path/Thea/
           - source is a file -> parent_of_file/Thea/

    The directory and its subdirectories are created if they don't exist.

    Args:
        source_path: The video file or directory passed to the pipeline.

    Returns:
        Absolute path to the data directory.
    """
    settings = _load_raw_settings()
    configured_dir = settings.get("data_dir", "").strip()

    if configured_dir:
        data_dir = os.path.abspath(configured_dir)
    else:
        source = os.path.abspath(source_path)
        if os.path.isdir(source):
            data_dir = os.path.join(source, DATA_ROOT_NAME)
        else:
            data_dir = os.path.join(os.path.dirname(source), DATA_ROOT_NAME)

    # Ensure structure exists
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, DOWNSAMPLED_DIR), exist_ok=True)
    os.makedirs(os.path.join(data_dir, SLICED_DIR), exist_ok=True)

    return data_dir


def get_downsampled_path(video_path: str, data_dir: str, lossless: bool = False) -> str:
    """Get the expected path for a downsampled version of a video.

    Args:
        video_path: Source video file path.
        data_dir: Resolved data directory.
        lossless: Whether lossless encoding is used.

    Returns:
        Full path where the downsampled video should be stored.
    """
    base = os.path.splitext(os.path.basename(video_path))[0]
    ext = ".avi" if lossless else ".mp4"
    return os.path.join(data_dir, DOWNSAMPLED_DIR, f"{base}{ext}")


def get_sliced_dir(data_dir: str) -> str:
    """Get the sliced output directory path."""
    return os.path.join(data_dir, SLICED_DIR)


def get_video_meta_path(data_dir: str) -> str:
    """Get the video_meta.csv path."""
    return os.path.join(data_dir, VIDEO_META_CSV)


def get_pipeline_stats_path(data_dir: str) -> str:
    """Get the pipeline_stats.csv path."""
    return os.path.join(data_dir, PIPELINE_STATS_CSV)
