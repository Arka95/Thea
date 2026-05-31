"""
test_optical_flow.py — Tests for optical flow computation module.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import numpy as np
import pytest
import cv2

from optical_flow import (
    FlowCalculator,
    FarnebackGPU,
    FarnebackCPU,
    create_flow_calculator,
)


@pytest.fixture
def config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    with open(config_path) as f:
        return json.load(f)


@pytest.fixture
def sample_frames():
    """Load two consecutive grayscale frames from sample video."""
    video_path = os.path.join(os.path.dirname(__file__), "..", "sample.MP4")
    cap = cv2.VideoCapture(video_path)
    assert cap.isOpened(), "Cannot open sample.MP4"

    ret, frame1 = cap.read()
    assert ret
    ret, frame2 = cap.read()
    assert ret
    cap.release()

    # Resize to analysis resolution
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    gray1 = cv2.resize(gray1, (320, 180))
    gray2 = cv2.resize(gray2, (320, 180))
    return gray1, gray2


class TestCreateFlowCalculator:
    """Test the factory function."""

    def test_creates_gpu_calculator_when_available(self, config):
        calc = create_flow_calculator(config)
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            assert isinstance(calc, FarnebackGPU)
            assert calc.backend == "cuda"
        else:
            assert isinstance(calc, FarnebackCPU)
            assert calc.backend == "cpu"

    def test_creates_cpu_calculator_when_gpu_disabled(self, config):
        config["gpu"]["enabled"] = False
        calc = create_flow_calculator(config)
        assert isinstance(calc, FarnebackCPU)
        assert calc.backend == "cpu"

    def test_raises_on_unsupported_algorithm(self, config):
        config["optical_flow"]["algorithm"] = "raft"
        with pytest.raises(ValueError, match="Unsupported"):
            create_flow_calculator(config)


class TestFlowComputation:
    """Test actual flow computation on sample frames."""

    def test_compute_returns_tuple(self, config, sample_frames):
        calc = create_flow_calculator(config)
        prev_gray, gray = sample_frames
        result = calc.compute(prev_gray, gray)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_motion_score_is_float(self, config, sample_frames):
        calc = create_flow_calculator(config)
        score, meta = calc.compute(*sample_frames)
        assert isinstance(score, float)
        assert score >= 0.0

    def test_frame_meta_has_required_keys(self, config, sample_frames):
        calc = create_flow_calculator(config)
        _, meta = calc.compute(*sample_frames)
        assert "motion_score" in meta
        assert "max_magnitude" in meta
        assert "mean_angle_deg" in meta
        assert "compute_ms" in meta

    def test_motion_score_matches_meta(self, config, sample_frames):
        calc = create_flow_calculator(config)
        score, meta = calc.compute(*sample_frames)
        assert abs(score - meta["motion_score"]) < 0.001

    def test_stats_update_after_compute(self, config, sample_frames):
        calc = create_flow_calculator(config)
        assert calc.stats["calls"] == 0
        calc.compute(*sample_frames)
        assert calc.stats["calls"] == 1
        assert calc.stats["total_time_sec"] > 0
        calc.compute(*sample_frames)
        assert calc.stats["calls"] == 2

    def test_reuse_calculator_across_frames(self, config):
        """Calculator should be reusable (not recreated per frame)."""
        video_path = os.path.join(os.path.dirname(__file__), "..", "sample.MP4")
        cap = cv2.VideoCapture(video_path)
        calc = create_flow_calculator(config)

        ret, frame = cap.read()
        prev_gray = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (320, 180))

        scores = []
        for _ in range(10):
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (320, 180))
            score, _ = calc.compute(prev_gray, gray)
            scores.append(score)
            prev_gray = gray

        cap.release()
        assert len(scores) == 10
        assert calc.stats["calls"] == 10
        # First frames of sample are very stable (near-static)
        assert all(s < 0.5 for s in scores[:5])

    def test_gpu_cpu_produce_similar_results(self, config, sample_frames):
        """GPU and CPU should produce reasonably close results."""
        if cv2.cuda.getCudaEnabledDeviceCount() == 0:
            pytest.skip("No GPU available for comparison")

        config_gpu = json.loads(json.dumps(config))
        config_cpu = json.loads(json.dumps(config))
        config_cpu["gpu"]["enabled"] = False

        calc_gpu = create_flow_calculator(config_gpu)
        calc_cpu = create_flow_calculator(config_cpu)

        score_gpu, _ = calc_gpu.compute(*sample_frames)
        score_cpu, _ = calc_cpu.compute(*sample_frames)

        # Should be within 10% of each other (minor numerical differences)
        if score_gpu > 0.01:
            ratio = abs(score_gpu - score_cpu) / score_gpu
            assert ratio < 0.10, f"GPU={score_gpu:.4f}, CPU={score_cpu:.4f}, diff={ratio*100:.1f}%"


class TestFlowWithStaticImage:
    """Test with identical frames (zero motion)."""

    def test_zero_motion_on_identical_frames(self, config):
        gray = np.random.randint(0, 255, (180, 320), dtype=np.uint8)
        calc = create_flow_calculator(config)
        score, meta = calc.compute(gray, gray)
        assert score < 0.01, f"Expected near-zero motion on identical frames, got {score}"
