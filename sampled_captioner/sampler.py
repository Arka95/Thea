"""Create a compact contact sheet from representative points in a video."""

from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class SampledContactSheet:
    video_path: str
    image_path: str
    timestamps_sec: tuple[float, ...]
    duration_sec: float
    frame_width: int
    frame_height: int
    processing_time_sec: float


def select_frame_indices(total_frames: int, sample_count: int) -> list[int]:
    """Select unique frame indices from the central 90% of a video."""
    if total_frames <= 0:
        raise ValueError("total_frames must be positive")
    if sample_count <= 0:
        raise ValueError("sample_count must be positive")

    count = min(total_frames, sample_count)
    if count == 1:
        return [total_frames // 2]

    start = round((total_frames - 1) * 0.05)
    end = round((total_frames - 1) * 0.95)
    indices = np.rint(np.linspace(start, end, count)).astype(int)
    return sorted(set(indices.tolist()))


def _letterbox_frame(frame: np.ndarray, width: int, height: int) -> np.ndarray:
    if width <= 0 or height <= 0:
        raise ValueError("frame dimensions must be positive")
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("frame must be a BGR image")

    source_height, source_width = frame.shape[:2]
    scale = min(width / source_width, height / source_height)
    resized_width = max(1, round(source_width * scale))
    resized_height = max(1, round(source_height * scale))
    resized = cv2.resize(frame, (resized_width, resized_height), interpolation=cv2.INTER_AREA)

    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    x = (width - resized_width) // 2
    y = (height - resized_height) // 2
    canvas[y : y + resized_height, x : x + resized_width] = resized
    return canvas


def _assemble_contact_sheet(frames: list[np.ndarray], columns: int) -> np.ndarray:
    if not frames:
        raise ValueError("at least one frame is required")
    if columns <= 0:
        raise ValueError("columns must be positive")

    frame_height, frame_width = frames[0].shape[:2]
    rows = math.ceil(len(frames) / columns)
    sheet = np.zeros((rows * frame_height, columns * frame_width, 3), dtype=np.uint8)

    for index, frame in enumerate(frames):
        if frame.shape[:2] != (frame_height, frame_width):
            raise ValueError("all frames must have identical dimensions")
        row, column = divmod(index, columns)
        y, x = row * frame_height, column * frame_width
        sheet[y : y + frame_height, x : x + frame_width] = frame

    return sheet


def create_contact_sheet(
    video_path: str,
    output_path: str,
    sample_count: int = 12,
    frame_width: int = 176,
    frame_height: int = 144,
    columns: int = 4,
) -> SampledContactSheet:
    """Sample a video without creating another downscaled video.

    ``video_path`` may point to Thea's existing downscaled output. Only sampled
    frames are resized here, avoiding a duplicate full-video downscale.
    """
    started = time.perf_counter()
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    try:
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            raise ValueError(f"Video has invalid FPS: {video_path}")

        indices = select_frame_indices(total_frames, sample_count)
        frames = []
        timestamps = []
        for frame_index in indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = capture.read()
            if not ok:
                raise ValueError(f"Cannot read frame {frame_index}: {video_path}")
            frames.append(_letterbox_frame(frame, frame_width, frame_height))
            timestamps.append(frame_index / fps)
    finally:
        capture.release()

    sheet = _assemble_contact_sheet(frames, columns)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if not cv2.imwrite(output_path, sheet):
        raise ValueError(f"Cannot write contact sheet: {output_path}")

    return SampledContactSheet(
        video_path=os.path.abspath(video_path),
        image_path=os.path.abspath(output_path),
        timestamps_sec=tuple(round(value, 3) for value in timestamps),
        duration_sec=round(total_frames / fps, 3),
        frame_width=frame_width,
        frame_height=frame_height,
        processing_time_sec=round(time.perf_counter() - started, 3),
    )
