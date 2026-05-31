"""
utils/config_loader.py — Configuration preset discovery, loading, and validation.

Scans config/presets/ for JSON files; each file's stem is the preset name.
"""

import json
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("thea")

# Project root and preset directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRESETS_DIR = PROJECT_ROOT / "config" / "presets"
SETTINGS_DIR = PROJECT_ROOT / "config" / "settings"
DEFAULT_PRESET = "cinematic"


def list_presets() -> dict:
    """Discover all available presets.

    Returns:
        dict mapping preset_name -> file_path
    """
    presets = {}
    if PRESETS_DIR.exists():
        for f in sorted(PRESETS_DIR.glob("*.json")):
            presets[f.stem] = str(f)
    return presets


def load_preset(preset_name: Optional[str] = None) -> dict:
    """Load a configuration preset by name.

    Args:
        preset_name: Name of preset (e.g., "cinematic", "strict").
                     If None, uses DEFAULT_PRESET.

    Returns:
        Validated config dict.

    Raises:
        FileNotFoundError: If preset doesn't exist.
        ValueError: If config is invalid.
    """
    name = preset_name or DEFAULT_PRESET
    presets = list_presets()

    if name not in presets:
        available = ", ".join(presets.keys()) or "(none found)"
        raise FileNotFoundError(
            f"Preset '{name}' not found. Available: {available}\n"
            f"Presets directory: {PRESETS_DIR}"
        )

    with open(presets[name], "r") as f:
        config = json.load(f)

    config["_preset_name"] = name
    config["_preset_path"] = presets[name]
    validate_config(config)
    return config


def load_config_file(path: str) -> dict:
    """Load configuration from an explicit file path.

    Args:
        path: Path to a JSON config file.

    Returns:
        Validated config dict.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        config = json.load(f)

    config["_preset_name"] = Path(path).stem
    config["_preset_path"] = str(path)
    validate_config(config)
    return config


def validate_config(config: dict):
    """Validate config values. Raises ValueError on issues."""
    errors = []

    # Required sections
    for section in ("analysis", "optical_flow", "window_detection", "output", "gpu"):
        if section not in config:
            errors.append(f"Missing config section: '{section}'")

    if errors:
        raise ValueError("Config validation failed:\n  " + "\n  ".join(errors))

    # Optical flow
    algo = config["optical_flow"].get("algorithm", "")
    if algo not in ("farneback",):
        errors.append(f"Unsupported algorithm: '{algo}'. Supported: farneback")
    elif algo not in config["optical_flow"]:
        errors.append(f"Algorithm '{algo}' selected but no parameters section found")

    # Analysis
    if config["analysis"].get("max_width", 0) <= 0:
        errors.append("analysis.max_width must be > 0")
    if config["analysis"].get("motion_smoothing_sigma", 0) < 0:
        errors.append("analysis.motion_smoothing_sigma must be >= 0")

    # Window detection
    wd = config["window_detection"]
    if wd.get("min_duration_sec", 0) <= 0:
        errors.append("window_detection.min_duration_sec must be > 0")
    if wd.get("motion_threshold", -1) < 0:
        errors.append("window_detection.motion_threshold must be >= 0")
    if wd.get("merge_gap_sec", -1) < 0:
        errors.append("window_detection.merge_gap_sec must be >= 0")

    # Farneback specifics
    if algo == "farneback" and "farneback" in config["optical_flow"]:
        fb = config["optical_flow"]["farneback"]
        if fb.get("winsize", 0) < 1:
            errors.append("farneback.winsize must be >= 1")
        if fb.get("levels", 0) < 1:
            errors.append("farneback.levels must be >= 1")
        if fb.get("iterations", 0) < 1:
            errors.append("farneback.iterations must be >= 1")

    if errors:
        raise ValueError("Config validation failed:\n  " + "\n  ".join(errors))


def get_supported_codecs() -> list:
    """Read supported codecs from settings file.

    Returns:
        List of (fourcc, description) tuples.
    """
    codecs_file = SETTINGS_DIR / "supported_codecs.txt"
    codecs = []
    if codecs_file.exists():
        with open(codecs_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("|", 1)
                fourcc = parts[0].strip()
                desc = parts[1].strip() if len(parts) > 1 else ""
                codecs.append((fourcc, desc))
    return codecs
