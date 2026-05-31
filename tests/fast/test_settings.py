"""
tests/fast/test_settings.py — Tests for utils/settings.py and utils/pipeline_logger.py
"""

import os
import json
import csv
import tempfile
import pytest
from unittest.mock import patch
from pathlib import Path

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.settings import (
    resolve_data_dir,
    get_downsampled_path,
    get_sliced_dir,
    get_video_meta_path,
    get_pipeline_stats_path,
    DOWNSAMPLED_DIR,
    SLICED_DIR,
    VIDEO_META_CSV,
    PIPELINE_STATS_CSV,
    DATA_ROOT_NAME,
)
from utils.pipeline_logger import (
    log_video_meta,
    log_pipeline_stats,
    _ensure_csv,
    VIDEO_META_HEADERS,
    PIPELINE_STATS_HEADERS,
)


class TestResolveDataDir:
    """Tests for resolve_data_dir path resolution logic."""

    def test_empty_settings_with_directory(self, tmp_path):
        """When data_dir is empty and source is a directory, uses source/Thea/."""
        source_dir = str(tmp_path / "videos")
        os.makedirs(source_dir)

        with patch("utils.settings._load_raw_settings", return_value={"data_dir": ""}):
            result = resolve_data_dir(source_dir)

        assert result == os.path.join(os.path.abspath(source_dir), DATA_ROOT_NAME)
        assert os.path.isdir(result)
        assert os.path.isdir(os.path.join(result, DOWNSAMPLED_DIR))
        assert os.path.isdir(os.path.join(result, SLICED_DIR))

    def test_empty_settings_with_file(self, tmp_path):
        """When data_dir is empty and source is a file, uses file_parent/Thea/."""
        video_file = str(tmp_path / "clip.mp4")
        Path(video_file).touch()

        with patch("utils.settings._load_raw_settings", return_value={"data_dir": ""}):
            result = resolve_data_dir(video_file)

        expected = os.path.join(str(tmp_path), DATA_ROOT_NAME)
        assert result == expected
        assert os.path.isdir(result)

    def test_configured_data_dir_used(self, tmp_path):
        """When data_dir is set in settings, uses that path."""
        custom_dir = str(tmp_path / "custom_data")

        with patch("utils.settings._load_raw_settings", return_value={"data_dir": custom_dir}):
            result = resolve_data_dir("some_video.mp4")

        assert result == os.path.abspath(custom_dir)
        assert os.path.isdir(result)
        assert os.path.isdir(os.path.join(result, DOWNSAMPLED_DIR))
        assert os.path.isdir(os.path.join(result, SLICED_DIR))

    def test_creates_subdirectories(self, tmp_path):
        """Ensures downsampled/ and sliced/ subdirs are created."""
        data_dir = str(tmp_path / "new_data")

        with patch("utils.settings._load_raw_settings", return_value={"data_dir": data_dir}):
            resolve_data_dir("video.mp4")

        assert os.path.isdir(os.path.join(data_dir, DOWNSAMPLED_DIR))
        assert os.path.isdir(os.path.join(data_dir, SLICED_DIR))


class TestGetPaths:
    """Tests for path helper functions."""

    def test_get_downsampled_path_lossy(self):
        data_dir = "/data"
        result = get_downsampled_path("/videos/clip.mp4", data_dir, lossless=False)
        assert result == os.path.join("/data", DOWNSAMPLED_DIR, "clip.mp4")

    def test_get_downsampled_path_lossless(self):
        data_dir = "/data"
        result = get_downsampled_path("/videos/clip.mp4", data_dir, lossless=True)
        assert result == os.path.join("/data", DOWNSAMPLED_DIR, "clip.avi")

    def test_get_sliced_dir(self):
        assert get_sliced_dir("/data") == os.path.join("/data", SLICED_DIR)

    def test_get_video_meta_path(self):
        assert get_video_meta_path("/data") == os.path.join("/data", VIDEO_META_CSV)

    def test_get_pipeline_stats_path(self):
        assert get_pipeline_stats_path("/data") == os.path.join("/data", PIPELINE_STATS_CSV)


