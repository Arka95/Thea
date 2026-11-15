"""
motion_assessment/analyzer.py — Motion scoring and stable window detection.

Computes per-frame motion scores and identifies stable windows suitable for extraction.

NOTE (TODO): Currently, optical flow metadata (per-frame angle, max_magnitude) is computed
during motion scoring but only the motion_score is used for window detection. A future
enhancement could attach compact per-window flow metadata (dominant direction, consistency,
acceleration profile) to each detected window without re-processing, since the raw per-frame
data is already available in memory. This would enable richer window-level metadata in the
output without additional overhead.
"""

import os
import cv2
import numpy as np
import time
import logging
from scipy.ndimage import gaussian_filter1d

from motion_assessment.optical_flow import create_flow_calculator
from utils.video_io import get_video_info
from utils.metrics import track, get_default_collector

logger = logging.getLogger("thea")


@track(context_fn=lambda a, kw: {"video": os.path.basename(a[0]) if a else ""})
def compute_motion_scores(video_path: str, config: dict) -> dict:
    """Compute per-frame motion scores using optical flow.

    Returns:
        dict with: motion_scores, raw_scores, motion_stats, video_info, processing, flow_calculator_stats
    """
    max_width = config["analysis"]["max_width"]
    sigma = config["analysis"]["motion_smoothing_sigma"]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    scale = max_width / w if w > max_width else 1.0
    analysis_w = int(w * scale)
    analysis_h = int(h * scale)

    logger.info(f"Video: {w}x{h} @ {fps:.1f}fps, {total_frames} frames ({total_frames/fps:.1f}s)")
    logger.info(f"Analysis resolution: {analysis_w}x{analysis_h} (scale={scale:.3f})")

    flow_calc = create_flow_calculator(config)
    logger.info(f"Optical flow: {config['optical_flow']['algorithm']} ({flow_calc.backend})")

    ret, frame = cap.read()
    if not ret:
        raise ValueError("Error reading first frame from video.")

    prev_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if scale < 1.0:
        prev_gray = cv2.resize(prev_gray, (analysis_w, analysis_h), interpolation=cv2.INTER_AREA)

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

    smoothed_scores = gaussian_filter1d(raw_scores, sigma=sigma).tolist() if raw_scores else []

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
        "frame_metadata": frame_metadata_list,
    }


@track()
def detect_stable_windows(motion_scores: list, fps: float, config: dict) -> list:
    """Find stable windows where motion is below threshold.

    Returns:
        List of dicts: [{start_sec, end_sec, duration_sec, avg_motion, max_motion, frame_range}, ...]
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

    # Pass 3: Filter by min_duration
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

    logger.info(f"Window detection: {len(raw_spans)} raw -> {len(merged_spans)} merged -> {len(windows)} final (>={min_duration}s)")
    return windows
