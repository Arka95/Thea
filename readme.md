# Thea — GPU-Accelerated Video Stock-Footage Extractor

Thea identifies stable cinematic segments in video files using GPU-accelerated optical flow analysis, then extracts them as individual clips suitable for stock footage libraries.

**What qualifies as a good stock video clip:** A minimum of 3-5 seconds of footage without unusual stutters, irregular camera movement, or inconsistent panning.

---

## Quick Start

```bash
# Complete docs/setup.md once, then activate the project environment
.\.venv\Scripts\Activate.ps1

# Process a single video (full pipeline: downscale + analyze + slice)
python main.py pipeline sample.MP4

# Analyze motion only (no slicing)
python main.py analyze sample.MP4

# Batch process a directory
python main.py pipeline ./my_videos/

# Use a specific preset
python main.py pipeline sample.MP4 --preset strict

# List available presets
python main.py presets

# Downscale videos (custom width, lossless option)
python main.py downscale sample.MP4 --width 640
python main.py downscale ./raw_videos/ --width 640 --lossless
```

---

## Video Indexing

Index source videos without altering them, including offline country lookup and
clearly labelled folder-inferred locations:

```powershell
python -m tools.walkdir "E:\2026 USA" --db "E:\Thea\video_index_2026.sqlite3" --geocode --infer-loc
```

`--db` persists the catalogue across runs; without it, storage remains temporary
and in-memory. The optional positional `LIMIT` still works. `--geocode` and
`--infer-loc` enable metadata probing automatically; `--probe` enables probing
alone. Zero-coordinate placeholders, out-of-range GPS and malformed location
tags are ignored, allowing folder inference when available. Valid embedded GPS
takes precedence over inferred locations. Records are deduplicated by content
hash, so duplicate copies retain one catalogue path.
Offline country lookup uses nearest-city data, so results near borders and
folder-inferred locations are approximate.

---

## Video Merging

Merge an ordered list of compatible clips without re-encoding:

```powershell
python main.py merge clip1.mp4 clip2.mp4 --output-path "E:\Thea\merged\trip.mp4"
python main.py merge --manifest "E:\Thea\clips.txt" --output-path "E:\Thea\merged\trip.mp4"
```

The manifest is UTF-8 text with one video path per line, in playback order.
Relative paths are resolved beside the manifest. There is no clip-count cap;
use manifests for large selections to avoid command-line length limits.

The Python API is `merger.merge_videos(video_paths, output_path)`.
Keep catalogue selection in `VideoSearch` or `IStore.query()`; pass the resulting
ordered paths to the merger. To order a catalogue selection by recording time,
use `order_by="creation_time"`.

The command defaults to `<resolved data_dir>\merged\merge_<timestamp>.mp4`;
`--output-path` overrides that location without using the configured data directory.
Inputs and existing outputs are never overwritten. All compatible streams,
including audio, are copied. Stream compatibility is checked first; differing
codecs, dimensions, audio layouts or time bases fail rather than silently
re-encode. Output is checked before publishing, and temporary files are cleaned
up on failure.

---

## Cropping and Panning

Python APIs use FFmpeg conventions: **width before height**, with crop and pan
coordinates specifying the rectangle's **top-left** in the displayed source.

```python
from src.cropandpan import crop, centercrop, ratiocrop, pan

crop("clip.mp4", 1000, 600, 100, 200, output_path=r"E:\Thea\cropandpan\crop.mp4")
centercrop("clip.mp4", 1080, 1080, output_path=r"E:\Thea\cropandpan\square.mp4")
ratiocrop("clip.mp4", 9, 16, output_path=r"E:\Thea\cropandpan\portrait.mp4")
pan("clip.mp4", duration=5, output_path=r"E:\Thea\cropandpan\pan.mp4")
```

Default pan: largest fitting 9:16 rectangle across the frame over the source
duration. Explicit endpoints support reverse, vertical and diagonal movement.
A shorter pan trims the output, not playback speed; longer-than-source
durations fail. Video is re-encoded with its original codec/pixel format and
audio is copied. Invalid/out-of-bounds rectangles fail before encoding.
No-op transformations return the original path. Otherwise output defaults to
`<resolved data_dir>\cropandpan`; `output_path` overrides it. Originals and
existing outputs are never overwritten.

| Document | Dev guide | Purpose |
|----------|-----------|---------|
| [Crop and pan](docs/cropandpan/README.md) | [Development](docs/cropandpan/dev.readme.md) | API signatures, coordinates, ratio fitting, encoding and output behavior |

