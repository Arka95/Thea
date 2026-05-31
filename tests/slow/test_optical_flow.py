"""
tests/slow/test_optical_flow.py — Tests for optical flow computation (requires GPU + sample.MP4).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import json
import numpy as np
import pytest
import cv2

from motion_assessment.optical_flow import FarnebackGPU, FarnebackCPU, create_flow_calculator
from utils.config_loader import load_preset

SAMPLE_VIDEO = os.path.join(os.path.dirname(__file__), "..", "sample.mp4")


@pytest.fixture
def config():
    return load_preset("cinematic")


@pytest.fixture
def sample_frames():
    cap = cv2.VideoCapture(SAMPLE_VIDEO)
    ret, f1 = cap.read()
    ret, f2 = cap.read()
    cap.release()
    g1 = cv2.resize(cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY), (320, 180))
    g2 = cv2.resize(cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY), (320, 180))
    return g1, g2


class TestFlowCalculator:
    def test_gpu_created_when_available(self, config):
        calc = create_flow_calculator(config)
        assert isinstance(calc, FarnebackGPU)
        assert calc.backend == "cuda"

    def test_cpu_when_gpu_disabled(self, config):
        config["gpu"]["enabled"] = False
        calc = create_flow_calculator(config)
        assert isinstance(calc, FarnebackCPU)

    def test_compute_returns_score_and_meta(self, config, sample_frames):
        calc = create_flow_calculator(config)
        score, meta = calc.compute(*sample_frames)
        assert isinstance(score, float)
        assert score >= 0
        assert "motion_score" in meta
        assert "compute_ms" in meta

    def test_stats_accumulate(self, config, sample_frames):
        calc = create_flow_calculator(config)
        calc.compute(*sample_frames)
        calc.compute(*sample_frames)
        assert calc.stats["calls"] == 2
        assert calc.stats["total_time_sec"] > 0

    def test_zero_motion_on_identical_frames(self, config):
        gray = np.random.randint(0, 255, (180, 320), dtype=np.uint8)
        calc = create_flow_calculator(config)
        score, _ = calc.compute(gray, gray)
        assert score < 0.01

    def test_gpu_cpu_similar_results(self, config, sample_frames):
        if cv2.cuda.getCudaEnabledDeviceCount() == 0:
            pytest.skip("No GPU")
        calc_gpu = create_flow_calculator(config)
        config["gpu"]["enabled"] = False
        calc_cpu = create_flow_calculator(config)

        score_gpu, _ = calc_gpu.compute(*sample_frames)
        score_cpu, _ = calc_cpu.compute(*sample_frames)

        if score_gpu > 0.01:
            assert abs(score_gpu - score_cpu) / score_gpu < 0.10
