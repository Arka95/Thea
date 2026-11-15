# Sampled Captioner

Generates one evidence-grounded travel-video caption from a compact chronological
contact sheet. Captions are worded so downstream code can extract location,
time of day, activity, subjects, and visible content.

The package does **not** downscale complete videos. Pass Thea's existing
downscaled output as `sampling_video_path`; otherwise it samples the source and
resizes only the selected frames.

```python
from sampled_captioner import (
    CaptionContext,
    OpenAICompatibleVisionBackend,
    SampledCaptioner,
)

backend = OpenAICompatibleVisionBackend(
    model="your-local-vision-model",
    base_url="http://localhost:1234/v1",
)
captioner = SampledCaptioner(backend)

result = captioner.caption_video(
    source_video_path=r"D:\videos\clip.mp4",
    sampling_video_path=r"D:\videos\Thea\downscaled\clip.mp4",
    contact_sheet_path=r"D:\videos\Thea\captions\clip.jpg",
    context=CaptionContext(
        location_in_metadata=True,
        timestamp_in_metadata=True,
    ),
)
print(result.caption)
```

Activity is always captioned. Location and time of day are included only when
those values are missing from the video's coordinates and metadata.

The configured LM Studio model must support image input. The existing text-only
Qwen 3 setup cannot caption contact sheets.
