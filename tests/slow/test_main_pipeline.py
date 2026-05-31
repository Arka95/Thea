"""
tests/slow/test_main_pipeline.py — Integration test for the full CLI pipeline.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import json
import pytest

SAMPLE_VIDEO = os.path.join(os.path.dirname(__file__), "..", "sample.mp4")


class TestPipelineIntegration:
    def test_full_pipeline(self, tmp_path):
        """Run pipeline and verify outputs."""
        from motion_assessment.analyzer import compute_motion_scores, detect_stable_windows
        from slicer.slicer import slice_video
        from utils.config_loader import load_preset

        config = load_preset("cinematic")
        result = compute_motion_scores(SAMPLE_VIDEO, config)
        windows = detect_stable_windows(result["motion_scores"], result["video_info"]["fps"], config)

        assert len(windows) == 3
        assert result["video_info"]["width"] == 640

        out_dir = str(tmp_path / "clips")
        files = slice_video(SAMPLE_VIDEO, windows, config, output_dir=out_dir)
        assert len(files) == 3

    def test_preset_affects_results(self):
        """Different presets should give different window counts."""
        from motion_assessment.analyzer import compute_motion_scores, detect_stable_windows
        from utils.config_loader import load_preset

        config_strict = load_preset("strict")
        config_action = load_preset("action")

        result = compute_motion_scores(SAMPLE_VIDEO, config_strict)
        windows_strict = detect_stable_windows(result["motion_scores"], result["video_info"]["fps"], config_strict)

        result2 = compute_motion_scores(SAMPLE_VIDEO, config_action)
        windows_action = detect_stable_windows(result2["motion_scores"], result2["video_info"]["fps"], config_action)

        # Action should be more permissive (more/longer windows)
        strict_total = sum(w["duration_sec"] for w in windows_strict)
        action_total = sum(w["duration_sec"] for w in windows_action)
        assert action_total >= strict_total
