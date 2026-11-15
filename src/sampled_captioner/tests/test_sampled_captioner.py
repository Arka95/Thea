"""Fast tests for sampled frame layout, prompting, and local vision requests."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pytest

from sampled_captioner import CaptionResult, SampledCaptioner, SampledContactSheet
from sampled_captioner.captioner import (
    CaptionContext,
    OpenAICompatibleVisionBackend,
    build_caption_prompt,
)
from sampled_captioner.sampler import (
    _assemble_contact_sheet,
    _letterbox_frame,
    select_frame_indices,
)


def test_select_frame_indices_uses_central_ninety_percent():
    indices = select_frame_indices(total_frames=100, sample_count=4)

    assert indices == [5, 35, 64, 94]


def test_select_frame_indices_caps_count_to_available_frames():
    assert select_frame_indices(total_frames=2, sample_count=12) == [0, 1]


def test_letterbox_preserves_shape_and_adds_padding():
    source = np.full((100, 200, 3), 255, dtype=np.uint8)

    result = _letterbox_frame(source, width=176, height=144)

    assert result.shape == (144, 176, 3)
    assert np.all(result[0] == 0)
    assert np.all(result[72] == 255)


def test_contact_sheet_uses_requested_columns():
    frames = [np.full((144, 176, 3), value, dtype=np.uint8) for value in range(5)]

    result = _assemble_contact_sheet(frames, columns=4)

    assert result.shape == (288, 704, 3)
    assert result[10, 10, 0] == 0
    assert result[154, 10, 0] == 4


def test_prompt_skips_location_and_time_when_metadata_has_them():
    prompt = build_caption_prompt(
        CaptionContext(
            location_in_metadata=True,
            timestamp_in_metadata=True,
        )
    )

    assert "do not mention location" in prompt
    assert "do not mention time of day" in prompt
    assert "Always describe the main visible activity" in prompt
    assert "Do not use probabilistic phrases" in prompt


def test_prompt_requests_only_missing_metadata():
    prompt = build_caption_prompt(CaptionContext())

    assert "Location is missing" in prompt
    assert "Capture time is missing" in prompt


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(
            {"choices": [{"message": {"content": "  An evening ferry crosses the sea.  "}}]}
        ).encode("utf-8")


def test_openai_backend_sends_low_detail_image_and_normalizes_caption(tmp_path):
    image_path = tmp_path / "sheet.jpg"
    image_path.write_bytes(b"jpeg")
    backend = OpenAICompatibleVisionBackend(model="vision-model")

    with patch("sampled_captioner.captioner.urlopen", return_value=_FakeResponse()) as request:
        caption = backend.caption(str(image_path), "Caption this")

    assert caption == "An evening ferry crosses the sea."
    payload = json.loads(request.call_args.args[0].data.decode("utf-8"))
    image = payload["messages"][0]["content"][1]["image_url"]
    assert image["detail"] == "low"
    assert image["url"].startswith("data:image/jpeg;base64,")


@pytest.mark.parametrize("keep", [False, True])
@pytest.mark.parametrize("failure", [None, "sampling", "inference"])
def test_captioner_owns_contact_sheet_cleanup(tmp_path, monkeypatch, keep, failure):
    source, sheet, unrelated = (
        tmp_path / name for name in ("source.mp4", "sheet.jpg", "other.jpg")
    )
    source.write_bytes(b"source video")
    unrelated.write_bytes(b"unrelated image")

    def sample_video(**kwargs):
        Path(kwargs["output_path"]).write_bytes(b"generated jpeg")
        if failure == "sampling":
            raise ValueError("sampling failed after writing an image")
        return SampledContactSheet(str(source), str(sheet), (1.0,), 2.0, 176, 144, 0.1)

    def infer(image_path, prompt):
        assert Path(image_path).read_bytes() == b"generated jpeg"
        if failure == "inference":
            raise RuntimeError("inference failed")
        return "A mountain landscape."

    monkeypatch.setattr("sampled_captioner.captioner.create_contact_sheet", sample_video)
    captioner = SampledCaptioner(SimpleNamespace(model="vision", caption=infer))
    arguments = {
        "source_video_path": str(source),
        "contact_sheet_path": str(sheet),
    }
    if keep:
        arguments["keep_contact_sheet"] = True
    if failure:
        with pytest.raises(ValueError if failure == "sampling" else RuntimeError):
            captioner.caption_video(**arguments)
    else:
        result = captioner.caption_video(**arguments)
        assert isinstance(result, CaptionResult)
        assert result.caption == "A mountain landscape."
        assert result.sample.image_path == (str(sheet) if keep else None)
    assert sheet.exists() is keep
    assert source.read_bytes() == b"source video"
    assert unrelated.read_bytes() == b"unrelated image"


def test_captioner_never_deletes_or_overwrites_existing_images(tmp_path, monkeypatch):
    sheet = tmp_path / "existing.jpg"
    sheet.write_bytes(b"existing image")
    sampler, backend = Mock(), Mock()
    monkeypatch.setattr("sampled_captioner.captioner.create_contact_sheet", sampler)
    with pytest.raises(FileExistsError):
        SampledCaptioner(backend).caption_video("source.mp4", str(sheet))
    assert sheet.read_bytes() == b"existing image"
    sampler.assert_not_called()
    backend.caption.assert_not_called()
