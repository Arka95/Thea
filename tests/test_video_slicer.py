"""
test_video_slicer.py — Tests for the main orchestrator/CLI entry point.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest

from video_slicer import load_config, _validate_config, get_system_info, DEFAULT_CONFIG_PATH


@pytest.fixture
def config():
    return load_config()


class TestLoadConfig:
    """Test configuration loading and validation."""

    def test_loads_default_config(self):
        config = load_config()
        assert isinstance(config, dict)
        assert "optical_flow" in config
        assert "window_detection" in config

    def test_loads_explicit_path(self):
        config = load_config(DEFAULT_CONFIG_PATH)
        assert config["optical_flow"]["algorithm"] == "farneback"

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent_config.json")

    def test_default_values(self, config):
        assert config["analysis"]["max_width"] == 320
        assert config["optical_flow"]["algorithm"] == "farneback"
        assert config["gpu"]["enabled"] is True


class TestValidateConfig:
    """Test config validation catches invalid values."""

    def test_valid_config_passes(self, config):
        # Should not raise
        _validate_config(config)

    def test_missing_section_raises(self, config):
        del config["optical_flow"]
        with pytest.raises(ValueError, match="Missing config section"):
            _validate_config(config)

    def test_invalid_algorithm_raises(self, config):
        config["optical_flow"]["algorithm"] = "invalid_algo"
        with pytest.raises(ValueError, match="Unsupported"):
            _validate_config(config)

    def test_zero_max_width_raises(self, config):
        config["analysis"]["max_width"] = 0
        with pytest.raises(ValueError, match="max_width"):
            _validate_config(config)

    def test_negative_threshold_raises(self, config):
        config["window_detection"]["motion_threshold"] = -1
        with pytest.raises(ValueError, match="motion_threshold"):
            _validate_config(config)

    def test_zero_min_duration_raises(self, config):
        config["window_detection"]["min_duration_sec"] = 0
        with pytest.raises(ValueError, match="min_duration_sec"):
            _validate_config(config)

    def test_negative_merge_gap_raises(self, config):
        config["window_detection"]["merge_gap_sec"] = -0.5
        with pytest.raises(ValueError, match="merge_gap_sec"):
            _validate_config(config)

    def test_invalid_winsize_raises(self, config):
        config["optical_flow"]["farneback"]["winsize"] = 0
        with pytest.raises(ValueError, match="winsize"):
            _validate_config(config)


class TestGetSystemInfo:
    """Test system info collection."""

    def test_returns_dict(self, config):
        info = get_system_info(config)
        assert isinstance(info, dict)

    def test_has_required_fields(self, config):
        info = get_system_info(config)
        assert "opencv_version" in info
        assert "python_version" in info
        assert "cuda_available" in info
        assert "timestamp" in info
        assert "platform" in info

    def test_opencv_version_format(self, config):
        info = get_system_info(config)
        # Should be like "4.13.0"
        parts = info["opencv_version"].split(".")
        assert len(parts) >= 2

    def test_cuda_available_on_this_machine(self, config):
        info = get_system_info(config)
        assert info["cuda_available"] is True
        assert info["cuda_device_count"] >= 1


class TestMainPipeline:
    """Integration test for the full pipeline."""

    def test_main_runs_successfully(self, tmp_path):
        """Full pipeline should complete without errors."""
        from video_slicer import main

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            sample = os.path.join(os.path.dirname(__file__), "..", "sample.MP4")
            metadata = main(video_path=sample)

            assert metadata is not None
            assert metadata["thea_version"] == "0.2.0"
            assert len(metadata["windows_detected"]) == 3
            assert metadata["video"]["width"] == 3840
            assert metadata["total_pipeline_time_sec"] > 0

            # Check metadata file was written
            assert os.path.exists("sample_metadata.json")
        finally:
            os.chdir(original_cwd)
