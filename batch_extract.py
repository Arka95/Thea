"""
batch_extract.py — Batch feature extraction utility.

Processes all videos in a directory, computing motion features and
suggested stable window marks. Outputs to CSV or pickle (pkl) format.

Parallelized based on detected hardware capabilities.

Usage:
    python batch_extract.py <video_directory> [--output csv|pkl] [--config config.json]

Example:
    python batch_extract.py ./videos --output csv
    python batch_extract.py D:\footage --output pkl --config custom_config.json
"""

import argparse
import csv
import json
import logging
import os
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hardware import detect_hardware, HardwareProfile
from motion_assessment import MotionAssessment, get_assessment_table

logger = logging.getLogger("thea.batch")

# Supported video extensions
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"}


def discover_videos(directory: str) -> list:
    """Recursively find all video files in a directory."""
    videos = []
    for root, _, files in os.walk(directory):
        for f in files:
            if Path(f).suffix.lower() in VIDEO_EXTENSIONS:
                videos.append(os.path.join(root, f))
    videos.sort()
    return videos


def process_single_video(args: tuple) -> dict:
    """Process one video — designed to run in a subprocess.

    Args:
        args: (video_path, config_dict)

    Returns:
        dict with video features and window marks
    """
    video_path, config = args

    # Re-import inside subprocess (required for ProcessPoolExecutor)
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from video_processing import compute_motion_scores, detect_stable_windows, get_video_info
    from motion_assessment import MotionAssessment

    result = {
        "video_path": video_path,
        "filename": os.path.basename(video_path),
        "status": "error",
        "error": None,
    }

    try:
        # Compute motion
        flow_result = compute_motion_scores(video_path, config)

        # Detect windows
        windows = detect_stable_windows(
            flow_result["motion_scores"],
            flow_result["video_info"]["fps"],
            config,
        )

        # Classify overall motion
        overall_assessment = MotionAssessment.from_score(
            flow_result["motion_stats"]["mean"],
            config["analysis"]["max_width"]
        )

        # Build feature record
        vi = flow_result["video_info"]
        ms = flow_result["motion_stats"]
        proc = flow_result["processing"]

        result.update({
            "status": "success",
            # Video metadata
            "width": vi["width"],
            "height": vi["height"],
            "fps": round(vi["fps"], 2),
            "duration_sec": vi["duration_sec"],
            "total_frames": vi["total_frames"],
            "codec": vi["codec"],
            # Motion features
            "motion_mean": ms["mean"],
            "motion_median": ms["median"],
            "motion_max": ms["max"],
            "motion_min": ms["min"],
            "motion_std": ms["std"],
            "motion_p25": ms["p25"],
            "motion_p75": ms["p75"],
            "motion_p95": ms["p95"],
            # Assessment
            "overall_assessment": overall_assessment.value,
            "stock_footage_grade": overall_assessment.stock_footage_grade,
            # Processing info
            "algorithm": proc["algorithm"],
            "backend": proc["backend"],
            "analysis_resolution": f"{proc['analysis_resolution'][0]}x{proc['analysis_resolution'][1]}",
            "processing_time_sec": proc["total_time_sec"],
            "throughput_fps": proc["fps_throughput"],
            # Windows
            "window_count": len(windows),
            "windows": windows,
            "total_extractable_sec": round(sum(w["duration_sec"] for w in windows), 2),
            "extractable_ratio": round(sum(w["duration_sec"] for w in windows) / vi["duration_sec"], 3) if vi["duration_sec"] > 0 else 0,
            # Raw scores (for pkl only — too large for CSV)
            "motion_scores": flow_result["motion_scores"],
            "raw_scores": flow_result["raw_scores"],
        })

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Failed: {video_path}: {e}")

    return result


