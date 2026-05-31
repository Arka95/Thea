"""
slicer/slicer.py — Video slicing based on detected stable windows.

Takes window timestamps and extracts those segments from the source video into
individual clip files.
"""

import os
import cv2
import time
import logging

from utils.metrics import track

logger = logging.getLogger("thea")


@track(context_fn=lambda a, kw: {"video": os.path.basename(a[0]) if a else "", "windows": len(a[1]) if len(a) > 1 else 0})
def slice_video(video_path: str, windows: list, config: dict, output_dir: str = None) -> list:
    """Slice a video into clips for each stable window.

    Args:
        video_path: Source video file.
        windows: List of window dicts with start_sec, end_sec.
        config: Config dict (uses output.codec).
        output_dir: Override output directory (default: {video_name}_sliced/).

    Returns:
        List of output file paths created.
    """
    if not windows:
        logger.info("No stable windows to slice.")
        return []

    codec = config["output"]["codec"]
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video for slicing: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    out_folder = output_dir or f"{base_name}_sliced"
    os.makedirs(out_folder, exist_ok=True)

    output_files = []
    t_start = time.perf_counter()

    for idx, window in enumerate(windows):
        start_frame = int(window["start_sec"] * fps)
        end_frame = int(window["end_sec"] * fps)
        out_path = os.path.join(out_folder, f"{base_name}_{idx + 1}.mp4")

        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(out_path, fourcc, fps, (frame_w, frame_h))

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        for _ in range(end_frame - start_frame):
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)

        out.release()
        output_files.append(out_path)
        logger.info(f"  Sliced: {out_path} ({window['duration_sec']:.1f}s)")

    cap.release()
    t_elapsed = time.perf_counter() - t_start
    logger.info(f"  Slicing complete: {len(output_files)} clips in {t_elapsed:.1f}s")
    return output_files
