"""Merge regression tests without real FFmpeg, media or hardware execution."""

import copy
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

import main
from merger import merger


@pytest.fixture
def merge_case(tmp_path, monkeypatch):
    first = tmp_path / "first's clip.mp4"
    second = tmp_path / "second.mp4"
    first.write_bytes(b"first source")
    second.write_bytes(b"second source")
    probe = {
        "format": {"duration": "6.0"},
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "hevc",
                "profile": "Main",
                "time_base": "1/90000",
                "width": 3840,
                "height": 2160,
                "pix_fmt": "yuv420p",
            },
            {
                "codec_type": "audio",
                "codec_name": "aac",
                "profile": "LC",
                "time_base": "1/48000",
                "sample_rate": "48000",
                "channels": 2,
                "channel_layout": "stereo",
            },
        ],
    }
    state = SimpleNamespace(
        inputs=[str(first), str(second)],
        output=str(tmp_path / "result.mp4"),
        probes={str(first): copy.deepcopy(probe), str(second): copy.deepcopy(probe)},
        output_probe=copy.deepcopy(probe),
        input_count=2,
        commands=[],
        manifest="",
    )

    def fake_probe(path):
        if path in state.probes:
            return copy.deepcopy(state.probes[path])
        result = copy.deepcopy(state.output_probe)
        result["format"]["duration"] = str(6 * state.input_count)
        return result

    def fake_run(command, **kwargs):
        state.commands.append(command)
        manifest = Path(command[command.index("-i") + 1])
        state.manifest = manifest.read_text(encoding="utf-8")
        Path(command[-1]).write_bytes(b"merged output")
        return SimpleNamespace(returncode=0, stderr="")

    state.run = fake_run
    monkeypatch.setattr(merger, "run_ffprobe", fake_probe)
    monkeypatch.setattr(merger, "get_ffmpeg_exe", lambda: "ffmpeg")
    monkeypatch.setattr(merger.subprocess, "run", fake_run)
    return state


def test_merge_preserves_order_audio_sources_and_escaped_paths(merge_case):
    case = merge_case
    result = merger.merge_videos(list(reversed(case.inputs)), case.output)
    lines = case.manifest.splitlines()
    assert lines[1] == f"file '{case.inputs[1]}'"
    assert lines[2] == "file '" + case.inputs[0].replace("'", "'\\''") + "'"
    command = case.commands[0]
    assert command[command.index("-map") + 1] == "0"
    assert command[command.index("-c") + 1] == "copy"
    assert case.inputs[0] not in command and case.inputs[1] not in command
    assert result["input_count"] == 2 and result["duration_sec"] == 12
    assert Path(case.output).read_bytes() == b"merged output"
    assert Path(case.inputs[0]).read_bytes() == b"first source"
    assert Path(case.inputs[1]).read_bytes() == b"second source"
    assert not list(Path(case.output).parent.glob(".thea-merge-*"))


@pytest.mark.parametrize(
    "stream,key,value",
    [
        (0, "codec_name", "h264"),
        (0, "width", 1920),
        (0, "time_base", "1/1000"),
        (1, "sample_rate", "44100"),
        (1, "channels", 1),
    ],
)
def test_merge_rejects_incompatible_streams_before_running_ffmpeg(merge_case, stream, key, value):
    case = merge_case
    case.probes[case.inputs[1]]["streams"][stream][key] = value
    with pytest.raises(ValueError, match="Incompatible streams"):
        merger.merge_videos(case.inputs, case.output)
    assert case.commands == []
    assert not Path(case.output).exists()


def test_merge_accepts_variable_frame_rate_clips(merge_case):
    case = merge_case
    case.probes[case.inputs[0]]["streams"][0]["r_frame_rate"] = "30/1"
    case.probes[case.inputs[1]]["streams"][0]["r_frame_rate"] = "120/1"
    assert merger.merge_videos(case.inputs, case.output)["input_count"] == 2


@pytest.mark.parametrize("invalid", ["single", "missing", "no_extension"])
def test_merge_rejects_invalid_inputs_before_running_ffmpeg(merge_case, invalid):
    case = merge_case
    inputs = case.inputs[:1] if invalid == "single" else list(case.inputs)
    if invalid == "missing":
        inputs[1] = str(Path(case.output).parent / "missing.mp4")
    output = str(Path(case.output).with_suffix("")) if invalid == "no_extension" else case.output
    with pytest.raises((ValueError, FileNotFoundError)):
        merger.merge_videos(inputs, output)
    assert case.commands == []


