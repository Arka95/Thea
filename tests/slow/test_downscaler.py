"""
tests/slow/test_downscaler.py — Tests for video downscaling (requires sample.MP4).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
import cv2

from downscaler.downscaler import downscale_video, batch_downscale
from utils.video_io import get_video_info

SAMPLE_VIDEO = os.path.join(os.path.dirname(__file__), "..", "sample.mp4")


class TestDownscaleVideo:
    def test_creates_output_file(self, tmp_path):
        out = str(tmp_path / "out.mp4")
        result = downscale_video(SAMPLE_VIDEO, out, max_width=320)
        assert os.path.exists(out)
        assert os.path.getsize(out) > 0

    def test_output_resolution(self, tmp_path):
        out = str(tmp_path / "out.mp4")
        downscale_video(SAMPLE_VIDEO, out, max_width=320)
        info = get_video_info(out)
        assert info["width"] == 320
        assert info["height"] == 180  # 3840x2160 -> 320x180

    def test_preserves_fps(self, tmp_path):
        out = str(tmp_path / "out.mp4")
        downscale_video(SAMPLE_VIDEO, out, max_width=320)
        src = get_video_info(SAMPLE_VIDEO)
        dst = get_video_info(out)
        assert abs(src["fps"] - dst["fps"]) < 0.1

    def test_preserves_frame_count(self, tmp_path):
        out = str(tmp_path / "out.mp4")
        result = downscale_video(SAMPLE_VIDEO, out, max_width=320)
        src = get_video_info(SAMPLE_VIDEO)
        assert result["frames_written"] == src["total_frames"]

    def test_size_reduction(self, tmp_path):
        out = str(tmp_path / "out.mp4")
        result = downscale_video(SAMPLE_VIDEO, out, max_width=320)
        assert result["size_reduction"] > 0.5  # At least 50% smaller

    def test_no_downscale_if_smaller(self, tmp_path):
        # First downscale to 320
        small = str(tmp_path / "small.mp4")
        downscale_video(SAMPLE_VIDEO, small, max_width=320)
        # Then "downscale" to 640 (should be no-op)
        out2 = str(tmp_path / "out2.mp4")
        result = downscale_video(small, out2, max_width=640)
        assert result["output_resolution"] == result["original_resolution"]


class TestBatchDownscale:
    def test_batch_processes_directory(self, tmp_path):
        import shutil
        src_dir = tmp_path / "source"
        src_dir.mkdir()
        shutil.copy2(SAMPLE_VIDEO, src_dir / "sample.mp4")

        sink_dir = str(tmp_path / "sink")
        results = batch_downscale(str(src_dir), sink_dir, max_width=320, workers=1)

        assert len(results) == 1
        assert os.path.exists(os.path.join(sink_dir, "sample.mp4"))
