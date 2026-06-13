"""Thea CLI — pipeline-config-driven video extraction tool.

Commands:
    thea pipeline <path> [--pipeline-config FILE] [--preset NAME]
    thea downscale <path> [--preset NAME] [--output DIR]
    thea analyze <path> [--preset NAME]
    thea slice <path> [--preset NAME]
    thea operations
    thea presets
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import thea  # triggers sys.path setup

from utils.config_loader import load_preset, list_presets, load_config_file
from utils.hardware import detect_hardware
from utils.video_io import discover_videos, get_video_info, is_video_file
from utils.settings import resolve_data_dir, get_downsampled_path, get_sliced_dir
from thea.observability import get_default_collector, reset_default_collector
from thea.pipeline import PipelineContext, load_pipeline_config, run_pipeline
from thea.operations import get_registry

logger = logging.getLogger("thea")


def setup_logging(verbose: bool = False):
    """Configure console logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )


# ---------------------------------------------------------------------------
# Command: pipeline (config-driven)
# ---------------------------------------------------------------------------

def cmd_pipeline(args, config):
    """Run a pipeline from a JSON pipeline config or the default (downscale -> analyze -> slice)."""
    hw = detect_hardware()

    if args.pipeline_config:
        pipeline_config = load_pipeline_config(args.pipeline_config)
    else:
        # Default pipeline: downscale -> analyze -> slice
        pipeline_config = {
            "version": 1,
            "pipeline": [
                {"operation": "downscale", "config": {}},
                {"operation": "analyze", "config": {}},
                {"operation": "slice", "config": {}},
            ],
        }

    source = Path(args.path).resolve()

    if source.is_dir():
        videos = discover_videos(str(source))
        logger.info(f"Pipeline: {len(videos)} videos from {source}")
        for i, video_path in enumerate(videos):
            logger.info(f"\n[{i + 1}/{len(videos)}] {os.path.basename(video_path)}")
            _run_pipeline_single(video_path, pipeline_config, config)
    else:
        _run_pipeline_single(str(source), pipeline_config, config)


def _run_pipeline_single(video_path: str, pipeline_config: dict, base_config: dict):
    """Execute pipeline on a single video."""
    data_dir = resolve_data_dir(video_path)
    source = Path(video_path).resolve()

    context = PipelineContext(
        source_path=source,
        current_video_path=source,
        data_dir=Path(data_dir),
    )

    t_start = time.perf_counter()
    context = run_pipeline(context, pipeline_config, base_config)
    t_elapsed = time.perf_counter() - t_start

    # Summary
    n_windows = len(context.stable_windows) if context.stable_windows else 0
    n_clips = len(context.clips) if context.clips else 0
    logger.info(f"  Done in {t_elapsed:.1f}s — {n_windows} windows, {n_clips} clips")

    return context


# ---------------------------------------------------------------------------
# Command: operations (list available operations)
# ---------------------------------------------------------------------------

def cmd_operations(args, config):
    """List all registered pipeline operations."""
    registry = get_registry()
    print(json.dumps(
        {name: op.to_dict() for name, op in sorted(registry.items())},
        indent=2,
    ))


# ---------------------------------------------------------------------------
# Command: downscale (standalone)
# ---------------------------------------------------------------------------

def cmd_downscale(args, config):
    """Downscale video(s) for optimized motion assessment."""
    from downscaler.downscaler import downscale_video, batch_downscale

    hw = detect_hardware()
    data_dir = resolve_data_dir(args.path)
    max_width = args.width
    lossless = getattr(args, "lossless", False)
    codec = config["output"]["codec"]

    if os.path.isdir(args.path):
        output_dir = args.output or os.path.join(data_dir, "downscaled")
        results = batch_downscale(
            source_dir=args.path,
            sink_dir=output_dir,
            max_width=max_width,
            codec=codec,
            workers=hw.recommended_workers,
            lossless=lossless,
        )
        logger.info(f"Batch downscale: {len(results)} videos -> {output_dir}")
    else:
        output_dir = args.output or os.path.join(data_dir, "downscaled")
        os.makedirs(output_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(args.path))[0]
        ext = ".avi" if lossless else ".mp4"
        out_path = os.path.join(output_dir, f"{base}{ext}")
        result = downscale_video(args.path, out_path, max_width, codec, lossless=lossless)
        logger.info(f"Downscaled: {result['output']} ({result['processing_time_sec']:.1f}s)")


# ---------------------------------------------------------------------------
# Command: analyze (standalone)
# ---------------------------------------------------------------------------

def cmd_analyze(args, config):
    """Run motion assessment on video(s)."""
    from motion_assessment.analyzer import compute_motion_scores, detect_stable_windows

    source = args.path
    if os.path.isdir(source):
        videos = discover_videos(source)
        for i, video in enumerate(videos):
            logger.info(f"[{i + 1}/{len(videos)}] {os.path.basename(video)}")
            result = compute_motion_scores(video, config)
            windows = detect_stable_windows(result["motion_scores"], result["video_info"]["fps"], config)
            logger.info(f"  {len(windows)} stable windows, mean_motion={result['motion_stats']['mean']:.4f}")
    else:
        result = compute_motion_scores(source, config)
        windows = detect_stable_windows(result["motion_scores"], result["video_info"]["fps"], config)
        print(json.dumps({
            "motion_stats": result["motion_stats"],
            "windows": windows,
            "processing": result["processing"],
        }, indent=2))


