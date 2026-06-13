"""Tests for pipeline config loading, validation, and execution."""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from thea.pipeline import (
    PipelineContext,
    load_pipeline_config,
    validate_pipeline_config,
    run_pipeline,
    _merge_config,
)
from thea.operations import get_registry


class TestPipelineConfigLoading:
    """Test pipeline config file loading."""

    def test_load_valid_config(self, tmp_path):
        config = {
            "version": 1,
            "pipeline": [
                {"operation": "downscale", "config": {}},
                {"operation": "analyze", "config": {}},
            ],
        }
        config_file = tmp_path / "pipeline.json"
        config_file.write_text(json.dumps(config))

        loaded = load_pipeline_config(str(config_file))
        assert loaded["version"] == 1
        assert len(loaded["pipeline"]) == 2
        assert loaded["pipeline"][0]["operation"] == "downscale"

    def test_load_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_pipeline_config("/nonexistent/path/pipeline.json")

    def test_load_invalid_json_raises(self, tmp_path):
        config_file = tmp_path / "bad.json"
        config_file.write_text("not json {{{")
        with pytest.raises(json.JSONDecodeError):
            load_pipeline_config(str(config_file))


class TestPipelineConfigValidation:
    """Test pipeline config validation logic."""

    def test_valid_config_passes(self):
        config = {
            "version": 1,
            "pipeline": [
                {"operation": "downscale", "config": {}},
                {"operation": "analyze", "config": {}},
                {"operation": "slice", "config": {}},
            ],
        }
        # Should not raise
        validate_pipeline_config(config)

    def test_missing_pipeline_key_raises(self):
        with pytest.raises(ValueError, match="must have a 'pipeline' array"):
            validate_pipeline_config({"version": 1})

    def test_empty_pipeline_raises(self):
        with pytest.raises(ValueError, match="at least one operation"):
            validate_pipeline_config({"pipeline": []})

    def test_non_list_pipeline_raises(self):
        with pytest.raises(ValueError, match="must be an array"):
            validate_pipeline_config({"pipeline": "not a list"})

    def test_step_missing_operation_raises(self):
        with pytest.raises(ValueError, match="missing 'operation' key"):
            validate_pipeline_config({"pipeline": [{"config": {}}]})

    def test_unknown_operation_raises(self):
        with pytest.raises(ValueError, match="unknown operation"):
            validate_pipeline_config({"pipeline": [{"operation": "nonexistent_op"}]})

    def test_non_dict_step_raises(self):
        with pytest.raises(ValueError, match="must be a dict"):
            validate_pipeline_config({"pipeline": ["not a dict"]})


class TestMergeConfig:
    """Test config merging logic."""

    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        overrides = {"b": 99, "c": 3}
        result = _merge_config(base, overrides)
        assert result == {"a": 1, "b": 99, "c": 3}

    def test_deep_merge(self):
        base = {"analysis": {"max_width": 320, "sigma": 2}}
        overrides = {"analysis": {"max_width": 480}}
        result = _merge_config(base, overrides)
        assert result["analysis"]["max_width"] == 480
        assert result["analysis"]["sigma"] == 2

    def test_empty_override(self):
        base = {"a": 1}
        result = _merge_config(base, {})
        assert result == {"a": 1}


class TestOperationRegistry:
    """Test operation registry discovery."""

    def test_registry_loads_all_operations(self):
        registry = get_registry()
        expected = {"downscale", "analyze", "slice", "colorgrade", "slowdown", "speedup"}
        assert set(registry.keys()) == expected

    def test_operations_have_metadata(self):
        registry = get_registry()
        for name, op in registry.items():
            assert op.name == name
            assert op.description != ""
            assert isinstance(op.requires, list)
            assert isinstance(op.provides, list)
            assert op.status in ("implemented", "stub")

    def test_stub_operations_identified(self):
        registry = get_registry()
        stubs = {name for name, op in registry.items() if op.status == "stub"}
        assert stubs == {"colorgrade", "slowdown", "speedup"}

    def test_implemented_operations(self):
        registry = get_registry()
        implemented = {name for name, op in registry.items() if op.status == "implemented"}
        assert implemented == {"downscale", "analyze", "slice"}

    def test_operation_to_dict(self):
        registry = get_registry()
        d = registry["downscale"].to_dict()
        assert d["name"] == "downscale"
        assert d["status"] == "implemented"
        assert "source_path" in d["requires"]
        assert "analysis_video_path" in d["provides"]


class TestPipelineExecution:
    """Test pipeline execution with stub/mock operations."""

    def test_stub_operation_raises_not_implemented(self):
        registry = get_registry()
        context = PipelineContext(
            source_path=Path("test.mp4"),
            current_video_path=Path("test.mp4"),
        )
        with pytest.raises(NotImplementedError):
            registry["colorgrade"].execute(context, {})

    def test_pipeline_context_to_dict(self):
        ctx = PipelineContext(
            source_path=Path("/videos/test.mp4"),
            current_video_path=Path("/videos/test.mp4"),
            data_dir=Path("/data"),
            stable_windows=[{"start_sec": 1.0, "end_sec": 5.0}],
        )
        d = ctx.to_dict()
        assert d["source_path"] == "/videos/test.mp4" or "test.mp4" in d["source_path"]
        assert d["stable_windows"] == [{"start_sec": 1.0, "end_sec": 5.0}]
        assert "data" in d["data_dir"]
