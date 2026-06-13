"""
thea.mcp.server — MCP server exposing Thea operations as AI-agent tools.

Run with:
    python -m thea.mcp.server

Tools exposed:
    - list_operations: Discover available pipeline operations and their status
    - run_operation: Execute a single operation on a video
    - run_pipeline: Execute a full pipeline config on a video
    - get_video_info: Extract metadata from a video file

Requires: pip install mcp
"""

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger("thea.mcp")

try:
    from mcp.server import Server
    from mcp.server.stdio import run_server
    from mcp.types import Tool, TextContent
except ImportError:
    print(
        "ERROR: MCP package not installed. Install with:\n"
        "  pip install mcp\n"
        "Or install thea with MCP support:\n"
        "  pip install -e .[mcp]",
        file=sys.stderr,
    )
    sys.exit(1)

import thea  # triggers sys.path setup
from thea.operations import get_registry
from thea.pipeline import PipelineContext, load_pipeline_config, run_pipeline, validate_pipeline_config
from utils.config_loader import load_preset, list_presets
from utils.settings import resolve_data_dir
from utils.video_io import get_video_info, is_video_file

app = Server("thea")


@app.list_tools()
async def list_tools():
    """Expose Thea tools to the MCP client."""
    return [
        Tool(
            name="list_operations",
            description="List all available Thea pipeline operations with their status, requirements, and outputs.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="list_presets",
            description="List available configuration presets (cinematic, strict, permissive, action).",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_video_info",
            description="Get metadata (resolution, fps, duration, codec) for a video file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_path": {"type": "string", "description": "Absolute path to the video file"},
                },
                "required": ["video_path"],
            },
        ),
        Tool(
            name="run_operation",
            description="Execute a single pipeline operation on a video. Returns updated context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Operation name (downscale, analyze, slice, etc.)",
                    },
                    "video_path": {"type": "string", "description": "Absolute path to the video file"},
                    "preset": {
                        "type": "string",
                        "description": "Config preset name (default: cinematic)",
                        "default": "cinematic",
                    },
                    "config_overrides": {
                        "type": "object",
                        "description": "Optional config overrides merged on top of preset",
                        "default": {},
                    },
                },
                "required": ["operation", "video_path"],
            },
        ),
        Tool(
            name="run_pipeline",
            description=(
                "Execute a full pipeline on a video. The pipeline is an ordered array of operations. "
                "Returns the final context with all results."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "video_path": {"type": "string", "description": "Absolute path to the video file"},
                    "pipeline": {
                        "type": "array",
                        "description": "Array of pipeline steps: [{operation, config?}, ...]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "operation": {"type": "string"},
                                "config": {"type": "object", "default": {}},
                            },
                            "required": ["operation"],
                        },
                    },
                    "preset": {
                        "type": "string",
                        "description": "Base config preset (default: cinematic)",
                        "default": "cinematic",
                    },
                },
                "required": ["video_path", "pipeline"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool invocations."""
    try:
        if name == "list_operations":
            return await _handle_list_operations()
        elif name == "list_presets":
            return await _handle_list_presets()
        elif name == "get_video_info":
            return await _handle_get_video_info(arguments)
        elif name == "run_operation":
            return await _handle_run_operation(arguments)
        elif name == "run_pipeline":
            return await _handle_run_pipeline(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {type(e).__name__}: {e}")]


async def _handle_list_operations():
    registry = get_registry()
    ops = {name: op.to_dict() for name, op in sorted(registry.items())}
    return [TextContent(type="text", text=json.dumps(ops, indent=2))]


async def _handle_list_presets():
    presets = list_presets()
    result = {}
    for name, path in presets.items():
        with open(path) as f:
            cfg = json.load(f)
        result[name] = {
            "path": path,
            "motion_threshold": cfg["window_detection"]["motion_threshold"],
            "min_duration_sec": cfg["window_detection"]["min_duration_sec"],
        }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _handle_get_video_info(arguments: dict):
    video_path = arguments["video_path"]
    if not Path(video_path).exists():
        return [TextContent(type="text", text=f"File not found: {video_path}")]
    if not is_video_file(video_path):
        return [TextContent(type="text", text=f"Not a supported video file: {video_path}")]
    info = get_video_info(video_path)
    return [TextContent(type="text", text=json.dumps(info, indent=2))]


async def _handle_run_operation(arguments: dict):
    op_name = arguments["operation"]
    video_path = arguments["video_path"]
    preset_name = arguments.get("preset", "cinematic")
    config_overrides = arguments.get("config_overrides", {})

    registry = get_registry()
    if op_name not in registry:
        return [TextContent(type="text", text=f"Unknown operation: {op_name}. Available: {sorted(registry.keys())}")]

    if not Path(video_path).exists():
        return [TextContent(type="text", text=f"File not found: {video_path}")]

    config = load_preset(preset_name)
    # Apply overrides
    for key, value in config_overrides.items():
        if isinstance(value, dict) and key in config:
            config[key].update(value)
        else:
            config[key] = value

    data_dir = resolve_data_dir(video_path)
    source = Path(video_path).resolve()
    context = PipelineContext(
        source_path=source,
        current_video_path=source,
        data_dir=Path(data_dir),
    )

    operation = registry[op_name]
    context = operation.execute(context, config)

    return [TextContent(type="text", text=json.dumps(context.to_dict(), indent=2))]


async def _handle_run_pipeline(arguments: dict):
    video_path = arguments["video_path"]
    pipeline_steps = arguments["pipeline"]
    preset_name = arguments.get("preset", "cinematic")

    if not Path(video_path).exists():
        return [TextContent(type="text", text=f"File not found: {video_path}")]

    pipeline_config = {"version": 1, "pipeline": pipeline_steps}
    validate_pipeline_config(pipeline_config)

    config = load_preset(preset_name)
    data_dir = resolve_data_dir(video_path)
    source = Path(video_path).resolve()

    context = PipelineContext(
        source_path=source,
        current_video_path=source,
        data_dir=Path(data_dir),
    )

    context = run_pipeline(context, pipeline_config, config)

    return [TextContent(type="text", text=json.dumps(context.to_dict(), indent=2))]


def main():
    """Run the MCP server on stdio."""
    logging.basicConfig(level=logging.INFO)
    import asyncio
    asyncio.run(run_server(app))


if __name__ == "__main__":
    main()
