"""Fast tests for sampled frame layout, prompting, and local vision requests."""

import json
import os
import sys
from unittest.mock import patch

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

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
