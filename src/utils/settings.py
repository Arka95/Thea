"""
utils/settings.py — Global pipeline settings with concrete directory structure.

Settings in config/settings/settings.local.json override settings.json.
Relative configured paths resolve from the repository root, not the current directory.
The default is data/. If explicitly empty (""), use the legacy source-relative path:
  - If source is a directory: source_dir/Thea/
  - If source is a file: file_parent_dir/Thea/

Directory structure (constants, not configurable):
  data_dir/
    downscaled/     — downscaled videos for analysis
    sliced/         — extracted stable clips
    merged/         — concatenated videos
    cropandpan/     — cropped and panned videos
    video_meta.csv  — motion assessment results per video
    pipeline_stats.csv — timing stats per pipeline run

Usage:
    from utils.settings import resolve_data_dir, DOWNSAMPLED_DIR, SLICED_DIR, ...

    data_dir = resolve_data_dir(source_path)
    downsampled = os.path.join(data_dir, DOWNSAMPLED_DIR)
"""

import json
import logging
import os
from pathlib import Path

from utils.paths import CONFIG_DIR, PROJECT_ROOT

logger = logging.getLogger("thea")

# ---------------------------------------------------------------------------
# Constants — directory structure (never changes)
# ---------------------------------------------------------------------------

DOWNSAMPLED_DIR = "downscaled"
SLICED_DIR = "sliced"
MERGED_DIR = "merged"
CROPANDPAN_DIR = "cropandpan"
VIDEO_META_CSV = "video_meta.csv"
PIPELINE_STATS_CSV = "pipeline_stats.csv"
DATA_ROOT_NAME = "Thea"

# ---------------------------------------------------------------------------
# Settings file location
# ---------------------------------------------------------------------------

_SETTINGS_FILE = CONFIG_DIR / "settings" / "settings.json"
_LOCAL_SETTINGS_FILE = _SETTINGS_FILE.with_name("settings.local.json")


def _load_raw_settings() -> dict:
    """Merge shared settings with an optional, ignored machine-local override."""
    settings = {"data_dir": "data", "data_collection": False, "reencode": False}
    for path in (_SETTINGS_FILE, _LOCAL_SETTINGS_FILE):
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            values = json.load(handle)
        if not isinstance(values, dict):
            raise TypeError(f"Settings must be a JSON object: {path}")
        settings.update(values)
    if not isinstance(settings["data_dir"], str):
        raise TypeError("data_dir must be a string")
    for key in ("data_collection", "reencode"):
        if not isinstance(settings[key], bool):
            raise TypeError(f"{key} must be a boolean")
    return settings


def is_data_collection_enabled() -> bool:
    """Check if CSV data collection is enabled in settings.

    Returns False if setting is missing or explicitly false.
    """
    settings = _load_raw_settings()
    return settings.get("data_collection", False) is True


def is_reencode_enabled() -> bool:
    """Check if slicing should re-encode using OpenCV.

    Returns False (default) for lossless FFmpeg stream copy.
    Returns True to re-encode with config output.codec via OpenCV.
    """
    settings = _load_raw_settings()
    return settings.get("reencode", False) is True


def resolve_data_dir(source_path: str) -> str:
    """Resolve the data directory for a pipeline run.

    Logic:
        1. Use the merged data_dir; relative paths are repository-relative.
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
        configured_path = Path(configured_dir).expanduser()
        if not configured_path.is_absolute():
            configured_path = PROJECT_ROOT / configured_path
        data_dir = str(configured_path.resolve())
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


def get_merged_dir(data_dir: str) -> str:
    """Get the merged video output directory path."""
    return os.path.join(data_dir, MERGED_DIR)


def get_cropandpan_dir(data_dir: str) -> str:
    """Get the crop/pan output directory path."""
    return os.path.join(data_dir, CROPANDPAN_DIR)


def get_video_meta_path(data_dir: str) -> str:
    """Get the video_meta.csv path."""
    return os.path.join(data_dir, VIDEO_META_CSV)


def get_pipeline_stats_path(data_dir: str) -> str:
    """Get the pipeline_stats.csv path."""
    return os.path.join(data_dir, PIPELINE_STATS_CSV)
