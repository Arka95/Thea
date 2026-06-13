# Thea MCP — Agent Instructions

## Overview

Thea is a GPU-accelerated video stock-footage extraction CLI. This MCP server exposes its operations as tools for AI agents.

## Available Tools

| Tool | Description |
|------|-------------|
| `list_operations` | Discover all pipeline operations and their status |
| `list_presets` | Get available config presets with key parameters |
| `get_video_info` | Extract metadata (resolution, fps, duration) from a video |
| `run_operation` | Execute a single operation on a video |
| `run_pipeline` | Execute a complete pipeline on a video |

## Workflow

1. **Discover** what's available: call `list_operations` and `list_presets`
2. **Inspect** the video: call `get_video_info` with the video path
3. **Choose** a preset based on the content (cinematic for slow shots, action for fast footage)
4. **Run** either a single operation or a full pipeline

## Pipeline Config Format

```json
{
  "version": 1,
  "pipeline": [
    {"operation": "downscale", "config": {}},
    {"operation": "analyze", "config": {"window_detection": {"motion_threshold": 0.8}}},
    {"operation": "slice", "config": {}}
  ]
}
```

## Operations Reference

| Operation | Status | Requires | Provides |
|-----------|--------|----------|----------|
| `downscale` | ✅ implemented | source_path | analysis_video_path |
| `analyze` | ✅ implemented | analysis_video_path | motion_scores, stable_windows, motion_stats |
| `slice` | ✅ implemented | stable_windows | clips |
| `colorgrade` | 🚧 stub | — | — |
| `slowdown` | 🚧 stub | — | — |
| `speedup` | 🚧 stub | — | — |

## Presets

- **cinematic** (default): threshold=0.5, min_duration=3s — best for slow, steady shots
- **strict**: threshold=0.2, min_duration=8s — very low motion only
- **permissive**: threshold=1.0, min_duration=3s — accepts moderate motion
- **action**: threshold=2.0, min_duration=2s — accepts high motion

## Running the MCP Server

```bash
python -m thea.mcp.server
```

Add to Cline MCP config:
```json
{
  "thea": {
    "command": "python",
    "args": ["-m", "thea.mcp.server"],
    "cwd": "C:\\Projects\\Thea"
  }
}
```

## CLI Usage (alternative to MCP)

```bash
# Full pipeline on a single video
thea pipeline video.mp4 --preset cinematic

# Custom pipeline config
thea pipeline video.mp4 --pipeline-config my_pipeline.json

# Batch mode (directory of videos)
thea pipeline ./videos/ --preset action

# Individual operations
thea downscale video.mp4 --width 480
thea analyze video.mp4 --preset strict
thea slice video.mp4 --preset permissive

# Discovery
thea operations   # JSON output of all operations
thea presets      # Table of available presets
```
