"""
utils/hardware.py — Hardware detection and parallelization configuration.
"""

import os
import sys
import logging
from dataclasses import dataclass, field

import cv2

logger = logging.getLogger("thea")


@dataclass
class GPUInfo:
    available: bool = False
    device_count: int = 0
    device_id: int = 0
    name: str = "N/A"
    compute_capability: str = "N/A"
    vram_mb: int = 0


@dataclass
class HardwareProfile:
    """Detected hardware capabilities for parallelization decisions."""
    cpu_cores_physical: int = 1
    cpu_cores_logical: int = 1
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    gpu: GPUInfo = field(default_factory=GPUInfo)
    platform: str = ""
    recommended_workers: int = 1
    recommended_batch_size: int = 1

    def summary(self) -> str:
        lines = [
            f"CPU: {self.cpu_cores_physical} physical / {self.cpu_cores_logical} logical cores",
            f"RAM: {self.ram_total_mb:,} MB total, {self.ram_available_mb:,} MB available",
            f"GPU: {'YES' if self.gpu.available else 'NO'}",
        ]
        if self.gpu.available:
            lines.append(f"  Device: {self.gpu.name} (compute {self.gpu.compute_capability})")
            lines.append(f"  VRAM: {self.gpu.vram_mb:,} MB")
        lines.append(f"Recommended workers: {self.recommended_workers}")
        return "\n".join(lines)


def detect_hardware() -> HardwareProfile:
    """Detect system hardware and compute parallelization recommendations."""
    profile = HardwareProfile()
    profile.platform = sys.platform
    profile.cpu_cores_logical = os.cpu_count() or 1
    profile.cpu_cores_physical = _get_physical_cores()
    profile.ram_total_mb, profile.ram_available_mb = _get_ram_info()
    profile.gpu = _detect_gpu()
    profile.recommended_workers = _compute_workers(profile)
    profile.recommended_batch_size = max(10, profile.recommended_workers * 5)
    return profile


def _get_physical_cores() -> int:
    try:
        import psutil
        return psutil.cpu_count(logical=False) or os.cpu_count() or 1
    except ImportError:
        logical = os.cpu_count() or 1
        return max(1, logical // 2)


def _get_ram_info() -> tuple:
    try:
        import psutil
        mem = psutil.virtual_memory()
        return int(mem.total / (1024 * 1024)), int(mem.available / (1024 * 1024))
    except ImportError:
        if sys.platform == "win32":
            try:
                import ctypes
                mem_status = ctypes.c_ulonglong()
                ctypes.windll.kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(mem_status))
                total_mb = int(mem_status.value / 1024)
                return total_mb, total_mb // 2
            except Exception:
                pass
        return 0, 0


def _detect_gpu() -> GPUInfo:
    info = GPUInfo()
    try:
        count = cv2.cuda.getCudaEnabledDeviceCount()
        if count > 0:
            info.available = True
            info.device_count = count
            info.device_id = 0
            cv2.cuda.setDevice(0)
            info.name = f"CUDA Device {cv2.cuda.getDevice()}"
            info.vram_mb = 8192  # Conservative default
    except Exception:
        pass
    return info


def _compute_workers(profile: HardwareProfile) -> int:
    if profile.gpu.available:
        gpu_streams = min(4, max(1, profile.gpu.vram_mb // 2048))
        cpu_cap = max(1, profile.cpu_cores_physical - 2)
        workers = min(gpu_streams, cpu_cap)
    else:
        workers = max(1, (profile.cpu_cores_physical - 2) // 2)

    if profile.ram_available_mb > 0:
        ram_cap = max(1, profile.ram_available_mb // 500)
        workers = min(workers, ram_cap)

    return max(1, min(workers, 8))
