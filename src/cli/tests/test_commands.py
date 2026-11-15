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
    assert captioner.return_value.caption_video.call_args.kwargs["keep_contact_sheet"] is True
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


def test_caption_uses_indexed_locale_and_saves_description(tmp_path, monkeypatch, catalogue_path):
    from tools.storage.sqlite_store import SQLiteStore
    from tools.walkdir import build_video

    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake video")
    video = build_video(str(source))
    video.country, video.state, video.width = "India", "Arunachal Pradesh", 3840
    video.tags = ["Tawang Monastery"]
    video.creation_time = "2024-09-14T11:48:10+0530"
    with SQLiteStore(str(catalogue_path)) as store:
        store.save(video)
    sample = SampledContactSheet(str(source), "sheet.jpg", (1.0,), 2.0, 176, 144, 0.1)
    result = CaptionResult(str(source), "Mountains in Arunachal Pradesh, India.", sample, "vision")
    captioner = Mock()
    captioner.return_value.caption_video.return_value = result
    monkeypatch.setattr(commands, "SampledCaptioner", captioner)
    output = main.run_command("caption", path=str(source), model="vision")
    context = captioner.return_value.caption_video.call_args.kwargs["context"]
    assert (context.country, context.state) == ("India", "Arunachal Pradesh")
    assert output["db"] == str(catalogue_path)
    with SQLiteStore(str(catalogue_path)) as store:
        stored = store.get("videos", video.content_hash)
    assert (stored["description"], stored["width"]) == (result.caption, 3840)
    assert stored["tags"] == ["Tawang Monastery"]
    assert stored["creation_time"] == "2024-09-14T11:48:10+0530"


def test_directory_caption_persists_success_and_retains_description_on_failure(
    tmp_path, monkeypatch, catalogue_path
):
    from tools.storage.sqlite_store import SQLiteStore
    from tools.walkdir import build_video

    root = tmp_path / "footage"
    root.mkdir()
    first, second = root / "first.mp4", root / "second.mp4"
    first.write_bytes(b"first footage")
    second.write_bytes(b"second footage")
    old = build_video(str(second))
    old.description = "Keep the earlier caption."
    with SQLiteStore(str(catalogue_path)) as store:
        store.save(old)

    def caption_video(**kwargs):
        source = kwargs["source_video_path"]
        if source == str(second):
            raise RuntimeError("private endpoint failure")
        sample = SampledContactSheet(source, "sheet.jpg", (1.0,), 2.0, 176, 144, 0.1)
        return CaptionResult(source, "A mountain landscape.", sample, "vision")

    captioner = Mock()
    captioner.return_value.caption_video.side_effect = caption_video
    monkeypatch.setattr(commands, "SampledCaptioner", captioner)
    result = main.run_command("caption", path=str(root), model="vision")
    assert (result["selected"], result["saved"], result["complete"]) == (2, 1, False)
    assert result["errors"] == [{"path": str(second), "error_type": "RuntimeError"}]
    with SQLiteStore(str(catalogue_path)) as store:
        assert store.get("videos", old.content_hash)["description"] == "Keep the earlier caption."
        assert (
            store.get("videos", build_video(str(first)).content_hash)["description"]
            == "A mountain landscape."
        )


def test_caption_detects_source_changes_without_persisting_filesystem_timestamps(
    tmp_path, monkeypatch, catalogue_path
):
    from tools.storage.sqlite_store import SQLiteStore
    from tools.walkdir import build_video

    source = tmp_path / "clip.mp4"
    source.write_bytes(b"original footage")
    video = build_video(str(source))
    video.description = "Keep the original caption."
    with SQLiteStore(str(catalogue_path)) as store:
        store.save(video)

    def caption_video(**kwargs):
        source.write_bytes(b"changed footage with different size")
        sample = SampledContactSheet(str(source), None, (1.0,), 2.0, 176, 144, 0.1)
        return CaptionResult(str(source), "Do not save.", sample, "vision")

    captioner = Mock()
    captioner.return_value.caption_video.side_effect = caption_video
    monkeypatch.setattr(commands, "SampledCaptioner", captioner)
    with pytest.raises(ValueError, match="changed during captioning"):
        main.run_command("caption", path=str(source), model="vision")
    with SQLiteStore(str(catalogue_path)) as store:
        assert store.get("videos", video.content_hash)["description"] == video.description


def test_index_dispatches_shared_api(monkeypatch):
    operation = Mock(return_value={"saved": 1})
    monkeypatch.setattr(commands, "index_videos", operation)
    assert main.run_command(
        "index", root="videos", limit=3, infer_loc=True, report_path="scan.json"
    ) == {"saved": 1}
    operation.assert_called_once_with(
        root="videos",
        limit=3,
        probe=False,
        geocode=False,
        infer_loc=True,
        report_path="scan.json",
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


def test_index_api_implies_probe_and_populates_metadata(tmp_path, monkeypatch, capsys):
    from tools import walkdir

    source = tmp_path / "clip.mp4"
    source.write_bytes(b"synthetic footage")
    geocoder, gazetteer = Mock(), Mock()
    geocoder.country.return_value = "India"
    monkeypatch.setattr(walkdir, "default_geocoder", Mock(return_value=geocoder))
    monkeypatch.setattr(walkdir, "default_gazetteer", Mock(return_value=gazetteer))
    probe = Mock(return_value={"format": {"tags": {"location": "+22.5+88.4/"}}, "streams": []})
    monkeypatch.setattr(walkdir, "run_ffprobe", probe)

    result = walkdir.index_videos(str(tmp_path), geocode=True, infer_loc=True)
    assert result["saved"] == result["distinct"] == 1
    assert result["scan"]["probe"] and result["scan"]["complete"]
    assert result["samples"][0]["country"] == "India"
    assert result["samples"][0]["latitude"] == 22.5
    probe.assert_called_once_with(str(source))
    assert capsys.readouterr().out == ""


def test_index_cli_exports_audit_report(tmp_path, monkeypatch, capsys):
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"synthetic footage")
    report = tmp_path / "scan.json"
    monkeypatch.setattr("sys.argv", ["thea", "index", str(tmp_path), "--report-path", str(report)])
    main.main()

    result = json.loads(capsys.readouterr().out)
    audit = json.loads(report.read_text(encoding="utf-8"))
    assert result["report_path"] == str(report)
    assert audit["files"][0]["path"] == str(source)
    assert audit["discovered"] == audit["saved"] == 1
    assert source.read_bytes() == b"synthetic footage"
