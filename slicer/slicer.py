"""
slicer/slicer.py — Video slicing based on detected stable windows.

Two modes controlled by settings.json `reencode`:
  - False (default): FFmpeg stream copy — lossless, ~6x faster, preserves original codec
  - True: OpenCV re-encode — uses config output.codec, allows codec conversion
"""

import os
import cv2
import subprocess
import time
import logging

from utils.metrics import track
from utils.settings import is_reencode_enabled

logger = logging.getLogger("thea")


def _get_ffmpeg_exe() -> str:
    """Get the FFmpeg executable path."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise RuntimeError(
            "FFmpeg is required for lossless slicing. "
            "Install via: pip install imageio-ffmpeg"
        )


def _slice_ffmpeg(video_path: str, windows: list, out_folder: str, base_name: str, src_ext: str) -> list:
    """Slice using FFmpeg stream copy (no re-encoding)."""
    ffmpeg = _get_ffmpeg_exe()
    output_files = []

    for idx, window in enumerate(windows):
        start = window["start_sec"]
        duration = window["end_sec"] - start
        out_path = os.path.join(out_folder, f"{base_name}_{idx + 1}{src_ext}")

        cmd = [
            ffmpeg, "-y",
            "-ss", f"{start:.3f}",
            "-i", video_path,
            "-t", f"{duration:.3f}",
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            out_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"FFmpeg failed for window {idx+1}: {result.stderr[-200:]}")
            continue

        output_files.append(out_path)
        logger.info(f"  Sliced: {out_path} ({window['duration_sec']:.1f}s)")

    return output_files


def _slice_opencv(video_path: str, windows: list, out_folder: str, base_name: str, codec: str) -> list:
    """Slice using OpenCV VideoWriter (re-encodes with specified codec)."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video for slicing: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    output_files = []

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
    return output_files


@track(context_fn=lambda a, kw: {"video": os.path.basename(a[0]) if a else "", "windows": len(a[1]) if len(a) > 1 else 0})
def slice_video(video_path: str, windows: list, config: dict, output_dir: str = None) -> list:
    """Slice a video into clips for each stable window.

    Mode is determined by settings.json `reencode`:
      - False: FFmpeg stream copy (lossless, fast)
      - True: OpenCV re-encode (uses config output.codec)

    Args:
        video_path: Source video file.
        windows: List of window dicts with start_sec, end_sec.
        config: Config dict (output.codec used only when reencode=True).
        output_dir: Override output directory.

    Returns:
        List of output file paths created.
    """
    if not windows:
        logger.info("No stable windows to slice.")
        return []

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    src_ext = os.path.splitext(video_path)[1] or ".mp4"
    out_folder = output_dir or f"{base_name}_sliced"
    os.makedirs(out_folder, exist_ok=True)

    t_start = time.perf_counter()

    if is_reencode_enabled():
        codec = config["output"]["codec"]
        logger.info(f"  Slicing mode: OpenCV re-encode (codec={codec})")
        output_files = _slice_opencv(video_path, windows, out_folder, base_name, codec)
    else:
        logger.info(f"  Slicing mode: FFmpeg stream copy (lossless)")
        output_files = _slice_ffmpeg(video_path, windows, out_folder, base_name, src_ext)

    t_elapsed = time.perf_counter() - t_start
    logger.info(f"  Slicing complete: {len(output_files)} clips in {t_elapsed:.1f}s")
    return output_files
