"""
tests/slow/test_slicer.py — Tests for video slicing (requires sample.MP4).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from slicer.slicer import slice_video
from utils.config_loader import load_preset


SAMPLE_VIDEO = os.path.join(os.path.dirname(__file__), "..", "sample.mp4")


@pytest.fixture
def config():
    return load_preset("cinematic")


@pytest.fixture
def windows():
    return [
        {"start_sec": 0.0, "end_sec": 6.2, "duration_sec": 6.2, "avg_motion": 0.17, "max_motion": 0.49, "frame_range": [0, 186]},
        {"start_sec": 8.6, "end_sec": 12.1, "duration_sec": 3.5, "avg_motion": 0.28, "max_motion": 0.50, "frame_range": [257, 362]},
        {"start_sec": 14.7, "end_sec": 19.1, "duration_sec": 4.4, "avg_motion": 0.23, "max_motion": 0.48, "frame_range": [442, 573]},
    ]


class TestSliceVideo:
    def test_creates_correct_number_of_clips(self, config, windows, tmp_path):
        out_dir = str(tmp_path / "sliced")
        files = slice_video(SAMPLE_VIDEO, windows, config, output_dir=out_dir)
        assert len(files) == 3
        for f in files:
            assert os.path.exists(f)
            assert os.path.getsize(f) > 0

    def test_empty_windows_no_output(self, config):
        files = slice_video(SAMPLE_VIDEO, [], config)
        assert files == []

    def test_clip_naming(self, config, windows, tmp_path):
        out_dir = str(tmp_path / "sliced")
        files = slice_video(SAMPLE_VIDEO, windows, config, output_dir=out_dir)
        basenames = [os.path.basename(f) for f in files]
        assert "sample_1.mp4" in basenames
        assert "sample_2.mp4" in basenames
        assert "sample_3.mp4" in basenames
