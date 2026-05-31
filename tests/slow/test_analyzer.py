"""
tests/slow/test_analyzer.py — Tests for motion scoring and window detection (requires sample.MP4).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import json
import pytest
import numpy as np

from motion_assessment.analyzer import compute_motion_scores, detect_stable_windows
from utils.config_loader import load_preset

SAMPLE_VIDEO = os.path.join(os.path.dirname(__file__), "..", "sample.mp4")
REFERENCE_PATH = os.path.join(os.path.dirname(__file__), "reference_sample.json")


@pytest.fixture
def config():
    return load_preset("cinematic")


@pytest.fixture
def reference():
    with open(REFERENCE_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def motion_result():
    config = load_preset("cinematic")
    return compute_motion_scores(SAMPLE_VIDEO, config)


class TestComputeMotionScores:
    def test_returns_required_keys(self, motion_result):
        for key in ("motion_scores", "raw_scores", "motion_stats", "video_info", "processing"):
            assert key in motion_result

    def test_frame_count(self, motion_result, reference):
        assert motion_result["processing"]["frames_analyzed"] == reference["processing"]["frames_analyzed"]

    def test_stats_mean_close(self, motion_result, reference):
        assert abs(motion_result["motion_stats"]["mean"] - reference["motion_stats"]["mean"]) < 0.02

    def test_stats_max_close(self, motion_result, reference):
        assert abs(motion_result["motion_stats"]["max"] - reference["motion_stats"]["max"]) < 0.05

    def test_scores_non_negative(self, motion_result):
        assert all(s >= 0 for s in motion_result["motion_scores"])

    def test_smoothed_less_variable(self, motion_result):
        assert np.std(motion_result["motion_scores"]) <= np.std(motion_result["raw_scores"])


class TestDetectStableWindows:
    def test_window_count(self, motion_result, reference, config):
        windows = detect_stable_windows(motion_result["motion_scores"], motion_result["video_info"]["fps"], config)
        assert len(windows) == reference["window_count"]

    def test_window_timing(self, motion_result, reference, config):
        windows = detect_stable_windows(motion_result["motion_scores"], motion_result["video_info"]["fps"], config)
        for actual, expected in zip(windows, reference["windows"]):
            assert abs(actual["start_sec"] - expected["start_sec"]) < 0.5
            assert abs(actual["end_sec"] - expected["end_sec"]) < 0.5

    def test_windows_non_overlapping(self, motion_result, config):
        windows = detect_stable_windows(motion_result["motion_scores"], motion_result["video_info"]["fps"], config)
        for i in range(len(windows) - 1):
            assert windows[i]["end_sec"] <= windows[i + 1]["start_sec"]

    def test_motion_below_threshold(self, motion_result, config):
        windows = detect_stable_windows(motion_result["motion_scores"], motion_result["video_info"]["fps"], config)
        for w in windows:
            assert w["avg_motion"] < config["window_detection"]["motion_threshold"]

    def test_zero_threshold_no_windows(self, motion_result, config):
        cfg = {"window_detection": {"motion_threshold": 0.0, "min_duration_sec": 3.0, "merge_gap_sec": 0}}
        assert detect_stable_windows(motion_result["motion_scores"], 30.0, cfg) == []

    def test_high_threshold_one_window(self, motion_result, config):
        cfg = {"window_detection": {"motion_threshold": 100.0, "min_duration_sec": 3.0, "merge_gap_sec": 1.0}}
        windows = detect_stable_windows(motion_result["motion_scores"], motion_result["video_info"]["fps"], cfg)
        assert len(windows) == 1
        assert windows[0]["duration_sec"] > 18.0

    def test_empty_scores(self, config):
        assert detect_stable_windows([], 30.0, config) == []
