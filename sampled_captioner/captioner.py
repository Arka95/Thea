"""Caption sampled video contact sheets through an injectable vision backend."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sampled_captioner.sampler import SampledContactSheet, create_contact_sheet


@dataclass(frozen=True)
class CaptionContext:
    location_in_metadata: bool = False
    timestamp_in_metadata: bool = False
    additional_context: str | None = None


@dataclass(frozen=True)
class CaptionResult:
    source_video_path: str
    caption: str
    sample: SampledContactSheet
    model: str


class VisionCaptionBackend(Protocol):
    model: str

    def caption(self, image_path: str, prompt: str) -> str:
        ...


def build_caption_prompt(context: CaptionContext | None = None) -> str:
    """Build a strict one-sentence prompt suitable for downstream extraction."""
    context = context or CaptionContext()
    requirements = ["Always describe the main visible activity and subject."]
    if context.location_in_metadata:
        requirements.append("Location already exists in metadata; do not mention location.")
    else:
        requirements.append(
            "Location is missing; include the most specific visually supported location."
        )
    if context.timestamp_in_metadata:
        requirements.append("Capture time already exists in metadata; do not mention time of day.")
    else:
        requirements.append("Capture time is missing; include the visually supported time of day.")
    if context.additional_context:
        requirements.append(f"Additional trusted context: {context.additional_context}")

    requirement_block = "\n".join(f"- {requirement}" for requirement in requirements)
    return (
        "Caption this travel video from its chronological contact sheet. Return exactly one "
        "short, definitive, natural sentence containing only the requested missing metadata "
        "and visible activity.\n"
        f"{requirement_block}\n"
        "Do not use probabilistic phrases such as 'appears to be', 'likely', or 'possibly'. "
        "When a named place is not visually supported, use a definitive generic setting such "
        "as 'a beach', 'a city street', or 'an airport' instead of guessing. Do not invent "
        "events between samples, mention filenames, or output labels, JSON, or bullets."
    )


class OpenAICompatibleVisionBackend:
    """Call a local OpenAI-compatible multimodal endpoint such as LM Studio."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:1234/v1",
        api_key: str | None = None,
        timeout_sec: int = 120,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_sec = timeout_sec

    def caption(self, image_path: str, prompt: str) -> str:
        with open(image_path, "rb") as image:
            encoded_image = base64.b64encode(image.read()).decode("ascii")

        payload = {
            "model": self.model,
            "temperature": 0.1,
            "max_tokens": 120,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_sec) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Caption endpoint returned HTTP {error.code}: {detail}") from error
        except URLError as error:
            raise RuntimeError(f"Cannot reach caption endpoint: {error.reason}") from error

        try:
            caption = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError("Caption endpoint returned an invalid response") from error

        normalized = " ".join(str(caption).split())
        if not normalized:
            raise ValueError("Caption endpoint returned an empty caption")
        return normalized


# TODO: Add a Florence-2-large local backend for lightweight offline captioning.
class SampledCaptioner:
    """Sample a video and ask a configured vision backend for one caption."""

    def __init__(
        self,
        backend: VisionCaptionBackend,
        sample_count: int = 12,
        frame_width: int = 176,
        frame_height: int = 144,
        columns: int = 4,
    ) -> None:
        self.backend = backend
        self.sample_count = sample_count
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.columns = columns

    def caption_video(
        self,
        source_video_path: str,
        contact_sheet_path: str,
        context: CaptionContext | None = None,
        sampling_video_path: str | None = None,
    ) -> CaptionResult:
        """Caption a source video, optionally sampling Thea's downscaled copy."""
        sample = create_contact_sheet(
            video_path=sampling_video_path or source_video_path,
            output_path=contact_sheet_path,
            sample_count=self.sample_count,
            frame_width=self.frame_width,
            frame_height=self.frame_height,
            columns=self.columns,
        )
        caption = self.backend.caption(sample.image_path, build_caption_prompt(context))
        return CaptionResult(
            source_video_path=source_video_path,
            caption=caption,
            sample=sample,
            model=self.backend.model,
        )
