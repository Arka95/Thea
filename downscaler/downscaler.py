"""
downscaler/downscaler.py — Video downscaling for motion assessment optimization.

Provides single and batch downscaling, producing analysis-optimized video files
(lower resolution, preserved fps) that can be fed directly to motion assessment.
"""

import os
import cv2
import time
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

from utils.video_io import discover_videos, get_video_info
from utils.metrics import track

logger = logging.getLogger("thea")


@track(context_fn=lambda a, kw: {"video": os.path.basename(a[0]) if a else ""})
def downscale_video(
    source_path: str,
    output_path: str,
    max_width: int = 320,
    codec: str = "mp4v",
    lossless: bool = False,
) -> dict:
    """Downscale a single video to the target analysis width.

    The output preserves original FPS and aspect ratio.

    Args:
        source_path: Input video file path.
        output_path: Output video file path.
        max_width: Target maximum width (height scales proportionally).
        codec: FourCC codec string for output (ignored if lossless=True).
        lossless: If True, uses FFV1 lossless codec with LANCZOS4 interpolation.
                  Output is .avi regardless of output_path extension.

    Returns:
        dict with: source, output, original_res, output_res, frames, duration_sec, time_sec
    """
    cap = cv2.VideoCapture(source_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {source_path}")

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Compute output dimensions
    if w <= max_width:
        out_w, out_h = w, h
    else:
        scale = max_width / w
        out_w = int(w * scale)
        out_h = int(h * scale)

    # Lossless mode: override codec and extension
    if lossless:
        codec = "FFV1"
        output_path = os.path.splitext(output_path)[0] + ".avi"
        interpolation = cv2.INTER_LANCZOS4
    else:
        interpolation = cv2.INTER_AREA

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(output_path, fourcc, fps, (out_w, out_h))

    if not writer.isOpened():
        cap.release()
        raise ValueError(f"Cannot create output video with codec '{codec}': {output_path}")

    t_start = time.perf_counter()
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if out_w != w or out_h != h:
            frame = cv2.resize(frame, (out_w, out_h), interpolation=interpolation)

        writer.write(frame)
        frame_count += 1

    cap.release()
    writer.release()
    t_elapsed = time.perf_counter() - t_start

    return {
        "source": source_path,
        "output": output_path,
        "original_resolution": [w, h],
        "output_resolution": [out_w, out_h],
        "frames_written": frame_count,
        "duration_sec": round(total_frames / fps, 2) if fps > 0 else 0,
        "processing_time_sec": round(t_elapsed, 2),
        "size_reduction": round(1 - (os.path.getsize(output_path) / os.path.getsize(source_path)), 3) if os.path.exists(output_path) else 0,
        "lossless": lossless,
    }


def _downscale_worker(args: tuple) -> dict:
    """Worker function for parallel batch processing."""
    source_path, output_path, max_width, codec, lossless = args
    try:
        return downscale_video(source_path, output_path, max_width, codec, lossless=lossless)
    except Exception as e:
        return {
            "source": source_path,
            "output": output_path,
            "error": str(e),
            "status": "failed",
        }


def batch_downscale(
    source_dir: str,
    sink_dir: str,
    max_width: int = 320,
    codec: str = "mp4v",
    workers: int = 4,
    recursive: bool = True,
    lossless: bool = False,
) -> list:
    """Downscale all videos in source_dir, writing results to sink_dir.

    Preserves relative directory structure from source_dir in sink_dir.
    Parallelized across available workers.

    Args:
        source_dir: Directory containing source videos.
        sink_dir: Directory to write downscaled videos to.
        max_width: Target width for downscaled output.
        codec: FourCC codec for output files (ignored if lossless=True).
        workers: Number of parallel workers.
        recursive: Search subdirectories.
        lossless: If True, uses FFV1 lossless codec with LANCZOS4 interpolation.

    Returns:
        List of result dicts (one per video).
    """
    videos = discover_videos(source_dir, recursive=recursive)
    if not videos:
        logger.warning(f"No videos found in: {source_dir}")
        return []

    os.makedirs(sink_dir, exist_ok=True)
    logger.info(f"Batch downscale: {len(videos)} videos, {workers} workers, target={max_width}px")

    # Build task list preserving relative structure
    tasks = []
    source_root = os.path.abspath(source_dir)
    for video_path in videos:
        rel_path = os.path.relpath(video_path, source_root)
        output_path = os.path.join(sink_dir, rel_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        tasks.append((video_path, output_path, max_width, codec, lossless))

    # Process
    t_start = time.perf_counter()
    results = []

    if workers <= 1:
        for i, task in enumerate(tasks):
            logger.info(f"  [{i+1}/{len(tasks)}] {os.path.basename(task[0])}")
            result = _downscale_worker(task)
            results.append(result)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_downscale_worker, t): t[0] for t in tasks}
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                results.append(result)
                name = os.path.basename(result.get("source", ""))
                if "error" in result:
                    logger.error(f"  [{i+1}/{len(tasks)}] {name} FAILED: {result['error']}")
                else:
                    reduction = result.get("size_reduction", 0) * 100
                    logger.info(f"  [{i+1}/{len(tasks)}] {name} -> {reduction:.0f}% smaller")

    t_elapsed = time.perf_counter() - t_start
    success = sum(1 for r in results if "error" not in r)
    logger.info(f"Batch complete: {success}/{len(results)} in {t_elapsed:.1f}s")

    return results
