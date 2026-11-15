"""Sample representative video frames and generate one evidence-grounded caption."""

from sampled_captioner.captioner import (
    CaptionContext,
    CaptionResult,
    OpenAICompatibleVisionBackend,
    SampledCaptioner,
    build_caption_prompt,
)
from sampled_captioner.sampler import SampledContactSheet, create_contact_sheet

__all__ = [
    "CaptionContext",
    "CaptionResult",
    "OpenAICompatibleVisionBackend",
    "SampledCaptioner",
    "SampledContactSheet",
    "build_caption_prompt",
    "create_contact_sheet",
]