# ---------------------------------------------------------------------------
# Command: slice (standalone)
# ---------------------------------------------------------------------------

def cmd_slice(args, config):
    """Slice video(s) into stable window clips."""
    from motion_assessment.analyzer import compute_motion_scores, detect_stable_windows
    from slicer.slicer import slice_video

    source = args.path
    data_dir = resolve_data_dir(source)
    output_dir = args.output or get_sliced_dir(data_dir)

    if os.path.isdir(source):
        videos = discover_videos(source)
        for i, video in enumerate(videos):
            logger.info(f"[{i + 1}/{len(videos)}] {os.path.basename(video)}")
            result = compute_motion_scores(video, config)
            windows = detect_stable_windows(result["motion_scores"], result["video_info"]["fps"], config)
            if windows:
                slice_video(video, windows, config, output_dir=output_dir)
    else:
        result = compute_motion_scores(source, config)
        windows = detect_stable_windows(result["motion_scores"], result["video_info"]["fps"], config)
        if windows:
            files = slice_video(source, windows, config, output_dir=output_dir)
            logger.info(f"Created {len(files)} clip(s) -> {output_dir}")
        else:
            logger.info("No stable windows found.")


# ---------------------------------------------------------------------------
# Command: presets
# ---------------------------------------------------------------------------

def cmd_presets(args, config):
    """List available configuration presets."""
    presets = list_presets()
    print(f"{'Name':<15} {'Threshold':<12} {'Min Duration':<14} {'Path'}")
    print("-" * 70)
    for name, path in presets.items():
        with open(path) as f:
            cfg = json.load(f)
        thresh = cfg["window_detection"]["motion_threshold"]
        min_d = cfg["window_detection"]["min_duration_sec"]
        print(f"{name:<15} {thresh:<12} {min_d:<14.1f} {path}")


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="thea",
        description="Thea — GPU-accelerated video stock-footage extraction CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  thea pipeline video.mp4 --preset cinematic
  thea pipeline ./videos/ --pipeline-config my_pipeline.json
  thea downscale video.mp4 --width 480
  thea analyze video.mp4 --preset strict
  thea slice video.mp4 --preset permissive
  thea operations
  thea presets
        """,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # pipeline
    p = subparsers.add_parser("pipeline", help="Run pipeline (config-driven or default)")
    p.add_argument("path", help="Video file or directory")
    p.add_argument("--preset", default="cinematic", help="Config preset (default: cinematic)")
    p.add_argument("--config", default=None, help="Explicit Thea config file path")
    p.add_argument("--pipeline-config", default=None, help="Pipeline definition JSON file")
    p.add_argument("--output", default=None, help="Output directory override")

    # downscale
    p = subparsers.add_parser("downscale", help="Downscale video(s) for analysis")
    p.add_argument("path", help="Video file or directory")
    p.add_argument("--preset", default="cinematic", help="Config preset")
    p.add_argument("--config", default=None, help="Explicit config file path")
    p.add_argument("--output", default=None, help="Output directory")
    p.add_argument("--width", type=int, default=320, help="Target width (default: 320)")
    p.add_argument("--lossless", action="store_true", help="Lossless mode (FFV1, .avi)")

    # analyze
    p = subparsers.add_parser("analyze", help="Run motion assessment")
    p.add_argument("path", help="Video file or directory")
    p.add_argument("--preset", default="cinematic", help="Config preset")
    p.add_argument("--config", default=None, help="Explicit config file path")

    # slice
    p = subparsers.add_parser("slice", help="Slice video(s) into clips")
    p.add_argument("path", help="Video file or directory")
    p.add_argument("--preset", default="cinematic", help="Config preset")
    p.add_argument("--config", default=None, help="Explicit config file path")
    p.add_argument("--output", default=None, help="Output directory")

    # operations
    subparsers.add_parser("operations", help="List available pipeline operations (JSON)")

    # presets
    subparsers.add_parser("presets", help="List available config presets")

    return parser


def main():
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    setup_logging(verbose=getattr(args, "verbose", False))

    if not args.command:
        parser.print_help()
        sys.exit(0)

    reset_default_collector()

    # Load config
    try:
        if args.command in ("presets", "operations"):
            config = {}
        elif hasattr(args, "config") and args.config:
            config = load_config_file(args.config)
        else:
            preset = getattr(args, "preset", "cinematic")
            config = load_preset(preset)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Dispatch
    commands = {
        "pipeline": cmd_pipeline,
        "downscale": cmd_downscale,
        "analyze": cmd_analyze,
        "slice": cmd_slice,
        "operations": cmd_operations,
        "presets": cmd_presets,
    }

    cmd_func = commands.get(args.command)
    if not cmd_func:
        parser.print_help()
        sys.exit(1)

    try:
        cmd_func(args, config)
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
        collector = get_default_collector()
        if collector.records:
            logger.debug(collector.report_table())


if __name__ == "__main__":
    main()
