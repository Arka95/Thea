"""Exercise MCP schemas and tool calls in memory with faked media operations."""

import json
import sqlite3
from contextlib import closing
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


@pytest.mark.anyio
async def test_mcp_index_exports_scan_audit(tmp_path):
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"synthetic footage")
    report = tmp_path / "scan.json"
    async with Client(create_server()) as client:
        result = await client.call_tool(
            "index", {"root": str(tmp_path), "report_path": str(report)}
        )
    assert not result.is_error
    assert result.structured_content["scan"]["complete"]
    audit = json.loads(report.read_text(encoding="utf-8"))
    assert audit["files"] == [
        {
            "path": str(source),
            "status": "saved",
            "content_hash": result.structured_content["samples"][0]["content_hash"],
            "duplicate_in_scan": False,
        }
    ]


@pytest.mark.anyio
async def test_mcp_import_and_search_use_same_configured_catalogue(tmp_path, catalogue_path):
    from tools.models.video import Video
    from tools.storage.sqlite_store import SQLiteStore

    legacy = tmp_path / "legacy.sqlite3"
    with SQLiteStore(str(legacy)) as store:
        store.save(
            Video(
                path=r"E:\Arunachal\drone\clip.mp4",
                name="clip.mp4",
                content_hash="clip",
                country="India",
                state="Arunachal Pradesh",
                description="A mountain landscape.",
            )
        )
    async with Client(create_server()) as client:
        imported = await client.call_tool("importindex", {"paths": [str(legacy)]})
        found = await client.call_tool("search", {"query": "drone footage in Arunachal for nature"})
    assert not imported.is_error and not found.is_error
    assert (
        imported.structured_content["db"] == found.structured_content["db"] == str(catalogue_path)
    )
    assert found.structured_content["results"][0]["content_hash"] == "clip"


@pytest.mark.anyio
async def test_mcp_index_migrates_legacy_schema_and_preserves_captions_tags_and_time(
    tmp_path, catalogue_path
):
    from tools.walkdir import build_video

    source = tmp_path / "clip.mp4"
    source.write_bytes(b"synthetic footage")
    video = build_video(str(source))
    with closing(sqlite3.connect(catalogue_path)) as connection, connection:
        connection.execute(
            "CREATE TABLE videos (content_hash PRIMARY KEY,path UNIQUE,name,description,tags,"
            "creation_time,created_time,video_codec,audio_codec,raw_metadata)"
        )
        connection.execute(
            "INSERT INTO videos VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                video.content_hash,
                str(source),
                "clip.mp4",
                "A courtyard.",
                '["Tawang Monastery"]',
                "2025-03-01T10:20:30+05:30",
                1700000000,
                "hevc",
                "aac",
                "must be ignored",
            ),
        )
    async with Client(create_server()) as client:
        indexed = await client.call_tool("index", {"root": str(tmp_path)})
        found = await client.call_tool("search", {"query": "Tawang Monastery"})
    assert not indexed.is_error and not found.is_error
    schema = indexed.structured_content["schema"]
    assert {"video_codec", "audio_codec", "raw_metadata", "created_time"} <= set(
        schema["removed_columns"]
    )
    record = found.structured_content["results"][0]
    assert record["tags"] == ["Tawang Monastery"]
    assert record["description"] == "A courtyard."
    assert record["creation_time"] == "2025-03-01T10:20:30+05:30"
    with closing(sqlite3.connect(catalogue_path)) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(videos)")}
    assert columns == set(schema["columns"]) == record.keys() - {"score", "exists"}
