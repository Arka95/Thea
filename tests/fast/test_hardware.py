"""
tests/fast/test_hardware.py — Unit tests for hardware detection.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from utils.hardware import detect_hardware, HardwareProfile, GPUInfo


class TestDetectHardware:
    def test_returns_profile(self):
        hw = detect_hardware()
        assert isinstance(hw, HardwareProfile)

    def test_cpu_cores_positive(self):
        hw = detect_hardware()
        assert hw.cpu_cores_physical >= 1
        assert hw.cpu_cores_logical >= hw.cpu_cores_physical

    def test_recommended_workers_bounded(self):
        hw = detect_hardware()
        assert 1 <= hw.recommended_workers <= 8

    def test_gpu_detected(self):
        hw = detect_hardware()
        assert hw.gpu.available is True
        assert hw.gpu.device_count >= 1

    def test_summary_readable(self):
        hw = detect_hardware()
        s = hw.summary()
        assert "CPU" in s
        assert "GPU" in s
