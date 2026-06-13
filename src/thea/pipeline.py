"""Pipeline engine — loads pipeline configs, chains operations, manages context."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """Typed context passed through pipeline operations."""

    source_path: Path
    current_video_path: Path
    analysis_video_path: Optional[Path] = None
    stable_windows: Optional[list] = None
    motion_scores: Optional[list] = None
    motion_stats: Optional[dict] = None
    clips: Optional[list] = None
    data_dir: Optional[Path] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize context for JSON output."""
        return {
            "source_path": str(self.source_path),
            "current_video_path": str(self.current_video_path),
            "analysis_video_path": str(self.analysis_video_path) if self.analysis_video_path else None,
            "stable_windows": self.stable_windows,
            "motion_stats": self.motion_stats,
            "clips": [str(c) for c in self.clips] if self.clips else None,
            "data_dir": str(self.data_dir) if self.data_dir else None,
            "metadata": self.metadata,
        }


def load_pipeline_config(path: str) -> dict:
    """Load and validate a pipeline config JSON file.

    Expected format:
    {
        "version": 1,
        "base_preset": "cinematic",  // optional
        "pipeline": [
            {"operation": "downscale", "config": {}},
            {"operation": "analyze", "config": {}},
            {"operation": "slice", "config": {}}
        ]
    }
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Pipeline config not found: {path}")

    with open(config_path, "r") as f:
        data = json.load(f)

    validate_pipeline_config(data)
    return data


def validate_pipeline_config(config: dict) -> None:
    """Validate pipeline config structure."""
    if not isinstance(config, dict):
        raise ValueError("Pipeline config must be a JSON object")

    if "pipeline" not in config:
        raise ValueError("Pipeline config must have a 'pipeline' array")

    pipeline = config["pipeline"]
    if not isinstance(pipeline, list):
        raise ValueError("'pipeline' must be an array of operation steps")

    if len(pipeline) == 0:
        raise ValueError("'pipeline' must contain at least one operation")

    from thea.operations import get_registry

    registry = get_registry()
    available = set(registry.keys())

    for i, step in enumerate(pipeline):
        if not isinstance(step, dict):
            raise ValueError(f"Pipeline step {i} must be a dict, got {type(step).__name__}")
        if "operation" not in step:
            raise ValueError(f"Pipeline step {i} missing 'operation' key")
        op_name = step["operation"]
        if op_name not in available:
            raise ValueError(
                f"Pipeline step {i}: unknown operation '{op_name}'. "
                f"Available: {sorted(available)}"
            )


def run_pipeline(context: PipelineContext, pipeline_config: dict, base_config: dict) -> PipelineContext:
    """Execute a pipeline, chaining operations through the context.

    Args:
        context: Initial pipeline context (source video, data_dir, etc.)
        pipeline_config: The pipeline definition (with 'pipeline' array)
        base_config: The base Thea config (preset + settings merged)

    Returns:
        Final PipelineContext after all operations complete.
    """
    from thea.operations import get_registry

    registry = get_registry()
    steps = pipeline_config["pipeline"]

    logger.info(f"Running pipeline with {len(steps)} steps on: {context.source_path}")

    for i, step in enumerate(steps):
        op_name = step["operation"]
        step_config = step.get("config", {})

        operation = registry[op_name]

        # Merge step-specific config over base config
        merged_config = _merge_config(base_config, step_config)

        logger.info(f"  Step {i + 1}/{len(steps)}: {op_name}")

        # Validate required inputs
        for key in operation.requires:
            value = getattr(context, key, None)
            if value is None and key not in ("analysis_video_path",):
                # Some keys are optional depending on pipeline order
                pass

        # Execute
        context = operation.execute(context, merged_config)

    logger.info("Pipeline complete.")
    return context


def _merge_config(base: dict, overrides: dict) -> dict:
    """Deep-merge overrides into base config."""
    result = {}
    for key, value in base.items():
        if key in overrides and isinstance(value, dict) and isinstance(overrides[key], dict):
            result[key] = _merge_config(value, overrides[key])
        elif key in overrides:
            result[key] = overrides[key]
        else:
            result[key] = value

    # Add any keys from overrides not in base
    for key, value in overrides.items():
        if key not in result:
            result[key] = value

    return result
