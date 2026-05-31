"""
test_video_processing.py — Tests for video I/O, motion scoring, and window detection.

Uses reference data from tests/reference_sample.json generated from sample.MP4.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
import numpy as np

from video_processing import (
    get_video_info,
    compute_motion_scores,
    detect_stable_windows,
    slice_video,
)


@pytest.fixture
def config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    with open(config_path) as f:
        return json.load(f)


@pytest.fixture
def reference():
    ref_path = os.path.join(os.path.dirname(__file__), "reference_sample.json")
    with open(ref_path) as f:
        return json.load(f)


@pytest.fixture
def sample_video():
    return os.path.join(os.path.dirname(__file__), "..", "sample.MP4")


@pytest.fixture
def motion_result(sample_video, config):
    """Compute motion scores (cached for test session via fixture)."""
    return compute_motion_scores(sample_video, config)


class TestGetVideoInfo:
    """Test video metadata extraction."""

    def test_returns_dict(self, sample_video):
        info = get_video_info(sample_video)
        assert isinstance(info, dict)

    def test_resolution(self, sample_video, reference):
        info = get_video_info(sample_video)
        assert info["width"] == reference["video_info"]["width"]
        assert info["height"] == reference["video_info"]["height"]

    def test_fps(self, sample_video, reference):
        info = get_video_info(sample_video)
        assert abs(info["fps"] - reference["video_info"]["fps"]) < 0.01

    def test_frame_count(self, sample_video, reference):
        info = get_video_info(sample_video)
        assert info["total_frames"] == reference["video_info"]["total_frames"]

    def test_duration(self, sample_video, reference):
        info = get_video_info(sample_video)
        assert abs(info["duration_sec"] - reference["video_info"]["duration_sec"]) < 0.1

    def test_codec(self, sample_video):
        info = get_video_info(sample_video)
        assert info["codec"] == "h264"

    def test_invalid_path_raises(self):
        with pytest.raises(ValueError):
            get_video_info("nonexistent_video.mp4")


class TestComputeMotionScores:
    """Test motion score computation against reference values."""

    def test_returns_required_keys(self, motion_result):
        assert "motion_scores" in motion_result
        assert "raw_scores" in motion_result
        assert "motion_stats" in motion_result
        assert "video_info" in motion_result
        assert "processing" in motion_result
        assert "flow_calculator_stats" in motion_result

    def test_frame_count_matches(self, motion_result, reference):
        assert motion_result["processing"]["frames_analyzed"] == reference["processing"]["frames_analyzed"]

    def test_motion_scores_length(self, motion_result, reference):
        expected_frames = reference["processing"]["frames_analyzed"]
        assert len(motion_result["motion_scores"]) == expected_frames
        assert len(motion_result["raw_scores"]) == expected_frames

    def test_motion_stats_mean(self, motion_result, reference):
        """Mean motion should be very close to reference (deterministic algorithm)."""
        assert abs(motion_result["motion_stats"]["mean"] - reference["motion_stats"]["mean"]) < 0.02

    def test_motion_stats_max(self, motion_result, reference):
        assert abs(motion_result["motion_stats"]["max"] - reference["motion_stats"]["max"]) < 0.05

    def test_motion_stats_min(self, motion_result, reference):
        assert abs(motion_result["motion_stats"]["min"] - reference["motion_stats"]["min"]) < 0.01

    def test_motion_stats_median(self, motion_result, reference):
        assert abs(motion_result["motion_stats"]["median"] - reference["motion_stats"]["median"]) < 0.02

    def test_algorithm_used(self, motion_result, reference):
        assert motion_result["processing"]["algorithm"] == reference["processing"]["algorithm"]

    def test_analysis_resolution(self, motion_result, reference):
        assert motion_result["processing"]["analysis_resolution"] == reference["processing"]["analysis_resolution"]

    def test_scores_are_non_negative(self, motion_result):
        assert all(s >= 0 for s in motion_result["motion_scores"])
        assert all(s >= 0 for s in motion_result["raw_scores"])

    def test_smoothed_less_variable_than_raw(self, motion_result):
        """Smoothed scores should have lower std than raw."""
        raw_std = np.std(motion_result["raw_scores"])
        smooth_std = np.std(motion_result["motion_scores"])
        assert smooth_std <= raw_std


class TestDetectStableWindows:
    """Test stable window detection logic."""

    def test_window_count_matches_reference(self, motion_result, reference, config):
        windows = detect_stable_windows(
            motion_result["motion_scores"],
            motion_result["video_info"]["fps"],
            config,
        )
        assert len(windows) == reference["window_count"]

    def test_window_structure(self, motion_result, config):
        windows = detect_stable_windows(
            motion_result["motion_scores"],
            motion_result["video_info"]["fps"],
            config,
        )
        for w in windows:
            assert "start_sec" in w
            assert "end_sec" in w
            assert "duration_sec" in w
            assert "avg_motion" in w
            assert "max_motion" in w
            assert "frame_range" in w

    def test_window_timing_close_to_reference(self, motion_result, reference, config):
        """Window start/end times should be within 0.5s of reference."""
        windows = detect_stable_windows(
            motion_result["motion_scores"],
            motion_result["video_info"]["fps"],
            config,
        )
        for actual, expected in zip(windows, reference["windows"]):
            assert abs(actual["start_sec"] - expected["start_sec"]) < 0.5
            assert abs(actual["end_sec"] - expected["end_sec"]) < 0.5
            assert abs(actual["duration_sec"] - expected["duration_sec"]) < 1.0

    def test_windows_dont_overlap(self, motion_result, config):
        windows = detect_stable_windows(
            motion_result["motion_scores"],
            motion_result["video_info"]["fps"],
            config,
        )
        for i in range(len(windows) - 1):
            assert windows[i]["end_sec"] <= windows[i + 1]["start_sec"]

    def test_windows_respect_min_duration(self, motion_result, config):
        windows = detect_stable_windows(
            motion_result["motion_scores"],
            motion_result["video_info"]["fps"],
            config,
        )
        min_dur = config["window_detection"]["min_duration_sec"]
        for w in windows:
            assert w["duration_sec"] >= min_dur - 0.1  # small tolerance for frame rounding

    def test_window_motion_below_threshold(self, motion_result, config):
        """Average motion in each window should be below threshold."""
        windows = detect_stable_windows(
            motion_result["motion_scores"],
            motion_result["video_info"]["fps"],
            config,
        )
        threshold = config["window_detection"]["motion_threshold"]
        for w in windows:
            assert w["avg_motion"] < threshold

    def test_total_extractable_matches_reference(self, motion_result, reference, config):
        windows = detect_stable_windows(
            motion_result["motion_scores"],
            motion_result["video_info"]["fps"],
            config,
        )
        total = sum(w["duration_sec"] for w in windows)
        assert abs(total - reference["total_extractable_sec"]) < 1.0

    def test_no_windows_with_zero_threshold(self, motion_result, config):
        """Threshold of 0 should find no stable frames."""
        config_zero = dict(config)
        config_zero["window_detection"] = {"motion_threshold": 0.0, "min_duration_sec": 3.0, "merge_gap_sec": 0.0}
        windows = detect_stable_windows(
            motion_result["motion_scores"],
            motion_result["video_info"]["fps"],
            config_zero,
        )
        assert len(windows) == 0

    def test_one_window_with_high_threshold(self, motion_result, config):
        """Very high threshold should merge everything into one window."""
        config_high = dict(config)
        config_high["window_detection"] = {"motion_threshold": 100.0, "min_duration_sec": 3.0, "merge_gap_sec": 1.0}
        windows = detect_stable_windows(
            motion_result["motion_scores"],
            motion_result["video_info"]["fps"],
            config_high,
        )
        assert len(windows) == 1
        # Should span nearly the entire video
        assert windows[0]["duration_sec"] > 18.0

    def test_merge_gap_combines_nearby_windows(self, motion_result, config):
        """Large merge gap should reduce window count."""
        # Use a threshold that creates multiple raw spans
        config_merge = dict(config)
        config_merge["window_detection"] = {"motion_threshold": 0.5, "min_duration_sec": 1.0, "merge_gap_sec": 0.0}
        windows_no_merge = detect_stable_windows(
            motion_result["motion_scores"],
            motion_result["video_info"]["fps"],
            config_merge,
        )

        config_merge["window_detection"]["merge_gap_sec"] = 5.0
        windows_with_merge = detect_stable_windows(
            motion_result["motion_scores"],
            motion_result["video_info"]["fps"],
            config_merge,
        )

        assert len(windows_with_merge) <= len(windows_no_merge)

    def test_empty_scores_returns_empty(self, config):
        windows = detect_stable_windows([], 30.0, config)
        assert windows == []


class TestSliceVideo:
    """Test video slicing output."""

    def test_slice_creates_files(self, sample_video, motion_result, config, tmp_path):
        """Slicing should create output files."""
        windows = detect_stable_windows(
            motion_result["motion_scores"],
            motion_result["video_info"]["fps"],
            config,
        )
        # Use tmp_path by changing cwd
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            output_files = slice_video(sample_video, windows, config)
            assert len(output_files) == len(windows)
            for f in output_files:
                assert os.path.exists(f)
                assert os.path.getsize(f) > 0
        finally:
            os.chdir(original_cwd)

    def test_slice_empty_windows_returns_empty(self, sample_video, config):
        output_files = slice_video(sample_video, [], config)
        assert output_files == []
