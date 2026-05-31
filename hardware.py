"""
hardware.py — Hardware detection and parallelization configuration.

Detects available CPU cores, GPU capabilities, and memory to determine
optimal parallelization settings for batch video processing.
"""

import os
import sys
import logging
from dataclasses import dataclass, field
from typing import Optional

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

    # Computed recommendations
    recommended_workers: int = 1
    recommended_batch_size: int = 1
    gpu_decode_available: bool = False

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
        lines.append(f"Recommended batch size: {self.recommended_batch_size}")
        return "\n".join(lines)


def detect_hardware() -> HardwareProfile:
    """Detect system hardware and compute parallelization recommendations.

    Strategy:
      - GPU optical flow is the bottleneck per video (single GPU stream)
      - CPU cores handle video decode, resize, I/O
      - Multiple videos can be processed in parallel if GPU has enough VRAM
      - Each 320px analysis stream uses ~50-100MB VRAM

    Returns:
        HardwareProfile with detected specs and recommendations
    """
    profile = HardwareProfile()
    profile.platform = sys.platform

    # CPU detection
    profile.cpu_cores_logical = os.cpu_count() or 1
    profile.cpu_cores_physical = _get_physical_cores()

    # RAM detection
    profile.ram_total_mb, profile.ram_available_mb = _get_ram_info()

    # GPU detection
    profile.gpu = _detect_gpu()

    # Compute recommendations
    profile.recommended_workers = _compute_workers(profile)
    profile.recommended_batch_size = _compute_batch_size(profile)

    return profile


def _get_physical_cores() -> int:
    """Get physical CPU core count."""
    try:
        import multiprocessing
        # On Windows, os.cpu_count() returns logical. Try psutil if available.
        try:
            import psutil
            return psutil.cpu_count(logical=False) or os.cpu_count() or 1
        except ImportError:
            # Estimate: most modern CPUs have 2 threads per core
            logical = os.cpu_count() or 1
            return max(1, logical // 2)
    except Exception:
        return 1


def _get_ram_info() -> tuple:
    """Get (total_mb, available_mb)."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return int(mem.total / (1024 * 1024)), int(mem.available / (1024 * 1024))
    except ImportError:
        # Fallback for Windows without psutil
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                mem_status = ctypes.c_ulonglong()
                kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(mem_status))
                total_mb = int(mem_status.value / 1024)
                return total_mb, total_mb // 2  # Estimate 50% available
            except Exception:
                pass
        return 0, 0


def _detect_gpu() -> GPUInfo:
    """Detect NVIDIA GPU via OpenCV CUDA."""
    info = GPUInfo()
    try:
        count = cv2.cuda.getCudaEnabledDeviceCount()
        if count > 0:
            info.available = True
            info.device_count = count
            info.device_id = 0
            cv2.cuda.setDevice(0)

            # Get device properties via printCudaDeviceInfo (parsed from string)
            # OpenCV doesn't expose individual properties easily, so we use what's available
            device_info = cv2.cuda.getDevice()
            info.name = f"CUDA Device {device_info}"

            # Try to get name from build info
            build_info = cv2.getBuildInformation()
            for line in build_info.split("\n"):
                if "NVIDIA" in line and "Device" in line:
                    info.name = line.strip()
                    break

            # Estimate VRAM from device (not directly available in OpenCV Python)
            # Default conservative estimate for RTX 40-series: 8-16 GB
            info.vram_mb = 8192  # Conservative default
    except Exception:
        pass
    return info


def _compute_workers(profile: HardwareProfile) -> int:
    """Determine optimal number of parallel video workers.

    Logic:
      - If GPU available: GPU is the bottleneck. Can process 1-2 videos at a time
        on the GPU depending on VRAM (each stream ~100MB at 320px).
        Additional workers handle CPU-bound decode/resize.
      - If CPU only: limited by physical cores. Each video uses 1 core for flow + 1 for decode.
      - Always leave 1-2 cores for OS and I/O.
      - Cap at available RAM / ~500MB per worker (video buffers).
    """
    if profile.gpu.available:
        # GPU path: 2-4 concurrent streams typically fit in VRAM
        # But each also needs CPU for decode, so factor that in
        gpu_streams = min(4, max(1, profile.gpu.vram_mb // 2048))
        cpu_cap = max(1, profile.cpu_cores_physical - 2)
        workers = min(gpu_streams, cpu_cap)
    else:
        # CPU path: each video saturates ~2 cores (flow + decode)
        workers = max(1, (profile.cpu_cores_physical - 2) // 2)

    # RAM cap: ~500MB per worker for video buffers
    if profile.ram_available_mb > 0:
        ram_cap = max(1, profile.ram_available_mb // 500)
        workers = min(workers, ram_cap)

    return max(1, min(workers, 8))  # Hard cap at 8


def _compute_batch_size(profile: HardwareProfile) -> int:
    """How many videos to queue per batch (for progress reporting)."""
    return max(10, profile.recommended_workers * 5)
