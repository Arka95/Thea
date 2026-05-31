"""
video_processing.py — Video I/O, stable window detection, and slicing.

Handles reading video metadata, detecting stable windows from motion scores,
merging nearby windows, and slicing the source video into clips.
"""

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
import os
import time
import logging

from optical_flow import create_flow_calculator

logger = logging.getLogger("thea")


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


def compute_motion_scores(video_path: str, config: dict) -> dict:
    """Compute per-frame motion scores using optical flow.

    Returns:
        dict with keys: motion_scores, video_info, processing_meta, frame_metadata
    """
    max_width = config["analysis"]["max_width"]
    sigma = config["analysis"]["motion_smoothing_sigma"]

    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Compute analysis scale
    scale = max_width / w if w > max_width else 1.0
    analysis_w = int(w * scale)
    analysis_h = int(h * scale)

    logger.info(f"Video: {w}x{h} @ {fps:.1f}fps, {total_frames} frames ({total_frames/fps:.1f}s)")
    logger.info(f"Analysis resolution: {analysis_w}x{analysis_h} (scale={scale:.3f})")

    # Create flow calculator (reused across all frames)
    flow_calc = create_flow_calculator(config)
    logger.info(f"Optical flow: {config['optical_flow']['algorithm']} ({flow_calc.backend})")

    # Read first frame
    ret, frame = cap.read()
    if not ret:
        raise ValueError("Error reading first frame from video.")

    prev_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if scale < 1.0:
        prev_gray = cv2.resize(prev_gray, (analysis_w, analysis_h), interpolation=cv2.INTER_AREA)

    # Process all frames
    raw_scores = []
    frame_metadata_list = []
    frame_count = 0
    t_start = time.perf_counter()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if scale < 1.0:
            gray = cv2.resize(gray, (analysis_w, analysis_h), interpolation=cv2.INTER_AREA)

        motion_score, frame_meta = flow_calc.compute(prev_gray, gray)
        raw_scores.append(motion_score)
        frame_metadata_list.append(frame_meta)

        prev_gray = gray
        frame_count += 1
        if frame_count % 200 == 0:
            logger.info(f"  Processed {frame_count}/{total_frames} frames...")

    cap.release()
    t_elapsed = time.perf_counter() - t_start
    logger.info(f"  Processed {frame_count}/{total_frames} frames in {t_elapsed:.2f}s")

    # Apply temporal smoothing
    smoothed_scores = gaussian_filter1d(raw_scores, sigma=sigma).tolist() if raw_scores else []

    # Compile motion statistics
    scores_arr = np.array(raw_scores) if raw_scores else np.array([0.0])
    motion_stats = {
        "mean": round(float(np.mean(scores_arr)), 4),
        "median": round(float(np.median(scores_arr)), 4),
        "max": round(float(np.max(scores_arr)), 4),
        "min": round(float(np.min(scores_arr)), 4),
        "std": round(float(np.std(scores_arr)), 4),
        "p25": round(float(np.percentile(scores_arr, 25)), 4),
        "p75": round(float(np.percentile(scores_arr, 75)), 4),
        "p95": round(float(np.percentile(scores_arr, 95)), 4),
    }

    # Processing metadata
    processing_meta = {
        "source_resolution": [w, h],
        "analysis_resolution": [analysis_w, analysis_h],
        "scale_factor": round(scale, 4),
        "algorithm": config["optical_flow"]["algorithm"],
        "algorithm_params": config["optical_flow"][config["optical_flow"]["algorithm"]],
        "backend": flow_calc.backend,
        "gpu_requested": config["gpu"]["enabled"],
        "gpu_used": flow_calc.backend == "cuda",
        "smoothing_sigma": sigma,
        "frames_analyzed": frame_count,
        "total_time_sec": round(t_elapsed, 3),
        "avg_flow_time_ms": flow_calc.stats["avg_time_ms"],
        "fps_throughput": round(frame_count / t_elapsed, 1) if t_elapsed > 0 else 0,
        "motion_units": "mean_pixel_displacement_at_analysis_resolution",
    }

    return {
        "motion_scores": smoothed_scores,
        "raw_scores": raw_scores,
        "motion_stats": motion_stats,
        "video_info": get_video_info(video_path),
        "processing": processing_meta,
        "flow_calculator_stats": flow_calc.stats,
    }


def detect_stable_windows(motion_scores: list, fps: float, config: dict) -> list:
    """Find stable windows where motion is below threshold.

    Applies merge_gap_sec to join nearby stable segments, then filters by min_duration.

    Returns:
        List of dicts: [{start_sec, end_sec, duration_sec, avg_motion, frame_range}, ...]
    """
    wc = config["window_detection"]
    threshold = wc["motion_threshold"]
    min_duration = wc["min_duration_sec"]
    merge_gap = wc.get("merge_gap_sec", 0.0)

    # Pass 1: Find raw stable spans
    raw_spans = []
    start_frame = None

    for idx, score in enumerate(motion_scores):
        if score < threshold:
            if start_frame is None:
                start_frame = idx
        else:
            if start_frame is not None:
                raw_spans.append((start_frame, idx))
                start_frame = None

    # Handle video ending while stable
    if start_frame is not None:
        raw_spans.append((start_frame, len(motion_scores)))

    # Pass 2: Merge spans separated by <= merge_gap_sec
    merge_gap_frames = int(merge_gap * fps)
    merged_spans = []
    for span in raw_spans:
        if merged_spans and (span[0] - merged_spans[-1][1]) <= merge_gap_frames:
            merged_spans[-1] = (merged_spans[-1][0], span[1])
        else:
            merged_spans.append(span)

    # Pass 3: Filter by min_duration and build output
    min_frames = int(min_duration * fps)
    windows = []
    for start_f, end_f in merged_spans:
        if (end_f - start_f) >= min_frames:
            start_sec = round(start_f / fps, 3)
            end_sec = round(end_f / fps, 3)
            segment_scores = motion_scores[start_f:end_f]
            windows.append({
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration_sec": round(end_sec - start_sec, 3),
                "avg_motion": round(float(np.mean(segment_scores)), 4) if segment_scores else 0,
                "max_motion": round(float(np.max(segment_scores)), 4) if segment_scores else 0,
                "frame_range": [start_f, end_f],
            })

    logger.info(f"Window detection: {len(raw_spans)} raw spans -> {len(merged_spans)} merged -> {len(windows)} final (>={min_duration}s)")
    return windows


def slice_video(video_path: str, windows: list, config: dict) -> list:
    """Slice video into clips for each stable window.

    Returns:
        List of output file paths created.
    """
    if not windows:
        logger.info("No stable windows to slice.")
        return []

    codec = config["output"]["codec"]
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_folder = f"{base_name}_sliced"
    os.makedirs(output_folder, exist_ok=True)

    output_files = []
    for idx, window in enumerate(windows):
        start_frame = int(window["start_sec"] * fps)
        end_frame = int(window["end_sec"] * fps)
        out_path = os.path.join(output_folder, f"{base_name}_{idx + 1}.mp4")

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
