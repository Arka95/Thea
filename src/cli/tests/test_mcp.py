"""Exercise MCP schemas and tool calls in memory with faked media operations."""

from unittest.mock import Mock

import pytest

import main
from cli import commands
from cli.mcp import create_server

mcp = pytest.importorskip("mcp")
if not hasattr(mcp, "Client"):
    pytest.skip("Install Thea's MCP v2 extra for protocol tests", allow_module_level=True)
Client = mcp.Client


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_mcp_exposes_every_cli_command_with_matching_parameters():
    async with Client(create_server()) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
    parser = main.build_parser()
    subparsers = next(action.choices for action in parser._actions if action.dest == "command")
    assert tools.keys() == subparsers.keys()
    for name, parser in subparsers.items():
        cli_fields = {action.dest for action in parser._actions if action.dest != "help"}
        assert set(tools[name].input_schema["properties"]) == cli_fields


@pytest.mark.anyio
async def test_mcp_pan_defaults_return_output_without_media(monkeypatch):
    operation = Mock(return_value="pan.mp4")
    monkeypatch.setattr(commands.cropandpan, "pan", operation)
    async with Client(create_server()) as client:
        result = await client.call_tool("pan", {"path": "clip.mp4"})
    assert not result.is_error
    assert result.structured_content == {"output": "pan.mp4"}
    assert operation.call_args.args == ("clip.mp4",)
    assert all(value is None for value in operation.call_args.kwargs.values())


@pytest.mark.anyio
async def test_mcp_validation_failure_does_not_run_media(monkeypatch):
    operation = Mock()
    monkeypatch.setattr(commands.cropandpan, "crop", operation)
    async with Client(create_server()) as client:
        result = await client.call_tool("crop", {"path": "clip.mp4", "width": 10})
    assert result.is_error
    operation.assert_not_called()


@pytest.mark.anyio
async def test_mcp_surfaces_actionable_operation_error(monkeypatch):
    monkeypatch.setattr(commands.cropandpan, "pan", Mock(side_effect=ValueError("Invalid ratio")))
    async with Client(create_server()) as client:
        result = await client.call_tool("pan", {"path": "clip.mp4"})
    assert result.is_error
    assert "Invalid ratio" in str(result.content)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "command", ["downscale", "analyze", "slice", "pipeline", "merge", "index", "caption"]
)
async def test_mcp_uses_shared_dispatch_for_other_commands(command, monkeypatch):
    operation = Mock(return_value={"result": command})
    monkeypatch.setattr(main, f"cmd_{command}", operation)
    arguments = {
        "merge": {"paths": ["first.mp4", "second.mp4"]},
        "index": {"root": "videos"},
        "caption": {"path": "clip.mp4", "model": "vision-model"},
    }.get(command, {"path": "clip.mp4"})
    async with Client(create_server()) as client:
        result = await client.call_tool(command, arguments)
    assert not result.is_error
    assert result.structured_content == {"result": command}
    operation.assert_called_once()