---

## Architecture

```
Thea/
├── main.py                         Unified CLI (entry point)
├── config/
│   ├── presets/                     Configuration preset JSON files
│   │   ├── cinematic.json          Default: balanced stock footage extraction
│   │   ├── strict.json             Very tight: only static/slider shots
│   │   ├── permissive.json         Loose: includes stabilized handheld
│   │   └── action.json             Maximum extraction
│   └── settings/
│       ├── settings.json           Global pipeline settings (data_dir, flags)
│       └── supported_codecs.txt    List of validated video codecs
├── motion_assessment/              Core analysis engine
│   ├── optical_flow.py             GPU/CPU flow calculators (Farneback)
│   ├── analyzer.py                 Motion scoring + window detection
│   └── assessment.py               MotionAssessment enum (7 categories)
├── downscaler/
│   └── downscaler.py               Single + batch video downscaling
├── slicer/
│   └── slicer.py                   Lossless slicing (FFmpeg) or re-encode (OpenCV)
├── merger/
│   └── merger.py                   Ordered FFmpeg stream-copy concatenation
├── src/
│   └── cropandpan/                 Validated FFmpeg cropping and linear panning APIs
├── utils/
│   ├── config_loader.py            Preset discovery, loading, validation
│   ├── settings.py                 Global settings, data directory resolution
│   ├── pipeline_logger.py          CSV logging (video_meta, pipeline_stats)
│   ├── hardware.py                 Hardware profiling (CPU/GPU/RAM)
│   ├── video_io.py                 Video discovery + metadata extraction
│   ├── validations.py              Video file + metadata validation
│   └── metrics.py                  Execution metrics (@track decorator)
└── tests/
    ├── fast/                       Unit tests (~2s, no video I/O)
    ├── slow/                       Integration tests (~18s, uses sample.mp4)
    └── sample.mp4                  640x360 test video (tracked in git)
```

### Component Details

#### `main.py` — CLI Entry Point

The unified command-line interface dispatching to all Thea capabilities. Handles argument parsing, config loading, error handling, and metrics reporting.

| Subcommand | Description |
|------------|-------------|
| `pipeline` | Full pipeline: downscale + analyze + slice (most common) |
| `analyze` | Motion analysis only — outputs metadata JSON and/or CSV |
| `slice` | Analyze + slice (no downscaling step) |
| `downscale` | Downscale videos to a target width |
| `presets` | List available configuration presets |
| `merge` | Join ordered video paths or a manifest using FFmpeg stream copy |

