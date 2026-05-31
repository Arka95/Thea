"""
tests/fast/test_config_loader.py — Unit tests for config loading and validation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import json
import pytest
from utils.config_loader import (
    load_preset, list_presets, validate_config, get_supported_codecs, PRESETS_DIR,
)


class TestListPresets:
    def test_finds_presets(self):
        presets = list_presets()
        assert len(presets) >= 4
        assert "cinematic" in presets
        assert "strict" in presets
        assert "permissive" in presets
        assert "action" in presets

    def test_paths_exist(self):
        for name, path in list_presets().items():
            assert os.path.exists(path)


class TestLoadPreset:
    def test_loads_cinematic(self):
        config = load_preset("cinematic")
        assert config["optical_flow"]["algorithm"] == "farneback"
        assert config["window_detection"]["motion_threshold"] == 0.5

    def test_loads_strict(self):
        config = load_preset("strict")
        assert config["window_detection"]["motion_threshold"] == 0.20

    def test_default_is_cinematic(self):
        config = load_preset()
        assert config["_preset_name"] == "cinematic"

    def test_raises_on_unknown_preset(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_preset("nonexistent_preset_xyz")


class TestValidateConfig:
    def test_valid_config_passes(self):
        config = load_preset("cinematic")
        validate_config(config)  # Should not raise

    def test_missing_section_raises(self):
        config = load_preset("cinematic")
        del config["optical_flow"]
        with pytest.raises(ValueError, match="Missing"):
            validate_config(config)

    def test_invalid_algorithm_raises(self):
        config = load_preset("cinematic")
        config["optical_flow"]["algorithm"] = "raft"
        with pytest.raises(ValueError, match="Unsupported"):
            validate_config(config)

    def test_negative_threshold_raises(self):
        config = load_preset("cinematic")
        config["window_detection"]["motion_threshold"] = -1
        with pytest.raises(ValueError):
            validate_config(config)

    def test_zero_max_width_raises(self):
        config = load_preset("cinematic")
        config["analysis"]["max_width"] = 0
        with pytest.raises(ValueError):
            validate_config(config)


class TestSupportedCodecs:
    def test_returns_list(self):
        codecs = get_supported_codecs()
        assert isinstance(codecs, list)
        assert len(codecs) > 10

    def test_contains_common_codecs(self):
        fourcc_codes = [c[0] for c in get_supported_codecs()]
        assert "mp4v" in fourcc_codes
        assert "MJPG" in fourcc_codes

    def test_each_has_description(self):
        for fourcc, desc in get_supported_codecs():
            assert len(fourcc) == 4
            assert len(desc) > 0
