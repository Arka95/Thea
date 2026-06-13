"""Analyze pipeline operation."""

from __future__ import annotations

from pathlib import Path

from motion_assessment.analyzer import compute_motion_scores, detect_stable_windows
from thea.operations import Operation, register


class AnalyzeOperation(Operation):
    name = "analyze"
    description = "Compute motion scores and detect stable windows."
    requires = ["analysis_video_path"]
    provides = ["motion_scores", "stable_windows", "motion_stats"]

    def execute(self, context, config: dict):
        video_path = context.analysis_video_path or context.current_video_path or context.source_path
        result = compute_motion_scores(str(video_path), config)
        windows = detect_stable_windows(result["motion_scores"], result["video_info"]["fps"], config)

        context.analysis_video_path = Path(video_path)
        context.motion_scores = result["motion_scores"]
        context.motion_stats = result["motion_stats"]
        context.stable_windows = windows
        return context


register(AnalyzeOperation())