Processing commands accept a video file or directory. `merge` accepts ordered
video paths or a manifest. Output follows the resolved `data_dir` (see
[Settings](#settings)); `merge --output-path` overrides the output file.

#### `motion_assessment/` — Core Analysis Engine

| File | Purpose |
|------|---------|
| `optical_flow.py` | Factory pattern producing GPU (`cv2.cuda.FarnebackOpticalFlow`) or CPU flow calculators. GPU calculator reuses `GpuMat` objects across frames to avoid allocation overhead. |
| `analyzer.py` | `compute_motion_scores()` — processes all frames, returns per-frame motion magnitudes. `detect_stable_windows()` — 3-pass algorithm: find raw stable spans, merge nearby spans, filter by minimum duration. |
| `assessment.py` | `MotionAssessment` enum classifying motion into 7 categories (STATIC through CUT) with score ranges and stock-footage grade flags. |

**Pipeline flow:**
```
Video frames --> Grayscale --> Downscale --> Optical Flow --> Motion Magnitude
    --> Gaussian Smoothing --> Threshold --> Raw Windows --> Merge --> Filter
```

#### `downscaler/` — Video Downscaling

Prepares videos for efficient analysis. Preserves FPS and aspect ratio while reducing resolution to a target width (default 320px). Batch mode uses hardware-aware parallelization.

| Flag | Effect |
|------|--------|
| `--width N` | Target width in pixels (default: 320) |
| `--lossless` | FFV1 codec + LANCZOS4 interpolation (.avi output) |

Default (no flags) uses `INTER_AREA` interpolation + lossy `mp4v` codec — optimized for analysis consumption (small files, fast I/O).

#### `slicer/` — Video Extraction

Takes detected stable windows and extracts individual clips. Two modes controlled by `settings.json`:

| `reencode` | Method | Speed | Quality |
|------------|--------|-------|---------|
| `false` (default) | FFmpeg stream copy (`-c copy`) | **~6x faster** | Lossless — identical to source |
| `true` | OpenCV `VideoWriter` | Slower | Re-encodes with `config.output.codec` |

#### `utils/` — Shared Utilities

| File | Purpose |
|------|---------|
| `config_loader.py` | Scans `config/presets/*.json`, validates all parameters against schema, supports custom JSON files via `--config` flag. |
| `settings.py` | Loads `settings.json`, resolves `data_dir` from source path, provides path helpers for subdirectories. All directory structure constants defined here. |
| `pipeline_logger.py` | Appends per-video results to `video_meta.csv` and per-run timing to `pipeline_stats.csv` in `data_dir`. Gated by `data_collection` setting. |
| `hardware.py` | `HardwareProfile` detection: CPU cores, RAM, GPU presence/VRAM, recommended worker count for parallel processing. |
| `video_io.py` | `discover_videos()` finds all valid video files in a directory; `get_video_info()` extracts resolution, FPS, frame count, codec. |
| `validations.py` | `validate_video_file()` — checks file existence, readability, codec support. `validate_motion_metadata()` — post-processing validation (designed for future use). |
| `metrics.py` | `@track` decorator for execution timing. Thread-safe `MetricsCollector` aggregates per-function stats. Printed as a summary table at the end of each command. |

#### `config/presets/` — Configuration Presets

Presets are JSON files discovered by filename stem. The active preset defines all tunable parameters:

- **Optical flow algorithm and parameters** (Farneback: pyramid levels, window size, iterations, etc.)
- **Motion threshold** for stable/unstable classification
- **Window detection** rules (minimum duration, merge gap)
- **Output** settings (codec for re-encode mode, metadata toggle)
- **GPU** preferences (enabled, device ID)

#### `tests/` — Test Suite

| Folder | Tests | Runtime | Coverage |
|--------|-------|---------|----------|
| `tests/fast/` | 47 | ~2s | Config loader, hardware detection, motion assessment enum, settings, pipeline logger |
| `tests/slow/` | 31 | ~18s | Optical flow, analyzer, downscaler, slicer, full pipeline |
| `tools/tests/` | 100 | ~20s | Storage, metadata, geocoding, search, and directory walking |

Reference outputs in `tests/slow/reference_sample.json` ensure reproducible results across changes.

---

## Settings

Global pipeline settings live in `config/settings/settings.json`:

```json
{
  "data_dir": "",
  "data_collection": false,
  "reencode": false
}
```

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `data_dir` | string | `""` | Root directory for all pipeline output. If empty, resolves automatically from the video source path (see below). |
| `data_collection` | bool | `false` | When `true`, appends results to `video_meta.csv` and `pipeline_stats.csv` in `data_dir`. |
| `reencode` | bool | `false` | When `false`, slicing uses FFmpeg stream copy (lossless, fast). When `true`, re-encodes with OpenCV using `output.codec` from the active preset. |

### Data Directory Resolution

When `data_dir` is empty (`""`), Thea resolves it from the source path:

| Input | Resolved `data_dir` |
|-------|---------------------|
| `python main.py pipeline sample.mp4` | `./Thea/` (parent of file + `/Thea`) |
| `python main.py pipeline ./videos/` | `./videos/Thea/` (source dir + `/Thea`) |
| `data_dir: "D:/Thea"` in settings | `D:/Thea/` (used as-is) |

### Data Directory Structure

```
data_dir/
├── downsampled/        Downscaled videos (cached, skipped on re-runs)
├── sliced/             Extracted stable clips
├── video_meta.csv      Per-video motion assessment results (if data_collection=true)
├── pipeline_stats.csv  Per-run timing stats (if data_collection=true)
└── {video}_metadata.json   Per-video metadata (video info + motion stats + windows)
```

### Pipeline Stats CSV

Logged per pipeline run when `data_collection: true`:

| Column | Description |
|--------|-------------|
| `video_path` | Source video file |
| `video_duration_sec` | Video length |
| `downscaler_time_sec` | Time spent downscaling (0 if cached) |
| `motion_assessment_time_sec` | Optical flow + window detection time |
| `slicing_time_sec` | Time to extract clips |
| `total_time_sec` | Total pipeline wall clock |
| `timestamp` | ISO 8601 run timestamp |

### Video Metadata CSV

Logged per video when `data_collection: true`:

| Column | Description |
|--------|-------------|
| `video_name` | Filename |
| `video_path` | Full path |
| `video_duration_sec` | Length in seconds |
| `resolution` | e.g. `640x360` |
| `fps` | Frames per second |
| `good_window_slices` | JSON array of `[start, end]` pairs |
| `overall_assessment` | Motion category (static/stable/etc.) |
| `mean_motion` / `max_motion` | Motion score statistics |
| `optical_flow_config` | Flow algorithm parameters used |

---

## Configuration Guide

### Configuration Parameters

| Section | Parameter | Type | Default | Description |
|---------|-----------|------|---------|-------------|
| `analysis` | `max_width` | int | 320 | Downscale width for motion analysis. Lower = faster but less precise. Higher (640+) detects finer motion but slower. |
| `analysis` | `motion_smoothing_sigma` | float | 5 | Temporal Gaussian smoothing of motion scores. Higher = smoother curve, less sensitive to single-frame spikes. |
| `optical_flow` | `algorithm` | string | "farneback" | Optical flow algorithm. Currently supported: `farneback`. |
| `optical_flow.farneback` | `pyr_scale` | float | 0.5 | Pyramid scale (0-1). 0.5 is standard. |
| `optical_flow.farneback` | `levels` | int | 5 | Pyramid levels. More = handles larger motion. 3-5 for cinematic. |
| `optical_flow.farneback` | `winsize` | int | 21 | Averaging window size. Larger = smoother flow, better for global camera motion. |
| `optical_flow.farneback` | `iterations` | int | 5 | Solver iterations per level. More = more accurate but slower. |
| `optical_flow.farneback` | `poly_n` | int | 7 | Polynomial expansion neighborhood. 5 = faster, 7 = smoother. |
| `optical_flow.farneback` | `poly_sigma` | float | 1.5 | Gaussian std for polynomial expansion. 1.2 for poly_n=5, 1.5 for poly_n=7. |
| `optical_flow.farneback` | `flags` | int | 0 | OpenCV flags. 256 = OPTFLOW_FARNEBACK_GAUSSIAN for Gaussian window. |
| `window_detection` | `motion_threshold` | float | 0.5 | **Key parameter.** Max motion score for a frame to be "stable". |
| `window_detection` | `min_duration_sec` | float | 3.0 | Minimum clip duration. Shorter windows discarded. |
| `window_detection` | `merge_gap_sec` | float | 1.0 | Merge stable windows separated by <= this many seconds. |
| `output` | `codec` | string | "mp4v" | FourCC codec for re-encode mode (`reencode: true`). Ignored when using FFmpeg stream copy. |
| `output` | `write_metadata` | bool | true | Write `_metadata.json` with video info and motion analysis results. |
| `gpu` | `enabled` | bool | true | Use CUDA GPU for optical flow. Falls back to CPU if unavailable. |
| `gpu` | `device_id` | int | 0 | GPU device index (multi-GPU systems). |

### Motion Assessment Categories

Motion scores are **mean pixel displacement at analysis resolution** (default 320px width):

| Category | Score Range | Description | Stock Footage? |
|----------|-------------|-------------|----------------|
| `static` | 0.00 - 0.05 | Tripod/locked camera, no visible motion | Yes |
| `very_stable` | 0.05 - 0.20 | Slow dolly, slider, or imperceptible drift | Yes |
| `stable` | 0.20 - 0.50 | Smooth pan/tilt or gentle tracking shot | Yes |
| `moderate` | 0.50 - 1.00 | Fast pan, stabilized handheld | Borderline |
| `unstable` | 1.00 - 2.00 | Jerky handheld, whip pan, irregular motion | No |
| `very_unstable` | 2.00 - 5.00 | Extreme shake, rapid direction change | No |
| `cut` | 5.00+ | Scene cut, flash, or abrupt transition | No |

### Preset Selection Guide

| Preset | Threshold | Best For | Expected Result |
|--------|-----------|----------|-----------------|
| **cinematic** (default) | 0.50 | Stock footage, film clips, smooth camera | Pans/tilts included, handheld excluded |
| **strict** | 0.20 | Static b-roll, timelapse base plates | Only locked-off/slider shots |
| **permissive** | 1.00 | Vlogs, stabilized action | Most motion passes except jerky |
| **action** | 2.00 | Maximum extraction, minimal filtering | Nearly everything except cuts |

### Example Custom Configurations

**Slow cinematic drone footage:**
```json
{
  "window_detection": { "motion_threshold": 0.30, "min_duration_sec": 8.0, "merge_gap_sec": 2.0 },
  "optical_flow": { "farneback": { "winsize": 31, "levels": 5, "iterations": 7 } }
}
```

**Handheld interview/vlog:**
```json
{
  "window_detection": { "motion_threshold": 1.5, "min_duration_sec": 3.0, "merge_gap_sec": 0.5 },
  "optical_flow": { "farneback": { "winsize": 15, "levels": 3, "iterations": 3 } }
}
```

**4K sports footage:**
```json
{
  "window_detection": { "motion_threshold": 2.0, "min_duration_sec": 2.0, "merge_gap_sec": 0.3 },
  "analysis": { "max_width": 480 },
  "optical_flow": { "farneback": { "winsize": 11, "levels": 3, "iterations": 3 } }
}
```

---

## Execution Metrics

Every pipeline run collects per-function timing metrics, printed as a summary table at the end of each command:

```
EXECUTION METRICS
Function                        Calls  Total(s)   Avg(ms)   Min(ms)   Max(ms)  Errors
-------------------------------------------------------------------------------------
downscale_video                     1     0.349    348.77    348.77    348.77       0
compute_motion_scores               1     1.734   1734.16   1734.16   1734.16       0
detect_stable_windows               1     0.000      0.26      0.26      0.26       0
slice_video                         1     0.186    186.00    186.00    186.00       0
-------------------------------------------------------------------------------------
Total: 4 calls, 2.270s, 0 errors
```

---

## Output Files

All output is written to the resolved `data_dir` (see [Settings](#settings)):

| File | Location | Contents |
|------|----------|----------|
| `{video}.mp4` | `data_dir/downsampled/` | Downscaled video (cached for re-runs) |
| `{video}_N.mp4` | `data_dir/sliced/` | Extracted stable clips (lossless by default) |
| `{video}_metadata.json` | `data_dir/` | Video info, motion stats, windows detected |
| `video_meta.csv` | `data_dir/` | Per-video assessment results (if `data_collection: true`) |
| `pipeline_stats.csv` | `data_dir/` | Per-run timing stats (if `data_collection: true`) |
| `{dir}_features.csv` | `data_dir/` | Batch analyze output (per-video features table) |
| `{dir}_features.pkl` | `data_dir/` | Batch analyze output (full features + per-frame scores) |

---

## Performance

Benchmarked on RTX 4070 SUPER + Intel Core (10 physical cores), 640x360 test video:

| Operation | Speed |
|-----------|-------|
| GPU optical flow (320x180) | ~3 ms/frame |
| Motion assessment (574 frames) | ~1.7s |
| FFmpeg lossless slice (3 clips) | ~0.19s |
| OpenCV re-encode slice (3 clips) | ~1.1s (6x slower) |
| Full pipeline (19s video) | ~2.3s |

---

## Documentation Index

| File | Description |
|------|-------------|
| [setup.md](docs/setup.md) | Main sequenced setup and project-local Python environment |
| [setup.gpu.md](docs/setup.gpu.md) | Configure FFmpeg, NVIDIA CUDA/cuDNN, and CPU versus GPU OpenCV |
| [setup.local-llm-mcp.md](docs/setup.local-llm-mcp.md) | Configure VS Code, LM Studio or Ollama with Qwen 3, and Thea's MCP client |
| [video_creator.md](docs/video_creator.md) | LTX-Video 2 + ComfyUI setup for local AI video generation (720p, RTX 4070 SUPER) |
| [cline-custom-instructions.md](docs/cline-custom-instructions.md) | Agent behavior instructions (paste into Cline Custom Instructions) |
| [productionize.todo.md](docs/productionize.todo.md) | Roadmap to package Thea as a distributable offline .exe with installer |

How Agents Discover and Use Everything

## Agent's Discovery Flow

```
Agent starts working in Thea/
    ↓
1. Read .instructions.md (THIS FILE) ← Comprehensive guide
    ↓
2. Check .vscode/skills/ ← Find available skills
    ↓
3. Read .vscode/tasks.json ← Find executable tasks
    ↓
4. Check .vscode/launch.json ← Find debug configs
    ↓
5. Check .vscode/prompts/ ← Find slash commands
    ↓
6. Read .vscode/settings.json ← Load workspace config
    ↓
Agent now fully understands available capabilities
```