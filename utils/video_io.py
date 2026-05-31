"""
utils/video_io.py — Video file discovery and metadata extraction.
"""

import os
import cv2
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"}


def discover_videos(directory: str, recursive: bool = True) -> list:
    """Find all video files in a directory.

    Args:
        directory: Root directory to search.
        recursive: If True, searches subdirectories.

    Returns:
        Sorted list of absolute video file paths.
    """
    videos = []
    if recursive:
        for root, _, files in os.walk(directory):
            for f in files:
                if Path(f).suffix.lower() in VIDEO_EXTENSIONS:
                    videos.append(os.path.join(root, f))
    else:
        for f in os.listdir(directory):
            fp = os.path.join(directory, f)
            if os.path.isfile(fp) and Path(f).suffix.lower() in VIDEO_EXTENSIONS:
                videos.append(fp)
    videos.sort()
    return videos


def get_video_info(video_path: str) -> dict:
    """Extract metadata from a video file without reading all frames."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    info = {
        "path": os.path.abspath(video_path),
        "filename": os.path.basename(video_path),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "codec": _decode_fourcc(int(cap.get(cv2.CAP_PROP_FOURCC))),
    }
    info["duration_sec"] = round(info["total_frames"] / info["fps"], 2) if info["fps"] > 0 else 0
    cap.release()
    return info


def _decode_fourcc(fourcc: int) -> str:
    """Convert integer fourcc to readable string."""
    return "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])


def is_video_file(path: str) -> bool:
    """Check if a path points to a supported video file."""
    return os.path.isfile(path) and Path(path).suffix.lower() in VIDEO_EXTENSIONS
