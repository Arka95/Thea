"""
test_batch_extract.py — Tests for batch extraction utility.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import csv
import pickle
import pytest

from batch_extract import discover_videos, process_single_video, write_csv, write_pkl, run_batch


@pytest.fixture
def config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    with open(config_path) as f:
        return json.load(f)


@pytest.fixture
def project_dir():
    return os.path.join(os.path.dirname(__file__), "..")


class TestDiscoverVideos:
    """Test video file discovery."""

    def test_finds_sample_video(self, project_dir):
        videos = discover_videos(project_dir)
        filenames = [os.path.basename(v) for v in videos]
        assert "sample.MP4" in filenames

    def test_returns_absolute_paths(self, project_dir):
        videos = discover_videos(project_dir)
        for v in videos:
            assert os.path.isabs(v) or os.path.exists(v)

    def test_empty_directory(self, tmp_path):
        videos = discover_videos(str(tmp_path))
        assert videos == []

    def test_ignores_non_video_files(self, tmp_path):
        # Create non-video files
        (tmp_path / "test.txt").write_text("hello")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        videos = discover_videos(str(tmp_path))
        assert videos == []


class TestProcessSingleVideo:
    """Test single video processing."""

    def test_processes_sample_successfully(self, config):
        video_path = os.path.join(os.path.dirname(__file__), "..", "sample.MP4")
        result = process_single_video((video_path, config))

        assert result["status"] == "success"
        assert result["filename"] == "sample.MP4"
        assert result["width"] == 3840
        assert result["height"] == 2160
        assert result["window_count"] == 3
        assert result["overall_assessment"] == "stable"
        assert result["stock_footage_grade"] is True

    def test_failed_video_returns_error(self, config):
        result = process_single_video(("nonexistent.mp4", config))
        assert result["status"] == "error"
        assert result["error"] is not None

    def test_result_has_motion_features(self, config):
        video_path = os.path.join(os.path.dirname(__file__), "..", "sample.MP4")
        result = process_single_video((video_path, config))

        assert "motion_mean" in result
        assert "motion_std" in result
        assert "motion_p95" in result
        assert result["motion_mean"] > 0

    def test_result_has_windows(self, config):
        video_path = os.path.join(os.path.dirname(__file__), "..", "sample.MP4")
        result = process_single_video((video_path, config))

        assert "windows" in result
        assert len(result["windows"]) == 3
        assert result["total_extractable_sec"] > 10


class TestWriteCSV:
    """Test CSV output writing."""

    def test_writes_valid_csv(self, tmp_path, config):
        video_path = os.path.join(os.path.dirname(__file__), "..", "sample.MP4")
        result = process_single_video((video_path, config))

        csv_path = str(tmp_path / "test_output.csv")
        write_csv([result], csv_path)

        assert os.path.exists(csv_path)
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["filename"] == "sample.MP4"
            assert rows[0]["window_count"] == "3"
            assert rows[0]["overall_assessment"] == "stable"

    def test_csv_has_suggested_windows(self, tmp_path, config):
        video_path = os.path.join(os.path.dirname(__file__), "..", "sample.MP4")
        result = process_single_video((video_path, config))

        csv_path = str(tmp_path / "test_output.csv")
        write_csv([result], csv_path)

        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            row = next(reader)
            assert "suggested_windows" in row
            assert "s" in row["suggested_windows"]  # Contains time markers


class TestWritePkl:
    """Test pickle output writing."""

    def test_writes_valid_pkl(self, tmp_path, config):
        video_path = os.path.join(os.path.dirname(__file__), "..", "sample.MP4")
        result = process_single_video((video_path, config))

        pkl_path = str(tmp_path / "test_output.pkl")
        write_pkl([result], pkl_path)

        assert os.path.exists(pkl_path)
        with open(pkl_path, "rb") as f:
            data = pickle.load(f)
            assert len(data) == 1
            assert data[0]["filename"] == "sample.MP4"
            # PKL includes per-frame scores
            assert "motion_scores" in data[0]
            assert len(data[0]["motion_scores"]) > 500


class TestRunBatch:
    """Integration test for batch processing."""

    def test_batch_single_video_csv(self, tmp_path):
        """Run batch on a directory with one video."""
        # Copy or symlink sample video to tmp_path
        sample = os.path.join(os.path.dirname(__file__), "..", "sample.MP4")
        # Use original dir containing sample
        output_path = str(tmp_path / "batch_test.csv")

        # Create a temp dir with just the sample
        import shutil
        test_dir = tmp_path / "videos"
        test_dir.mkdir()
        shutil.copy2(sample, test_dir / "sample.MP4")

        run_batch(
            directory=str(test_dir),
            output_format="csv",
            output_path=output_path,
        )

        assert os.path.exists(output_path)
        with open(output_path, newline="") as f:
            rows = list(csv.DictReader(f))
            assert len(rows) == 1
            assert rows[0]["status"] == "success"
