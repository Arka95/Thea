"""Adapt public video APIs to the shared CLI/MCP argument contract."""

import json
import os
from copy import copy
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

import cropandpan
from sampled_captioner import (
    CaptionContext,
    OpenAICompatibleVisionBackend,
    SampledCaptioner,
)
from tools.catalogue import (
    enrich_locale,
    import_catalogues,
    open_catalogue,
    save_description,
    search_catalogue,
)
from tools.walkdir import build_video, find_video_paths, index_videos
from utils.metrics import track
from utils.settings import get_catalogue_path, resolve_data_dir


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
    """Caption a file or directory and persist descriptions in the shared index."""
    for name in ("sample_count", "frame_width", "frame_height", "columns", "timeout_sec"):
        if getattr(args, name) <= 0:
            raise ValueError(f"{name} must be positive")
    if not args.model.strip():
        raise ValueError("model must not be empty")
    if Path(args.path).is_dir():
        if args.contact_sheet or args.sampling_video:
            raise ValueError("Directory captioning cannot use one contact sheet or sampling video.")
        scan_errors = []
        paths = sorted(
            find_video_paths(
                args.path,
                on_error=lambda path, error: scan_errors.append(
                    {"path": path, "error_type": type(error).__name__, "stage": "scan"}
                ),
            )
        )
        if not paths:
            raise ValueError("No videos found for captioning.")
        results, errors = [], scan_errors
        for path in paths:
            child = copy(args)
            child.path = path
            try:
                results.append(_caption_file(child))
            except Exception as error:  # noqa: BLE001 - isolate failures within the batch
                errors.append({"path": path, "error_type": type(error).__name__})
        return {
            "db": get_catalogue_path(),
            "selected": len(paths),
            "saved": len(results),
            "complete": not errors,
            "results": results,
            "errors": errors,
        }
    return _caption_file(args)


@track()
def _caption_file(args):
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
    source_stat = os.stat(args.path)
    with open_catalogue() as store:
        video = build_video(args.path, store=store)
    if video is None:
        raise OSError("Cannot read video identity for caption persistence.")
    video = enrich_locale(video)
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
        keep_contact_sheet=bool(args.contact_sheet),
        context=CaptionContext(
            location_in_metadata=args.location_in_metadata,
            timestamp_in_metadata=args.timestamp_in_metadata or bool(video.creation_time),
            additional_context=args.context,
            country=video.country,
            state=video.state,
        ),
    )
    current = os.stat(args.path)
    if (current.st_size, current.st_mtime_ns) != (source_stat.st_size, source_stat.st_mtime_ns):
        raise ValueError("Source video changed during captioning; description was not saved.")
    return {
        **asdict(result),
        **save_description(video, result.caption),
        "locale": {
            "country": video.country,
            "state": video.state,
        },
    }


def cmd_index(args, config):
    """Index ROOT, optionally persisting metadata in DB; return counts and samples."""
    return index_videos(
        root=args.root,
        limit=args.limit,
        probe=args.probe,
        geocode=args.geocode,
        infer_loc=args.infer_loc,
        report_path=args.report_path,
    )


def cmd_importindex(args, config):
    """Merge source catalogues into the configured video-index.sqlite3."""
    return import_catalogues(args.paths)


def cmd_search(args, config):
    """Return bounded ranked video results from the configured catalogue."""
    return search_catalogue(args.query, args.limit)


def print_result(result):
    """Write a new command's JSON result to the interactive CLI."""
    print(json.dumps(result, indent=2))
