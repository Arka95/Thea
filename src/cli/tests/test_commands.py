"""CLI adapters use faked media APIs; no codecs, hardware or endpoint is exercised."""

import json
from unittest.mock import Mock

import pytest

import main
from cli import commands
from sampled_captioner import CaptionResult, SampledContactSheet


@pytest.mark.parametrize(
    ("name", "arguments", "function", "expected"),
    [
        ("crop", ["1000", "600", "100", "200"], "crop", ("clip.mp4", 1000, 600, 100, 200)),
        ("centercrop", ["1080", "1080"], "centercrop", ("clip.mp4", 1080, 1080)),
        ("ratiocrop", ["9", "16"], "ratiocrop", ("clip.mp4", 9.0, 16.0)),
    ],
)
def test_crop_cli_dispatches_and_prints_result(
    monkeypatch, capsys, name, arguments, function, expected
):
    operation = Mock(return_value="result.mp4")
    monkeypatch.setattr(commands.cropandpan, function, operation)
    monkeypatch.setattr(
        "sys.argv", ["thea", name, "clip.mp4", *arguments, "--output-path", "result.mp4"]
    )
    main.main()
    operation.assert_called_once_with(*expected, output_path="result.mp4")
    assert json.loads(capsys.readouterr().out) == {"output": "result.mp4"}


def test_pan_preserves_api_defaults(monkeypatch):
    operation = Mock(return_value="pan.mp4")
    monkeypatch.setattr(commands.cropandpan, "pan", operation)
    assert main.run_command("pan", path="clip.mp4") == {"output": "pan.mp4"}
    operation.assert_called_once_with(
        "clip.mp4",
        resolutionx=None,
        resolutiony=None,
        startx=None,
        starty=None,
        endx=None,
        endy=None,
        duration=None,
        ratiox=None,
        ratioy=None,
        output_path=None,
    )


def test_pan_cli_forwards_custom_trajectory(monkeypatch, capsys):
    operation = Mock(return_value="pan.mp4")
    monkeypatch.setattr(commands.cropandpan, "pan", operation)
    monkeypatch.setattr(
        "sys.argv",
        [
            "thea",
            "pan",
            "clip.mp4",
            "--resolutionx",
            "1000",
            "--resolutiony",
            "600",
            "--startx",
            "2840",
            "--starty",
            "780",
            "--endx",
            "0",
            "--endy",
            "780",
            "--duration",
            "5",
            "--output-path",
            "pan.mp4",
        ],
    )
    main.main()
    assert operation.call_args.kwargs == {
        "resolutionx": 1000,
        "resolutiony": 600,
        "startx": 2840,
        "starty": 780,
        "endx": 0,
        "endy": 780,
        "duration": 5.0,
        "ratiox": None,
        "ratioy": None,
        "output_path": "pan.mp4",
    }
    assert json.loads(capsys.readouterr().out)["output"] == "pan.mp4"


def test_cli_reports_processing_error(monkeypatch):
    monkeypatch.setattr(commands.cropandpan, "pan", Mock(side_effect=ValueError("Invalid ratio")))
    monkeypatch.setattr("sys.argv", ["thea", "pan", "clip.mp4"])
    with pytest.raises(SystemExit) as error:
        main.main()
    assert error.value.code == 1


