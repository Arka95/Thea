"""Adapt public video APIs to the shared CLI/MCP argument contract."""

import json
import os
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

import cropandpan
from sampled_captioner import (
    CaptionContext,
    OpenAICompatibleVisionBackend,
    SampledCaptioner,
)
from tools.walkdir import index_videos
from utils.settings import resolve_data_dir


def cmd_crop(args, config):
    """Crop PATH to WIDTH x HEIGHT at top-left X,Y; return the output path."""
    output = cropandpan.crop(
        args.path, args.width, args.height, args.x, args.y, output_path=args.output_path
    )
    return {"output": output}


def cmd_centercrop(args, config):
    """Center-crop PATH to WIDTH x HEIGHT; return the output path."""
    output = cropandpan.centercrop(args.path, args.width, args.height, output_path=args.output_path)
    return {"output": output}


def cmd_ratiocrop(args, config):
    """Center-crop PATH to the largest exact RATIOX:RATIOY rectangle."""
    output = cropandpan.ratiocrop(args.path, args.ratiox, args.ratioy, output_path=args.output_path)
    return {"output": output}


def cmd_pan(args, config):
    """Pan PATH; defaults to a 9:16 crop over the full original duration."""
    output = cropandpan.pan(
        args.path,
        resolutionx=args.resolutionx,
        resolutiony=args.resolutiony,
        startx=args.startx,
        starty=args.starty,
        endx=args.endx,
        endy=args.endy,
        duration=args.duration,
        ratiox=args.ratiox,
        ratioy=args.ratioy,
        output_path=args.output_path,
    )
    return {"output": output}


def cmd_caption(args, config):
    """Sample PATH and caption it using an explicitly selected vision model."""
    for name in ("sample_count", "frame_width", "frame_height", "columns", "timeout_sec"):
        if getattr(args, name) <= 0:
            raise ValueError(f"{name} must be positive")
    if not args.model.strip():
        raise ValueError("model must not be empty")
    for path in (args.path, args.sampling_video):
        if path is not None and not Path(path).is_file():
            raise FileNotFoundError(f"Video not found: {path}")
    if args.contact_sheet:
        sheet = Path(args.contact_sheet).expanduser().resolve()
    else:
        folder = Path(resolve_data_dir(args.path)) / "captions"
        sheet = folder / f"{Path(args.path).stem}_{uuid4().hex}.jpg"
    if sheet.exists():
        raise FileExistsError(f"Contact sheet already exists: {sheet}")
    if sheet.suffix.lower() not in {".jpg", ".jpeg"}:
        raise ValueError("contact_sheet must have a .jpg or .jpeg extension")
    backend = OpenAICompatibleVisionBackend(
        model=args.model,
        base_url=args.base_url,
        api_key=os.environ.get(args.api_key_env),
        timeout_sec=args.timeout_sec,
    )
    captioner = SampledCaptioner(
        backend,
        sample_count=args.sample_count,
        frame_width=args.frame_width,
        frame_height=args.frame_height,
        columns=args.columns,
    )
    result = captioner.caption_video(
        source_video_path=args.path,
        contact_sheet_path=str(sheet),
        sampling_video_path=args.sampling_video,
        context=CaptionContext(
            location_in_metadata=args.location_in_metadata,
            timestamp_in_metadata=args.timestamp_in_metadata,
            additional_context=args.context,
        ),
    )
    return asdict(result)


def cmd_index(args, config):
    """Index ROOT, optionally persisting metadata in DB; return counts and samples."""
    return index_videos(
        root=args.root,
        limit=args.limit,
        db=args.db,
        probe=args.probe,
        geocode=args.geocode,
        infer_loc=args.infer_loc,
    )


def print_result(result):
    """Write a new command's JSON result to the interactive CLI."""
    print(json.dumps(result, indent=2))
