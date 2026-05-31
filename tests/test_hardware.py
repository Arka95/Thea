"""
test_hardware.py — Tests for hardware detection module.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from hardware import detect_hardware, HardwareProfile, GPUInfo


class TestDetectHardware:
    """Test hardware detection returns valid profile."""

    def test_returns_profile(self):
        hw = detect_hardware()
        assert isinstance(hw, HardwareProfile)

    def test_cpu_cores_positive(self):
        hw = detect_hardware()
        assert hw.cpu_cores_physical >= 1
        assert hw.cpu_cores_logical >= 1
        assert hw.cpu_cores_logical >= hw.cpu_cores_physical

    def test_platform_detected(self):
        hw = detect_hardware()
        assert hw.platform in ("win32", "linux", "darwin")

    def test_recommended_workers_positive(self):
        hw = detect_hardware()
        assert hw.recommended_workers >= 1
        assert hw.recommended_workers <= 8

    def test_recommended_batch_size_positive(self):
        hw = detect_hardware()
        assert hw.recommended_batch_size >= 10

    def test_gpu_info_structure(self):
        hw = detect_hardware()
        assert isinstance(hw.gpu, GPUInfo)
        assert isinstance(hw.gpu.available, bool)
        assert isinstance(hw.gpu.device_count, int)


class TestHardwareProfileOnThisMachine:
    """Tests specific to the known test machine (RTX 4070 SUPER, 12 cores)."""

    def test_gpu_is_available(self):
        hw = detect_hardware()
        assert hw.gpu.available is True
        assert hw.gpu.device_count >= 1

    def test_multiple_cores(self):
        hw = detect_hardware()
        assert hw.cpu_cores_logical >= 8  # Known: 12 logical

    def test_workers_greater_than_one(self):
        """With GPU + multi-core, should recommend >1 worker."""
        hw = detect_hardware()
        assert hw.recommended_workers >= 2

    def test_summary_readable(self):
        hw = detect_hardware()
        summary = hw.summary()
        assert "CPU" in summary
        assert "RAM" in summary
        assert "GPU" in summary
        assert "YES" in summary  # GPU available
