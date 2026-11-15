# Crop and pan development

[Thea README](../../readme.md) | [Usage](README.md)

## Ownership and dependencies

`src\cropandpan` owns frame geometry, ratio fitting, linear crop expressions and
the four public Python APIs. New source is under `src`; existing root-level
modules are not relocated.
Reuse `tools.video_meta_strategy.run_ffprobe`, `utils.ffmpeg.get_ffmpeg_exe`,
`utils.settings` data-directory resolution and `utils.metrics.track`.
No new dependency, GPU detection or background service is required.

## Processing

Probe the first non-cover-art video, apply right-angle display rotation to its
geometry, and validate both endpoint rectangles before starting FFmpeg.
The straight path between in-bounds endpoints stays in bounds.
Exact ratio fitting uses rational arithmetic and chroma-aligned dimensions;
sample aspect ratio is inverted for quarter-turn autorotation.
`crop:exact=1` prevents silent chroma-position rounding.

FFmpeg uses a common timestamp-origin shift (`-copyts -start_at_zero`), preserves
frame timestamps (`-fps_mode passthrough`) and copies audio. Pan expressions
subtract the video's start offset relative to the container; output-side `-ss`
removes any audio-only lead-in so the pan starts at the first video frame.
They do not rescale timestamps or force a frame rate. `-t` limits output duration.

The source codec selects the encoder; `-pix_fmt +<source format>` disables silent
pixel-format conversion. The output probe verifies dimensions, codec, pixel
format, audio stream signatures and duration within frame/packet tolerance.
Source file identity, size and modification time are checked before publication.
Exclusive destination reservation prevents replacing an existing destination;
temporary results are cleaned up on errors. No-op transformations return the
source before data-directory resolution or encoding.

## Validation

Run the existing fast runner, with probes and FFmpeg replaced by fakes:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\fast\test_cropandpan.py tests\fast\test_merger.py tests\fast\test_settings.py -q --tb=short
.\.venv\Scripts\python.exe -m ruff check src\cropandpan tests\fast\test_cropandpan.py
.\.venv\Scripts\python.exe -m black --check --line-length 100 src\cropandpan tests\fast\test_cropandpan.py
```

Tests cover geometry/bounds, exact ratios and no-ops, rotations and sample aspect
ratio, default/reverse/vertical/diagonal pans, duration errors, original codec/
audio/timestamp commands, output validation and safe failure cleanup.
Real-media encoding is a separate, explicitly opted-in integration check.

## FFmpeg references

- [Crop filter](https://ffmpeg.org/ffmpeg-filters.html#crop)
- [Encoding, timestamps, autorotation and duration](https://ffmpeg.org/ffmpeg.html)
- [Codec encoders](https://ffmpeg.org/ffmpeg-codecs.html)