def write_csv(results: list, output_path: str):
    """Write results to CSV (excludes per-frame scores and detailed window data)."""
    # CSV columns (flat, no nested objects)
    csv_columns = [
        "filename", "video_path", "status",
        "width", "height", "fps", "duration_sec", "total_frames", "codec",
        "motion_mean", "motion_median", "motion_max", "motion_min", "motion_std",
        "motion_p25", "motion_p75", "motion_p95",
        "overall_assessment", "stock_footage_grade",
        "algorithm", "backend", "analysis_resolution",
        "processing_time_sec", "throughput_fps",
        "window_count", "total_extractable_sec", "extractable_ratio",
        "suggested_windows",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            row = dict(r)
            # Flatten windows into a readable string for CSV
            if r.get("windows"):
                row["suggested_windows"] = " | ".join(
                    f"{w['start_sec']:.1f}-{w['end_sec']:.1f}s ({w['duration_sec']:.1f}s)"
                    for w in r["windows"]
                )
            else:
                row["suggested_windows"] = ""
            writer.writerow(row)

    logger.info(f"CSV written: {output_path} ({len(results)} videos)")


def write_pkl(results: list, output_path: str):
    """Write full results to pickle (includes per-frame scores and window details)."""
    with open(output_path, "wb") as f:
        pickle.dump(results, f, protocol=pickle.HIGHEST_PROTOCOL)
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    logger.info(f"PKL written: {output_path} ({len(results)} videos, {size_mb:.1f} MB)")


def run_batch(
    directory: str,
    output_format: str = "csv",
    config_path: Optional[str] = None,
    output_path: Optional[str] = None,
):
    """Run batch extraction on all videos in a directory.

    Args:
        directory: Path to video directory
        output_format: "csv" or "pkl"
        config_path: Path to config.json (uses default if None)
        output_path: Output file path (auto-generated if None)
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Load config
    config_file = config_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    with open(config_file, "r") as f:
        config = json.load(f)

    # Detect hardware
    hw = detect_hardware()
    logger.info("=" * 60)
    logger.info("THEA BATCH EXTRACTION")
    logger.info("=" * 60)
    logger.info(f"Directory: {os.path.abspath(directory)}")
    logger.info(f"Config:    {config_file}")
    logger.info(f"Output:    {output_format.upper()}")
    logger.info(f"\nHardware:")
    for line in hw.summary().split("\n"):
        logger.info(f"  {line}")
    logger.info("=" * 60)

    # Discover videos
    videos = discover_videos(directory)
    if not videos:
        logger.warning(f"No video files found in: {directory}")
        return

    logger.info(f"\nFound {len(videos)} video(s)")
    workers = hw.recommended_workers
    logger.info(f"Processing with {workers} parallel worker(s)\n")

    # Process in parallel
    t_start = time.perf_counter()
    results = []
    tasks = [(v, config) for v in videos]

    if workers == 1:
        # Single worker — no subprocess overhead
        for i, task in enumerate(tasks):
            logger.info(f"[{i+1}/{len(tasks)}] {os.path.basename(task[0])}")
            result = process_single_video(task)
            results.append(result)
            if result["status"] == "success":
                logger.info(f"  -> {result['overall_assessment']}, {result['window_count']} windows, {result['processing_time_sec']:.1f}s")
    else:
        # Multi-worker parallel processing
        with ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_video = {executor.submit(process_single_video, t): t[0] for t in tasks}
            for i, future in enumerate(as_completed(future_to_video)):
                video_path = future_to_video[future]
                try:
                    result = future.result()
                    results.append(result)
                    if result["status"] == "success":
                        logger.info(f"[{i+1}/{len(tasks)}] {result['filename']} -> {result['overall_assessment']}, {result['window_count']} windows")
                    else:
                        logger.error(f"[{i+1}/{len(tasks)}] {os.path.basename(video_path)} -> FAILED: {result['error']}")
                except Exception as e:
                    logger.error(f"[{i+1}/{len(tasks)}] {os.path.basename(video_path)} -> EXCEPTION: {e}")
                    results.append({"video_path": video_path, "filename": os.path.basename(video_path), "status": "error", "error": str(e)})

    t_elapsed = time.perf_counter() - t_start

    # Sort results by original order
    video_order = {v: i for i, v in enumerate(videos)}
    results.sort(key=lambda r: video_order.get(r.get("video_path", ""), 999))

    # Write output
    if not output_path:
        dir_name = os.path.basename(os.path.abspath(directory))
        output_path = f"{dir_name}_features.{output_format}"

    if output_format == "csv":
        write_csv(results, output_path)
    else:
        write_pkl(results, output_path)

    # Summary
    success = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - success
    total_extractable = sum(r.get("total_extractable_sec", 0) for r in results)
    total_duration = sum(r.get("duration_sec", 0) for r in results)

    logger.info(f"\n{'='*60}")
    logger.info("BATCH SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"  Videos processed: {success}/{len(results)} ({failed} failed)")
    logger.info(f"  Total video duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")
    logger.info(f"  Total extractable: {total_extractable:.1f}s ({total_extractable/60:.1f} min)")
    logger.info(f"  Extraction ratio: {total_extractable/total_duration*100:.1f}%" if total_duration > 0 else "  Extraction ratio: N/A")
    logger.info(f"  Processing time: {t_elapsed:.1f}s ({t_elapsed/60:.1f} min)")
    logger.info(f"  Output: {output_path}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Thea Batch Feature Extraction — Process all videos in a directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_extract.py ./videos
  python batch_extract.py D:\\footage --output pkl
  python batch_extract.py ./clips --config strict_config.json --output csv
        """,
    )
    parser.add_argument("directory", help="Directory containing video files (searched recursively)")
    parser.add_argument("--output", choices=["csv", "pkl"], default="csv", help="Output format (default: csv)")
    parser.add_argument("--config", default=None, help="Path to config.json (default: ./config.json)")
    parser.add_argument("--output-path", default=None, help="Output file path (auto-generated if not specified)")

    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a directory")
        sys.exit(1)

    run_batch(
        directory=args.directory,
        output_format=args.output,
        config_path=args.config,
        output_path=args.output_path,
    )
