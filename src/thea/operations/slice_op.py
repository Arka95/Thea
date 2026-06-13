"""Slice pipeline operation."""

from __future__ import annotations

from pathlib import Path

from slicer.slicer import slice_video
from thea.operations import Operation, register
from utils.settings import get_sliced_dir


class SliceOperation(Operation):
    name = "slice"
    description = "Slice the source video into clips using stable windows."
    requires = ["stable_windows"]
    provides = ["clips"]

    def execute(self, context, config: dict):
        if context.data_dir is None:
            raise ValueError("PipelineContext.data_dir is required for slice operation")

        output_dir = get_sliced_dir(str(context.data_dir))
        files = slice_video(
            str(context.source_path),
            context.stable_windows or [],
            config,
            output_dir=output_dir,
        )

        context.clips = [Path(path) for path in files]
        return context


register(SliceOperation())
