# Thea — GPU-Accelerated Video Stock-Footage Extractor

Thea identifies stable cinematic segments in video files using GPU-accelerated optical flow analysis, then extracts them as individual clips suitable for stock footage libraries.

**What qualifies as a good stock video clip:** A minimum of 3-5 seconds of footage without unusual stutters, irregular camera movement, or inconsistent panning.

---

## Quick Start

```bash
# Install dependencies (requires CUDA-enabled OpenCV — see docs/setup.md)
pip install -r requirements.txt

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

All commands support single-file mode (path to a video) or batch mode (path to a directory). All output goes to the resolved `data_dir` (see [Settings](#settings) below).

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
| `fast/` | 47 | ~2s | Config loader, hardware detection, motion assessment enum, settings, pipeline logger |
| `slow/` | 31 | ~18s | Optical flow, analyzer, downscaler, slicer, full pipeline |

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
| [setup.md](docs/setup.md) | Install CUDA toolkit, cuDNN, and OpenCV with GPU acceleration |
| [setup.localLLM.md](docs/setup.localLLM.md) | Configure IntelliJ with a local LLM (Ollama/Qwen) for AI-assisted development |
| [productionize.todo.md](docs/productionize.todo.md) | Roadmap to package Thea as a distributable offline .exe with installer |