class TestEnsureCsv:
    """Tests for CSV header creation logic."""

    def test_creates_file_with_headers(self, tmp_path):
        csv_path = str(tmp_path / "test.csv")
        headers = ["col1", "col2", "col3"]
        _ensure_csv(csv_path, headers)

        assert os.path.exists(csv_path)
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            row = next(reader)
        assert row == headers

    def test_does_not_overwrite_existing(self, tmp_path):
        csv_path = str(tmp_path / "test.csv")
        # Write existing content
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["existing", "data"])
            writer.writerow(["row1", "val1"])

        _ensure_csv(csv_path, ["new", "headers"])

        # Original content should be untouched
        with open(csv_path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 2
        assert "existing" in lines[0]


class TestLogVideoMeta:
    """Tests for video metadata CSV logging."""

    @pytest.fixture(autouse=True)
    def enable_data_collection(self):
        with patch("utils.pipeline_logger.is_data_collection_enabled", return_value=True):
            yield

    def test_creates_and_appends(self, tmp_path):
        data_dir = str(tmp_path)
        result = {
            "video_info": {"width": 640, "height": 360, "fps": 30, "total_frames": 300},
            "motion_stats": {"mean": 0.35, "max": 1.2, "std": 0.3, "min": 0.01, "median": 0.3},
        }
        windows = [{"start_sec": 0.0, "end_sec": 5.0, "duration_sec": 5.0, "avg_motion": 0.2}]
        config = {"analysis": {"max_width": 320}, "optical_flow": {"algorithm": "farneback"}}

        # First call creates file
        log_video_meta(data_dir, "/videos/test.mp4", result, windows, config)
        csv_path = get_video_meta_path(data_dir)
        assert os.path.exists(csv_path)

        with open(csv_path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 2  # header + 1 row

        # Second call appends
        log_video_meta(data_dir, "/videos/test2.mp4", result, windows, config)
        with open(csv_path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 3  # header + 2 rows

    def test_row_content(self, tmp_path):
        data_dir = str(tmp_path)
        result = {
            "video_info": {"width": 1920, "height": 1080, "fps": 24, "total_frames": 480},
            "motion_stats": {"mean": 0.5, "max": 2.0, "std": 0.4, "min": 0.05, "median": 0.4},
        }
        windows = [{"start_sec": 1.0, "end_sec": 6.0, "duration_sec": 5.0, "avg_motion": 0.3}]
        config = {"analysis": {"max_width": 320}, "optical_flow": {"algorithm": "farneback"}}

        log_video_meta(data_dir, "/videos/sample.mp4", result, windows, config)

        csv_path = get_video_meta_path(data_dir)
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            row = next(reader)

        assert row[0] == "sample.mp4"
        assert row[6] == "moderate"  # mean=0.5 at 320px is moderate (0.50-1.00 range)
        assert row[7] == "0.5"


class TestLogPipelineStats:
    """Tests for pipeline stats CSV logging."""

    @pytest.fixture(autouse=True)
    def enable_data_collection(self):
        with patch("utils.pipeline_logger.is_data_collection_enabled", return_value=True):
            yield

    def test_creates_and_appends(self, tmp_path):
        data_dir = str(tmp_path)

        log_pipeline_stats(data_dir, "/v/test.mp4", 19.0, 0.5, 2.0, 1.5, 4.0)
        csv_path = get_pipeline_stats_path(data_dir)
        assert os.path.exists(csv_path)

        with open(csv_path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 2

        # Append
        log_pipeline_stats(data_dir, "/v/test2.mp4", 30.0, 0.8, 3.0, 2.0, 5.8)
        with open(csv_path, "r") as f:
            lines = f.readlines()
        assert len(lines) == 3

    def test_row_values(self, tmp_path):
        data_dir = str(tmp_path)
        log_pipeline_stats(data_dir, "/v/clip.mp4", 10.5, 0.3, 1.8, 0.9, 3.0)

        csv_path = get_pipeline_stats_path(data_dir)
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)

        assert row[0] == "/v/clip.mp4"
        assert row[1] == "10.5"
        assert row[2] == "0.3"
        assert row[3] == "1.8"
        assert row[4] == "0.9"
        assert row[5] == "3.0"
        # row[6] is timestamp
        assert "T" in row[6]  # ISO format


class TestDataCollectionToggle:
    """Tests that data_collection=false prevents CSV writes."""

    def test_log_video_meta_noop_when_disabled(self, tmp_path):
        with patch("utils.pipeline_logger.is_data_collection_enabled", return_value=False):
            result = {
                "video_info": {"width": 640, "height": 360, "fps": 30, "total_frames": 300},
                "motion_stats": {"mean": 0.35, "max": 1.2, "std": 0.3, "min": 0.01, "median": 0.3},
            }
            config = {"analysis": {"max_width": 320}, "optical_flow": {"algorithm": "farneback"}}
            log_video_meta(str(tmp_path), "/v/test.mp4", result, [], config)

        csv_path = get_video_meta_path(str(tmp_path))
        assert not os.path.exists(csv_path)

    def test_log_pipeline_stats_noop_when_disabled(self, tmp_path):
        with patch("utils.pipeline_logger.is_data_collection_enabled", return_value=False):
            log_pipeline_stats(str(tmp_path), "/v/test.mp4", 10.0, 0.5, 2.0, 1.0, 3.5)

        csv_path = get_pipeline_stats_path(str(tmp_path))
        assert not os.path.exists(csv_path)
