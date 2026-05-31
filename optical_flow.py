"""
optical_flow.py — Optical flow computation with GPU/CPU fallback.

Provides a factory function that returns a reusable flow calculator
based on the selected algorithm and hardware availability.
"""

import cv2
import numpy as np
import time


class FlowCalculator:
    """Base interface for optical flow computation."""

    def __init__(self, config: dict):
        self.config = config
        self._call_count = 0
        self._total_time = 0.0

    def compute(self, prev_gray: np.ndarray, gray: np.ndarray) -> tuple:
        """Compute motion score and per-frame metadata.

        Returns:
            (motion_score: float, frame_meta: dict)
        """
        raise NotImplementedError

    @property
    def stats(self) -> dict:
        return {
            "calls": self._call_count,
            "total_time_sec": round(self._total_time, 4),
            "avg_time_ms": round((self._total_time / max(self._call_count, 1)) * 1000, 2),
        }


class FarnebackGPU(FlowCalculator):
    """GPU-accelerated Farneback dense optical flow."""

    def __init__(self, config: dict):
        super().__init__(config)
        fb = config["optical_flow"]["farneback"]
        self._flow_algo = cv2.cuda.FarnebackOpticalFlow.create(
            numLevels=fb["levels"],
            pyrScale=fb["pyr_scale"],
            fastPyramids=False,
            winSize=fb["winsize"],
            numIters=fb["iterations"],
            polyN=fb["poly_n"],
            polySigma=fb["poly_sigma"],
            flags=fb["flags"],
        )
        self._gpu_prev = cv2.cuda_GpuMat()
        self._gpu_curr = cv2.cuda_GpuMat()
        self.backend = "cuda"

    def compute(self, prev_gray: np.ndarray, gray: np.ndarray) -> tuple:
        t0 = time.perf_counter()

        self._gpu_prev.upload(prev_gray)
        self._gpu_curr.upload(gray)
        flow_gpu = self._flow_algo.calc(self._gpu_prev, self._gpu_curr, None)
        flow = flow_gpu.download()

        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        motion_score = float(np.mean(magnitude))

        elapsed = time.perf_counter() - t0
        self._call_count += 1
        self._total_time += elapsed

        frame_meta = {
            "motion_score": round(motion_score, 4),
            "max_magnitude": round(float(np.max(magnitude)), 4),
            "mean_angle_deg": round(float(np.mean(angle) * 180 / np.pi), 2),
            "compute_ms": round(elapsed * 1000, 2),
        }
        return motion_score, frame_meta


class FarnebackCPU(FlowCalculator):
    """CPU Farneback dense optical flow (fallback)."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.fb = config["optical_flow"]["farneback"]
        self.backend = "cpu"

    def compute(self, prev_gray: np.ndarray, gray: np.ndarray) -> tuple:
        t0 = time.perf_counter()
        fb = self.fb

        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, gray, None,
            pyr_scale=fb["pyr_scale"],
            levels=fb["levels"],
            winsize=fb["winsize"],
            iterations=fb["iterations"],
            poly_n=fb["poly_n"],
            poly_sigma=fb["poly_sigma"],
            flags=fb["flags"],
        )

        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        motion_score = float(np.mean(magnitude))

        elapsed = time.perf_counter() - t0
        self._call_count += 1
        self._total_time += elapsed

        frame_meta = {
            "motion_score": round(motion_score, 4),
            "max_magnitude": round(float(np.max(magnitude)), 4),
            "mean_angle_deg": round(float(np.mean(angle) * 180 / np.pi), 2),
            "compute_ms": round(elapsed * 1000, 2),
        }
        return motion_score, frame_meta


def create_flow_calculator(config: dict) -> FlowCalculator:
    """Factory: create the appropriate flow calculator based on config and hardware.

    Returns:
        FlowCalculator instance (GPU or CPU)
    """
    algorithm = config["optical_flow"]["algorithm"]
    gpu_enabled = config["gpu"]["enabled"]
    gpu_available = cv2.cuda.getCudaEnabledDeviceCount() > 0

    if algorithm != "farneback":
        raise ValueError(f"Unsupported optical flow algorithm: '{algorithm}'. Supported: farneback")

    if gpu_enabled and gpu_available:
        device_id = config["gpu"].get("device_id", 0)
        cv2.cuda.setDevice(device_id)
        return FarnebackGPU(config)
    else:
        if gpu_enabled and not gpu_available:
            import logging
            logging.warning("GPU requested but no CUDA device found. Falling back to CPU.")
        return FarnebackCPU(config)