@pytest.mark.parametrize("source_as_output", [False, True])
def test_merge_never_overwrites_existing_output_or_source(merge_case, source_as_output):
    case = merge_case
    target = Path(case.inputs[0] if source_as_output else case.output)
    if not source_as_output:
        target.write_bytes(b"existing output")
    original = target.read_bytes()
    with pytest.raises(FileExistsError):
        merger.merge_videos(case.inputs, str(target))
    assert target.read_bytes() == original
    assert case.commands == []


def test_failed_ffmpeg_removes_partial_output(merge_case, monkeypatch):
    case = merge_case

    def fail(command, **kwargs):
        Path(command[-1]).write_bytes(b"partial output")
        return SimpleNamespace(returncode=1, stderr="merge failed")

    monkeypatch.setattr(merger.subprocess, "run", fail)
    with pytest.raises(RuntimeError, match="FFmpeg merge failed"):
        merger.merge_videos(case.inputs, case.output)
    assert not Path(case.output).exists()
    assert not list(Path(case.output).parent.glob(".thea-merge-*"))


def test_merge_does_not_replace_a_concurrently_created_output(merge_case, monkeypatch):
    case = merge_case

    def race(command, **kwargs):
        result = case.run(command, **kwargs)
        Path(case.output).write_bytes(b"another writer")
        return result

    monkeypatch.setattr(merger.subprocess, "run", race)
    with pytest.raises(FileExistsError):
        merger.merge_videos(case.inputs, case.output)
    assert Path(case.output).read_bytes() == b"another writer"


def test_merge_discards_output_if_source_changes(merge_case, monkeypatch):
    case = merge_case

    def change_source(command, **kwargs):
        result = case.run(command, **kwargs)
        Path(case.inputs[0]).write_bytes(b"external edit")
        return result

    monkeypatch.setattr(merger.subprocess, "run", change_source)
    with pytest.raises(RuntimeError, match="input changed"):
        merger.merge_videos(case.inputs, case.output)
    assert not Path(case.output).exists()


def test_merge_validates_output_resolution(merge_case):
    case = merge_case
    case.output_probe["streams"][0]["width"] = 1920
    with pytest.raises(RuntimeError, match="codec or resolution"):
        merger.merge_videos(case.inputs, case.output)
    assert not Path(case.output).exists()


def test_merge_accepts_large_lists_without_expanding_the_command_line(merge_case):
    case = merge_case
    paths = case.inputs * 501
    case.input_count = len(paths)
    result = merger.merge_videos(paths, case.output)
    assert result["input_count"] == 1002
    assert len(case.manifest.splitlines()) == 1003
    assert len(case.commands[0]) < 30


def test_read_manifest_preserves_order_and_resolves_relative_paths(tmp_path):
    manifest = tmp_path / "inputs.txt"
    manifest.write_text("\ufeffsecond.mp4\n\nfirst clip.mp4\n", encoding="utf-8")
    assert merger.read_video_manifest(str(manifest)) == [
        str(tmp_path / "second.mp4"),
        str(tmp_path / "first clip.mp4"),
    ]


@pytest.mark.parametrize("explicit_output", [False, True])
def test_merge_cli_uses_manifest_and_respects_output_override(
    tmp_path, monkeypatch, explicit_output
):
    manifest = tmp_path / "inputs.txt"
    manifest.write_text("second.mp4\nfirst.mp4\n", encoding="utf-8")
    captured = {}

    def fake_merge(paths, output):
        captured.update(paths=paths, output=output)
        return {
            "input_count": len(paths),
            "output": output,
            "duration_sec": 12,
            "width": 3840,
            "height": 2160,
            "time_sec": 0,
        }

    def resolve(path):
        if explicit_output:
            raise AssertionError("Explicit output must bypass configured data_dir")
        return str(tmp_path / "configured")

    monkeypatch.setattr(main, "resolve_data_dir", resolve)
    monkeypatch.setattr(main, "merge_videos", fake_merge)
    arguments = ["merge", "--manifest", str(manifest)]
    if explicit_output:
        arguments += ["--output-path", str(tmp_path / "chosen.mp4")]
    args = main.build_parser().parse_args(arguments)
    main.cmd_merge(args, {})
    assert captured["paths"] == [str(tmp_path / "second.mp4"), str(tmp_path / "first.mp4")]
    if explicit_output:
        assert captured["output"] == str(tmp_path / "chosen.mp4")
    else:
        assert Path(captured["output"]).parent == tmp_path / "configured" / "merged"


def test_merge_cli_rejects_ambiguous_input_sources():
    args = main.build_parser().parse_args(
        ["merge", "first.mp4", "second.mp4", "--manifest", "inputs.txt"]
    )
    with pytest.raises(ValueError, match="not both"):
        main.cmd_merge(args, {})
