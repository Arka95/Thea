"""
src/utils/tests/test_hardware.py — Unit tests for hardware detection.
"""

import pytest

from utils import hardware
from utils.hardware import GPUInfo, HardwareProfile, detect_hardware


@pytest.fixture(autouse=True)
def fake_hardware(monkeypatch):
    monkeypatch.setattr(hardware.os, "cpu_count", lambda: 16)
    monkeypatch.setattr(hardware, "_get_physical_cores", lambda: 8)
    monkeypatch.setattr(hardware, "_get_ram_info", lambda: (32768, 16384))
    monkeypatch.setattr(
        hardware,
        "_detect_gpu",
        lambda: GPUInfo(available=True, device_count=1, name="Test GPU", vram_mb=8192),
    )


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

    def test_cpu_only_profile(self, monkeypatch):
        monkeypatch.setattr(hardware, "_detect_gpu", GPUInfo)
        hw = detect_hardware()
        assert hw.gpu.available is False
        assert hw.recommended_workers == 3
