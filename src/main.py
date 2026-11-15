"""
main.py — Unified CLI entry point for Thea video extraction tool.

Commands:
    python -m main downscale <path> [--preset NAME] [--output DIR]
    python -m main analyze <path> [--preset NAME] [--output csv|pkl]
    python -m main slice <path> [--preset NAME]
    python -m main pipeline <path> [--preset NAME] [--output DIR]
    python -m main merge <video ...> [--manifest FILE] [--output-path FILE]
    python -m main presets
    python -m main crop <path> <width> <height> <x> <y> [--output-path FILE]
    python -m main centercrop <path> <width> <height> [--output-path FILE]
    python -m main ratiocrop <path> <ratiox> <ratioy> [--output-path FILE]
    python -m main pan <path> [--duration SECONDS] [--output-path FILE]
    python -m main caption <path> --model MODEL [--contact-sheet FILE]
    python -m main index [ROOT] [LIMIT]

Path can be a single video file (single mode) or a directory (batch mode).
"""

import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import cv2

from cli.commands import (
    cmd_caption,
    cmd_centercrop,
    cmd_crop,
    cmd_importindex,
    cmd_index,
    cmd_pan,
    cmd_ratiocrop,
    cmd_search,
    print_result,
)
from downscaler.downscaler import batch_downscale, downscale_video
from merger import merge_videos, read_video_manifest
from motion_assessment.analyzer import compute_motion_scores, detect_stable_windows
from motion_assessment.assessment import MotionAssessment
from slicer.slicer import slice_video
from tools.walkdir import add_index_arguments
from utils.config_loader import list_presets, load_config_file, load_preset
from utils.hardware import detect_hardware
from utils.metrics import log_default_metrics, reset_default_collector, track
from utils.pipeline_logger import log_pipeline_stats, log_video_meta
from utils.settings import (
    DOWNSAMPLED_DIR,
    get_downsampled_path,
    get_merged_dir,
    get_sliced_dir,
    resolve_data_dir,
)
from utils.video_io import discover_videos, get_video_info, is_video_file

logger = logging.getLogger("thea")


