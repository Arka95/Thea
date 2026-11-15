# Sampled Captioner

[Back to Thea](../../README.md) | [Developer guide](dev.readme.md)

Generates one evidence-grounded travel-video caption from a compact chronological
contact sheet. Captions are worded so downstream code can extract location,
time of day, activity, subjects, and visible content.

The package does **not** downscale complete videos. Pass Thea's existing
downscaled output as `sampling_video_path`; otherwise it samples the source and
resizes only the selected frames.

## CLI and MCP

```powershell
thea caption "D:\videos\clip.mp4" --model "your-local-vision-model" --location-in-metadata
```

The command prints the caption, model and contact-sheet metadata as JSON.
It persists the caption in `videos.description` in configured
`data_dir\video-index.sqlite3`; returned `db` and `content_hash` identify
the record. No separate caption JSON is automatically created.
Indexed country/state enrich the prompt, with an offline folder-name fallback
labelled approximate. Coordinates and explicit locale are not replaced by guesses.
Descriptions are generated drafts, not proof of visual accuracy.
The default endpoint is `http://localhost:1234/v1`; select another with
`--base-url`. Optional `--sampling-video` reuses a downscaled source.
`--contact-sheet` explicitly retains a new JPEG; otherwise a temporary JPEG under
configured `data_dir\captions` is deleted by the core captioner after inference,
including on failure. Cleaned results have `sample.image_path: null`.
Set `THEA_CAPTION_API_KEY` when needed, or use
`--api-key-env` to name another credential variable.

MCP tool `caption` accepts the same parameters with underscores instead of
hyphens. The model must already be served and support images; neither interface
downloads weights or starts a model. See the [complete CLI options](../../README.md#usage)
and [MCP contract](../mcp/README.md).

Passing a directory recursively captions its videos sequentially and returns
`selected`, `saved`, `complete`, per-video `results`, and `errors` containing
safe error types. Successful videos remain saved if another fails.
Existing descriptions survive inference failures; explicit contact-sheet and
sampling-video paths are single-file options only.
No automatic JPEG remains after an ordinary caption attempt.

## Python API

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

Activity is always requested. Location/time omission flags remain authoritative;
the CLI also omits time when the catalogue's `creation_time` is populated,
including its filesystem-created fallback.
The low-level injectable Python captioner does not perform catalogue writes;
that integration belongs to the CLI/MCP adapter.
The Python `SampledCaptioner.caption_video` method owns image cleanup itself,
independently of either interface. Pass `keep_contact_sheet=True` only when
retaining the intermediate image intentionally. Existing images are rejected,
not overwritten or deleted. Direct `create_contact_sheet` calls still create
their explicitly requested image output.

The configured LM Studio model must support image input. The existing text-only
Qwen 3 setup cannot caption contact sheets.
