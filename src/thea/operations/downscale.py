"""Downscale pipeline operation."""

from __future__ import annotations

import logging
from pathlib import Path

from downscaler.downscaler import downscale_video
from thea.operations import Operation, register
from utils.settings import get_downsampled_path

logger = logging.getLogger(__name__)


class DownscaleOperation(Operation):
    name = "downscale"
    description = "Downscale the source video for motion analysis."
    requires = ["source_path"]
    provides = ["analysis_video_path"]

    def execute(self, context, config: dict):
        if context.data_dir is None:
            raise ValueError("PipelineContext.data_dir is required for downscale operation")

        max_width = config["analysis"]["max_width"]
        codec = config["output"]["codec"]
        output_path = Path(get_downsampled_path(str(context.source_path), str(context.data_dir), lossless=False))

        if output_path.exists():
            logger.info(f"Downscaled video exists, skipping: {output_path}")
        else:
            result = downscale_video(
                str(context.source_path),
                str(output_path),
                max_width=max_width,
                codec=codec,
                lossless=False,
            )
            output_path = Path(result["output"])

        context.analysis_video_path = output_path
        return context


register(DownscaleOperation())