def test_caption_uses_selected_model_context_and_environment_key(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake video")
    sheet = tmp_path / "sheet.jpg"
    sample = SampledContactSheet(str(source), str(sheet), (1.0,), 2.0, 176, 144, 0.1)
    result = CaptionResult(str(source), "A boat crosses the sea.", sample, "vision-model")
    backend = Mock()
    captioner = Mock()
    captioner.return_value.caption_video.return_value = result
    monkeypatch.setattr(commands, "OpenAICompatibleVisionBackend", backend)
    monkeypatch.setattr(commands, "SampledCaptioner", captioner)
    monkeypatch.setenv("THEA_CAPTION_API_KEY", "test-key")
    args = main.build_parser().parse_args(
        [
            "caption",
            str(source),
            "--model",
            "vision-model",
            "--contact-sheet",
            str(sheet),
            "--location-in-metadata",
            "--timestamp-in-metadata",
            "--context",
            "Trusted context",
        ]
    )
    values = vars(args)
    output = main.run_command(values.pop("command"), **values)
    assert output["caption"] == result.caption
    assert output["sample"]["image_path"] == str(sheet)
    backend.assert_called_once_with(
        model="vision-model",
        base_url="http://localhost:1234/v1",
        api_key="test-key",
        timeout_sec=120,
    )
    context = captioner.return_value.caption_video.call_args.kwargs["context"]
    assert context.location_in_metadata and context.timestamp_in_metadata
    assert context.additional_context == "Trusted context"
    assert "test-key" not in json.dumps(output)


@pytest.mark.parametrize(
    "field", ["sample_count", "frame_width", "frame_height", "columns", "timeout_sec"]
)
def test_caption_rejects_nonpositive_settings_before_processing(field, monkeypatch):
    captioner = Mock()
    monkeypatch.setattr(commands, "SampledCaptioner", captioner)
    with pytest.raises(ValueError, match="positive"):
        main.run_command("caption", path="missing.mp4", model="vision-model", **{field: 0})
    captioner.assert_not_called()


def test_caption_refuses_existing_contact_sheet(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake video")
    sheet = tmp_path / "sheet.jpg"
    sheet.write_bytes(b"existing image")
    with pytest.raises(FileExistsError):
        main.run_command("caption", path=str(source), model="vision", contact_sheet=str(sheet))
    assert sheet.read_bytes() == b"existing image"


def test_caption_requires_model_in_cli():
    with pytest.raises(SystemExit) as error:
        main.build_parser().parse_args(["caption", "clip.mp4"])
    assert error.value.code == 2


def test_index_dispatches_shared_api(monkeypatch):
    operation = Mock(return_value={"saved": 1})
    monkeypatch.setattr(commands, "index_videos", operation)
    assert main.run_command("index", root="videos", limit=3, infer_loc=True) == {"saved": 1}
    operation.assert_called_once_with(
        root="videos",
        limit=3,
        db=None,
        probe=False,
        geocode=False,
        infer_loc=True,
    )


def test_pipeline_respects_explicit_output_directory(tmp_path, monkeypatch):
    output = tmp_path / "output"
    monkeypatch.setattr(main, "detect_hardware", Mock())
    monkeypatch.setattr(main, "print_header", Mock())
    operation = Mock(return_value={"clips": []})
    monkeypatch.setattr(main, "_run_single_pipeline", operation)
    result = main.run_command("pipeline", path="clip.mp4", output=str(output))
    assert output.is_dir()
    assert operation.call_args.args[2] == str(output)
    assert result == {"results": [{"clips": []}]}


def test_index_api_implies_probe_and_preserves_distinct_counts(monkeypatch, capsys):
    from tools import walkdir

    store = Mock()
    store.all.return_value = [{"name": "first.mp4"}, {"name": "second.mp4"}]
    monkeypatch.setattr(walkdir, "InMemoryStore", Mock(return_value=store))
    geocoder, gazetteer = object(), object()
    monkeypatch.setattr(walkdir, "default_geocoder", Mock(return_value=geocoder))
    monkeypatch.setattr(walkdir, "default_gazetteer", Mock(return_value=gazetteer))
    operation = Mock(return_value=3)
    monkeypatch.setattr(walkdir, "walk_and_store", operation)
    result = walkdir.index_videos("videos", geocode=True, infer_loc=True)
    assert result == {
        "saved": 3,
        "distinct": 2,
        "db": None,
        "samples": [{"name": "first.mp4"}, {"name": "second.mp4"}],
    }
    operation.assert_called_once_with(
        "videos",
        store,
        limit=None,
        probe=True,
        geocoder=geocoder,
        place_gazetteer=gazetteer,
    )
    assert capsys.readouterr().out == ""