def setup_logging(stream=None):
    """Configure console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=stream if stream is not None else sys.stdout,
    )


def print_header(config: dict, hw=None):
    """Print startup banner with system info."""
    logger.info("=" * 60)
    logger.info("THEA - Video Stock-Footage Extractor")
    logger.info("=" * 60)
    logger.info(f"  Preset:    {config.get('_preset_name', 'custom')}")
    logger.info(f"  OpenCV:    {cv2.__version__}")
    cuda_count = cv2.cuda.getCudaEnabledDeviceCount()
    logger.info(
        f"  CUDA:      {'YES (' + str(cuda_count) + ' device(s))' if cuda_count > 0 else 'NO'}"
    )
    if hw:
        logger.info(f"  Workers:   {hw.recommended_workers}")
    logger.info("=" * 60)


def is_batch_mode(path: str) -> bool:
    """Determine if path is a directory (batch) or file (single)."""
    return os.path.isdir(path)


# ---------------------------------------------------------------------------
# Command: downscale
# ---------------------------------------------------------------------------


def cmd_downscale(args, config):
    """Downscale video(s) for optimized motion assessment consumption."""
    hw = detect_hardware()
    data_dir = resolve_data_dir(args.path)
    max_width = args.width
    lossless = getattr(args, "lossless", False)
    codec = config["output"]["codec"]

    if is_batch_mode(args.path):
        output_dir = args.output or os.path.join(data_dir, DOWNSAMPLED_DIR)
        results = batch_downscale(
            source_dir=args.path,
            sink_dir=output_dir,
            max_width=max_width,
            codec=codec,
            workers=hw.recommended_workers,
            lossless=lossless,
        )
        logger.info(f"Batch downscale complete: {len(results)} videos -> {output_dir}")
        return {"results": results}
    else:
        base = os.path.splitext(os.path.basename(args.path))[0]
        output_dir = args.output or os.path.join(data_dir, DOWNSAMPLED_DIR)
        os.makedirs(output_dir, exist_ok=True)
        ext = ".avi" if lossless else ".mp4"
        out_path = os.path.join(output_dir, f"{base}{ext}")
        result = downscale_video(args.path, out_path, max_width, codec, lossless=lossless)
        logger.info(f"Downscaled: {result['original_resolution']} -> {result['output_resolution']}")
        logger.info(
            f"Output: {result['output']} ({result['size_reduction']*100:.0f}% smaller, lossless={lossless})"
        )
        return {"results": [result]}


# ---------------------------------------------------------------------------
# Command: analyze
# ---------------------------------------------------------------------------


def cmd_analyze(args, config):
    """Run motion assessment on video(s)."""
    hw = detect_hardware()

    if is_batch_mode(args.path):
        return _batch_analyze(args, config, hw)
    else:
        result, windows = _single_analyze(args.path, config)
        return {
            "video_info": result["video_info"],
            "motion_stats": result["motion_stats"],
            "windows": windows,
        }


def _write_video_metadata(video_path: str, result: dict, windows: list, data_dir: str):
    """Write per-video metadata JSON to the data directory.

    Uses the original video path for identification, with fps/frames/duration
    from the analyzed video (these are preserved across downscaling).
    """
    overall = MotionAssessment.from_score(
        result["motion_stats"]["mean"],
        result["processing"].get("analysis_width", 320),
    )

    vi = result["video_info"]
    metadata = {
        "video": {
            "filename": os.path.basename(video_path),
            "fps": vi["fps"],
            "total_frames": vi["total_frames"],
            "duration_sec": vi.get(
                "duration_sec", round(vi["total_frames"] / vi["fps"], 2) if vi["fps"] > 0 else 0
            ),
        },
        "motion_stats": result["motion_stats"],
        "overall_assessment": overall.value,
        "windows_detected": windows,
    }
    base = os.path.splitext(os.path.basename(video_path))[0]
    meta_path = os.path.join(data_dir, f"{base}_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Metadata: {meta_path}")
    return meta_path


def _single_analyze(video_path: str, config: dict):
    """Analyze a single video."""
    data_dir = resolve_data_dir(video_path)
    result = compute_motion_scores(video_path, config)
    windows = detect_stable_windows(result["motion_scores"], result["video_info"]["fps"], config)

    overall = MotionAssessment.from_score(
        result["motion_stats"]["mean"], config["analysis"]["max_width"]
    )

    logger.info(
        f"\nMotion Stats: mean={result['motion_stats']['mean']:.4f}, "
        f"max={result['motion_stats']['max']:.4f}, std={result['motion_stats']['std']:.4f}"
    )
    logger.info(f"Assessment: {overall.value} ({overall.description})")
    logger.info(f"Stock footage grade: {'YES' if overall.stock_footage_grade else 'NO'}")
    logger.info(f"Stable windows: {len(windows)}")
    for i, w in enumerate(windows):
        logger.info(
            f"  [{i+1}] {w['start_sec']:.1f}s - {w['end_sec']:.1f}s ({w['duration_sec']:.1f}s, avg={w['avg_motion']:.3f})"
        )

    _write_video_metadata(video_path, result, windows, data_dir)
    return result, windows


def _process_video_for_batch(args_tuple: tuple) -> dict:
    """Worker for batch analyze (runs in subprocess)."""
    video_path, config = args_tuple
    from motion_assessment.analyzer import compute_motion_scores, detect_stable_windows
    from motion_assessment.assessment import MotionAssessment

    try:
        result = compute_motion_scores(video_path, config)
        windows = detect_stable_windows(
            result["motion_scores"], result["video_info"]["fps"], config
        )
        overall = MotionAssessment.from_score(
            result["motion_stats"]["mean"], config["analysis"]["max_width"]
        )

        return {
            "status": "success",
            "video_path": video_path,
            "filename": os.path.basename(video_path),
            "width": result["video_info"]["width"],
            "height": result["video_info"]["height"],
            "fps": round(result["video_info"]["fps"], 2),
            "duration_sec": result["video_info"]["duration_sec"],
            "motion_mean": result["motion_stats"]["mean"],
            "motion_max": result["motion_stats"]["max"],
            "motion_std": result["motion_stats"]["std"],
            "overall_assessment": overall.value,
            "stock_footage_grade": overall.stock_footage_grade,
            "window_count": len(windows),
            "windows": windows,
            "total_extractable_sec": round(sum(w["duration_sec"] for w in windows), 2),
            "motion_scores": result["motion_scores"],
            "raw_scores": result["raw_scores"],
        }
    except Exception as e:
        return {
            "status": "error",
            "video_path": video_path,
            "filename": os.path.basename(video_path),
            "error": str(e),
        }


def _batch_analyze(args, config, hw):
    """Batch analyze all videos in a directory."""
    import csv
    import pickle

    data_dir = resolve_data_dir(args.path)
    videos = discover_videos(args.path)
    if not videos:
        logger.warning(f"No videos found in: {args.path}")
        return {"results": []}

    logger.info(f"Batch analyze: {len(videos)} videos, {hw.recommended_workers} workers")
    tasks = [(v, config) for v in videos]
    results = []

    t_start = time.perf_counter()
    if hw.recommended_workers <= 1:
        for i, task in enumerate(tasks):
            logger.info(f"  [{i+1}/{len(tasks)}] {os.path.basename(task[0])}")
            results.append(_process_video_for_batch(task))
    else:
        with ProcessPoolExecutor(max_workers=hw.recommended_workers) as executor:
            futures = {executor.submit(_process_video_for_batch, t): t[0] for t in tasks}
            for i, future in enumerate(as_completed(futures)):
                r = future.result()
                results.append(r)
                if r["status"] == "success":
                    logger.info(
                        f"  [{i+1}/{len(tasks)}] {r['filename']} -> {r['overall_assessment']}, {r['window_count']} windows"
                    )

    t_elapsed = time.perf_counter() - t_start

    # Output
    output_fmt = getattr(args, "output", "csv") or "csv"
    dir_name = os.path.basename(os.path.abspath(args.path))
    out_path = getattr(args, "output_path", None) or os.path.join(
        data_dir, f"{dir_name}_features.{output_fmt}"
    )

    if output_fmt == "pkl":
        with open(out_path, "wb") as f:
            pickle.dump(results, f)
    else:
        csv_cols = [
            "filename",
            "status",
            "duration_sec",
            "motion_mean",
            "motion_max",
            "overall_assessment",
            "stock_footage_grade",
            "window_count",
            "total_extractable_sec",
        ]
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csv_cols, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results)

    success = sum(1 for r in results if r["status"] == "success")
    logger.info(f"\nBatch complete: {success}/{len(results)} in {t_elapsed:.1f}s -> {out_path}")
    return {
        "output": out_path,
        "results": [
            {
                key: value
                for key, value in item.items()
                if key not in {"raw_scores", "motion_scores"}
            }
            for item in results
        ],
    }


# ---------------------------------------------------------------------------
# Command: slice
# ---------------------------------------------------------------------------


def cmd_slice(args, config):
    """Slice video(s) into stable window clips."""
    data_dir = resolve_data_dir(args.path)
    default_output = get_sliced_dir(data_dir)
    outputs = []

    if is_batch_mode(args.path):
        videos = discover_videos(args.path)
        for i, video in enumerate(videos):
            logger.info(f"\n[{i+1}/{len(videos)}] {os.path.basename(video)}")
            result = compute_motion_scores(video, config)
            windows = detect_stable_windows(
                result["motion_scores"], result["video_info"]["fps"], config
            )
            if windows:
                output_dir = args.output or default_output
                outputs.extend(slice_video(video, windows, config, output_dir=output_dir))
            else:
                logger.info("  No stable windows found.")
    else:
        result = compute_motion_scores(args.path, config)
        windows = detect_stable_windows(
            result["motion_scores"], result["video_info"]["fps"], config
        )
        if windows:
            output_dir = args.output or default_output
            files = slice_video(args.path, windows, config, output_dir=output_dir)
            outputs.extend(files)
            logger.info(f"Created {len(files)} clip(s) -> {output_dir}")
        else:
            logger.info("No stable windows found.")
    return {"clips": outputs}


# ---------------------------------------------------------------------------
# Command: pipeline (downscale -> analyze -> slice)
# ---------------------------------------------------------------------------


def _run_single_pipeline(video_path: str, config: dict, data_dir: str):
    """Run the full pipeline on a single video with settings-based paths and CSV logging."""
    max_width = config["analysis"]["max_width"]
    lossless = False  # Pipeline always uses optimized (lossy) downscale
    codec = config["output"]["codec"]

    t_total_start = time.perf_counter()

    # Step 1: Downscale (skip if already exists)
    t_ds_start = time.perf_counter()
    downsampled_path = get_downsampled_path(video_path, data_dir, lossless=lossless)

    if os.path.exists(downsampled_path):
        logger.info(f"Downsampled video exists, skipping: {downsampled_path}")
        ds_time = 0.0
    else:
        downscale_video(video_path, downsampled_path, max_width, codec, lossless=lossless)
        ds_time = time.perf_counter() - t_ds_start
        logger.info(f"Downsampled: {downsampled_path} ({ds_time:.2f}s)")

    # Step 2: Motion assessment (analyze the downsampled video)
    t_ma_start = time.perf_counter()
    result = compute_motion_scores(downsampled_path, config)
    windows = detect_stable_windows(result["motion_scores"], result["video_info"]["fps"], config)
    ma_time = time.perf_counter() - t_ma_start

    overall = MotionAssessment.from_score(
        result["motion_stats"]["mean"], config["analysis"]["max_width"]
    )
    logger.info(
        f"\nMotion Stats: mean={result['motion_stats']['mean']:.4f}, "
        f"max={result['motion_stats']['max']:.4f}, std={result['motion_stats']['std']:.4f}"
    )
    logger.info(f"Assessment: {overall.value} ({overall.description})")
    logger.info(f"Stable windows: {len(windows)}")
    for i, w in enumerate(windows):
        logger.info(
            f"  [{i+1}] {w['start_sec']:.1f}s - {w['end_sec']:.1f}s ({w['duration_sec']:.1f}s, avg={w['avg_motion']:.3f})"
        )

    # Step 3: Slice from ORIGINAL video into data_dir/sliced/
    t_sl_start = time.perf_counter()
    sl_time = 0.0
    files = []
    if windows:
        output_dir = get_sliced_dir(data_dir)
        files = slice_video(video_path, windows, config, output_dir=output_dir)
        sl_time = time.perf_counter() - t_sl_start
        logger.info(f"\nSliced into {len(files)} clip(s) -> {output_dir}")
    else:
        logger.info("\nNo stable windows found.")

    t_total = time.perf_counter() - t_total_start

    # Step 4: Log to CSVs
    vi = result["video_info"]
    video_duration = vi.get("total_frames", 0) / vi.get("fps", 1) if vi.get("fps", 0) > 0 else 0

    log_video_meta(data_dir, video_path, result, windows, config)
    log_pipeline_stats(data_dir, video_path, video_duration, ds_time, ma_time, sl_time, t_total)

    # Step 5: Write metadata JSON
    metadata = _write_video_metadata(video_path, result, windows, data_dir)
    return {
        "source": video_path,
        "analysis_video": downsampled_path,
        "clips": files,
        "metadata": metadata,
        "windows": windows,
    }


def cmd_pipeline(args, config):
    """Run the full pipeline: downscale -> analyze -> slice."""
    data_dir = os.path.abspath(args.output) if args.output else resolve_data_dir(args.path)
    os.makedirs(data_dir, exist_ok=True)
    hw = detect_hardware()
    print_header(config, hw)
    results = []

    if is_batch_mode(args.path):
        videos = discover_videos(args.path)
        logger.info(f"\nPipeline: {len(videos)} videos, data_dir: {data_dir}")
        for i, video in enumerate(videos):
            logger.info(f"\n{'='*40} [{i+1}/{len(videos)}] {os.path.basename(video)}")
            results.append(_run_single_pipeline(video, config, data_dir))
    else:
        logger.info(f"Data directory: {data_dir}")
        results.append(_run_single_pipeline(args.path, config, data_dir))
    return {"results": results}


# ---------------------------------------------------------------------------
# Command: merge
# ---------------------------------------------------------------------------


def cmd_merge(args, config):
    """Concatenate ordered videos without modifying the inputs."""
    if args.manifest and args.paths:
        raise ValueError("Use video paths or --manifest, not both.")
    paths = read_video_manifest(args.manifest) if args.manifest else args.paths
    if len(paths) < 2:
        raise ValueError("Provide at least two video paths or a manifest containing them.")
    output = args.output_path
    if output is None:
        data_dir = resolve_data_dir(paths[0])
        name = f"merge_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.mp4"
        output = os.path.join(get_merged_dir(data_dir), name)
    result = merge_videos(paths, output)
    logger.info(
        f"Merged {result['input_count']} videos -> {result['output']} "
        f"({result['duration_sec']:.1f}s, {result['width']}x{result['height']}, "
        f"stream copy, {result['time_sec']:.1f}s)"
    )
    return result


# ---------------------------------------------------------------------------
# Command: presets
# ---------------------------------------------------------------------------


def cmd_presets(args, config):
    """List available configuration presets."""
    presets = list_presets()
    logger.info("Available presets:")
    logger.info(f"{'Name':<15} {'Threshold':<12} {'Min Duration':<14} {'Path'}")
    logger.info("-" * 70)
    results = []
    for name, path in presets.items():
        with open(path) as f:
            cfg = json.load(f)
        thresh = cfg["window_detection"]["motion_threshold"]
        min_d = cfg["window_detection"]["min_duration_sec"]
        logger.info(f"{name:<15} {thresh:<12} {min_d:<14.1f} {path}")
        results.append(
            {"name": name, "path": str(path), "motion_threshold": thresh, "min_duration_sec": min_d}
        )
    return {"presets": results}


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="thea",
        description="Thea — Video stock-footage extraction tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m main pipeline sample.MP4 --preset cinematic
  python -m main analyze ./videos/ --preset strict --output pkl
  python -m main downscale ./raw_footage/ --output ./downscaled/
  python -m main slice sample.MP4 --preset permissive
  python -m main presets
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # downscale
    p = subparsers.add_parser("downscale", help="Downscale video(s) for optimized analysis")
    p.add_argument("path", help="Video file or directory")
    p.add_argument("--preset", default="cinematic", help="Config preset name (default: cinematic)")
    p.add_argument("--config", default=None, help="Explicit config file path (overrides --preset)")
    p.add_argument("--output", default=None, help="Output directory")
    p.add_argument("--width", type=int, default=320, help="Target width in pixels (default: 320)")
    p.add_argument(
        "--lossless",
        action="store_true",
        help="Lossless downscale (FFV1 codec, LANCZOS4 interpolation, .avi output)",
    )

    # analyze
    p = subparsers.add_parser("analyze", help="Run motion assessment on video(s)")
    p.add_argument("path", help="Video file or directory")
    p.add_argument("--preset", default="cinematic", help="Config preset name")
    p.add_argument("--config", default=None, help="Explicit config file path")
    p.add_argument("--output", default="csv", choices=["csv", "pkl"], help="Batch output format")
    p.add_argument("--output-path", default=None, help="Output file path")

    # slice
    p = subparsers.add_parser("slice", help="Slice video(s) into stable window clips")
    p.add_argument("path", help="Video file or directory")
    p.add_argument("--preset", default="cinematic", help="Config preset name")
    p.add_argument("--config", default=None, help="Explicit config file path")
    p.add_argument("--output", default=None, help="Output directory for clips")

    # pipeline
    p = subparsers.add_parser("pipeline", help="Full pipeline: analyze + slice")
    p.add_argument("path", help="Video file or directory")
    p.add_argument("--preset", default="cinematic", help="Config preset name")
    p.add_argument("--config", default=None, help="Explicit config file path")
    p.add_argument("--output", default=None, help="Output directory")

    # presets
    subparsers.add_parser("presets", help="List available configuration presets")

    p = subparsers.add_parser("merge", help="Merge ordered, compatible videos without re-encoding")
    p.add_argument("paths", nargs="*", help="Input videos in playback order")
    p.add_argument("--manifest", help="UTF-8 file containing one input path per line, in order")
    p.add_argument(
        "--output-path", help="Output file (default: data_dir/merged/merge_<timestamp>.mp4)"
    )

    for name in ("crop", "centercrop", "ratiocrop", "pan"):
        p = subparsers.add_parser(name, help=f"{name.capitalize()} one source video")
        p.add_argument("path", help="Source video file or directory")
        p.add_argument("--output-path", help="Output file (default: data_dir/cropandpan)")
        if name in {"crop", "centercrop"}:
            p.add_argument("width", type=int, help="Crop width in pixels")
            p.add_argument("height", type=int, help="Crop height in pixels")
        if name == "crop":
            p.add_argument("x", type=int, help="Left edge in pixels")
            p.add_argument("y", type=int, help="Top edge in pixels")
        if name == "ratiocrop":
            p.add_argument("ratiox", type=float, help="Aspect-ratio width")
            p.add_argument("ratioy", type=float, help="Aspect-ratio height")
        if name == "pan":
            for field in ("resolutionx", "resolutiony", "startx", "starty", "endx", "endy"):
                p.add_argument(f"--{field}", type=int, help=f"{field} in pixels")
            p.add_argument("--ratiox", type=float, help="Aspect-ratio width (default ratio: 9:16)")
            p.add_argument("--ratioy", type=float, help="Aspect-ratio height")
            p.add_argument(
                "--duration", type=float, help="Seconds from source start (default: full duration)"
            )

    p = subparsers.add_parser("caption", help="Caption sampled frames with a selected vision model")
    p.add_argument("path", help="Source video file")
    p.add_argument("--model", required=True, help="Image-capable model ID served by the endpoint")
    p.add_argument(
        "--base-url", default="http://localhost:1234/v1", help="Vision endpoint base URL"
    )
    p.add_argument(
        "--api-key-env",
        default="THEA_CAPTION_API_KEY",
        help="Environment variable holding the API key",
    )
    p.add_argument("--timeout-sec", type=int, default=120, help="Endpoint timeout in seconds")
    p.add_argument(
        "--contact-sheet", help="Retain a new JPEG at this path (default: auto-cleaned sheet)"
    )
    p.add_argument("--sampling-video", help="Optional existing downscaled video to sample")
    p.add_argument("--sample-count", type=int, default=12, help="Maximum sampled frames")
    p.add_argument("--frame-width", type=int, default=176, help="Contact-sheet tile width")
    p.add_argument("--frame-height", type=int, default=144, help="Contact-sheet tile height")
    p.add_argument("--columns", type=int, default=4, help="Contact-sheet columns")
    p.add_argument(
        "--location-in-metadata", action="store_true", help="Omit location from the caption"
    )
    p.add_argument(
        "--timestamp-in-metadata", action="store_true", help="Omit time of day from the caption"
    )
    p.add_argument("--context", help="Additional trusted caption context")

    p = subparsers.add_parser("index", help="Index video metadata (alias of thea-index)")
    add_index_arguments(p)
    p = subparsers.add_parser(
        "importindex", help="Merge old catalogues into the shared video index"
    )
    p.add_argument("paths", nargs="+", help="Read-only source SQLite catalogue files")
    p = subparsers.add_parser("search", help="Search indexed descriptions and video metadata")
    p.add_argument(
        "query", help="Descriptive search, for example: drone footage in Arunachal for nature"
    )
    p.add_argument("--limit", type=int, default=20, help="Maximum results, from 1 to 100")
    return parser


@track(context_fn=lambda args, kwargs: {"operation": args[0] if args else kwargs.get("command")})
def run_command(command: str, **arguments) -> dict:
    """Execute one CLI/MCP operation and return its structured result."""
    parser = build_parser()
    subparsers = next(action for action in parser._actions if action.dest == "command")
    if command not in subparsers.choices:
        raise ValueError(f"Unknown command: {command}")
    selected = subparsers.choices[command]
    defaults = {
        action.dest: action.default for action in selected._actions if action.dest != "help"
    }
    unknown = arguments.keys() - defaults.keys()
    if unknown:
        raise ValueError(f"Unknown arguments: {', '.join(sorted(unknown))}")
    defaults.update(arguments)
    args = argparse.Namespace(**defaults)
    if command in {"downscale", "analyze", "slice", "pipeline"}:
        config = load_config_file(args.config) if args.config else load_preset(args.preset)
    else:
        config = {}
    commands = {
        "downscale": cmd_downscale,
        "analyze": cmd_analyze,
        "slice": cmd_slice,
        "pipeline": cmd_pipeline,
        "presets": cmd_presets,
        "merge": cmd_merge,
        "crop": cmd_crop,
        "centercrop": cmd_centercrop,
        "ratiocrop": cmd_ratiocrop,
        "pan": cmd_pan,
        "caption": cmd_caption,
        "index": cmd_index,
        "importindex": cmd_importindex,
        "search": cmd_search,
    }
    return commands[command](args, config)


def main():
    parser = build_parser()
    args = parser.parse_args()
    json_commands = {
        "crop",
        "centercrop",
        "ratiocrop",
        "pan",
        "caption",
        "index",
        "importindex",
        "search",
    }
    setup_logging(sys.stderr if args.command in json_commands else sys.stdout)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Reset metrics for this run
    reset_default_collector()

    try:
        arguments = vars(args).copy()
        command = arguments.pop("command")
        result = run_command(command, **arguments)
        if command in json_commands:
            print_result(result)
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if args.command != "presets":
            log_default_metrics()


if __name__ == "__main__":
    main()
