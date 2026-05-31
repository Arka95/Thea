# Thea — GPU-Accelerated Video Stock-Footage Extractor

Thea identifies stable cinematic segments in video files using GPU-accelerated optical flow analysis, then extracts them as individual clips suitable for stock footage libraries.

**What qualifies as a good stock video clip:** A minimum of 3-5 seconds of footage without unusual stutters, irregular camera movement, or inconsistent panning.

---

## Quick Start

```bash
# Install dependencies (requires CUDA-enabled OpenCV — see setup.md)
pip install -r requirements.txt

# Process a single video (full pipeline: analyze + slice)
python main.py pipeline sample.MP4

# Analyze motion only (no slicing)
python main.py analyze sample.MP4

# Batch process a directory
python main.py pipeline ./my_videos/

# Use a specific preset
python main.py pipeline sample.MP4 --preset strict

# List available presets
python main.py presets

# Downscale videos for faster analysis
python main.py downscale ./raw_videos/ --output ./downscaled/
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
│       └── supported_codecs.txt    List of validated video codecs
├── motion_assessment/              Core analysis engine
│   ├── optical_flow.py             GPU/CPU flow calculators (Farneback)
│   ├── analyzer.py                 Motion scoring + window detection
│   └── assessment.py               MotionAssessment enum (7 categories)
├── downscaler/
│   └── downscaler.py               Single + batch video downscaling
├── slicer/
│   └── slicer.py                   Video slicing (extract windows to clips)
├── utils/
│   ├── config_loader.py            Preset discovery, loading, validation
│   ├── hardware.py                 Hardware profiling (CPU/GPU/RAM)
│   ├── video_io.py                 Video discovery + metadata extraction
│   ├── validations.py              Video file + metadata validation
│   └── metrics.py                  Execution metrics (@track decorator)
└── tests/
    ├── fast/                       Unit tests (~2s, no video I/O)
    └── slow/                       Integration tests (~6min, uses sample.MP4)
```

### Component Details

#### `main.py` — CLI Entry Point

The unified command-line interface dispatching to all Thea capabilities. Handles argument parsing, config loading, error handling, and metrics reporting.

| Subcommand | Description |
|------------|-------------|
| `pipeline` | Full analysis + slicing (most common) |
| `analyze` | Motion analysis only — outputs metadata JSON and/or CSV |
| `slice` | Slice video given pre-computed windows |
| `downscale` | Downscale videos to analysis-optimized resolution |
| `presets` | List available configuration presets |

Supports single-file mode (path to a video) or batch mode (path to a directory) for all commands.

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

Prepares videos for efficient analysis. Preserves FPS and aspect ratio while reducing resolution to analysis width (default 320px). Batch mode uses hardware-aware parallelization.

#### `slicer/` — Video Extraction

Takes detected stable windows and writes individual video clips to an output directory. Preserves original quality — reads from source at full resolution, writes with configurable codec.

#### `utils/` — Shared Utilities

| File | Purpose |
|------|---------|
| `config_loader.py` | Scans `config/presets/*.json`, validates all parameters against schema, supports custom JSON files via `--config` flag. |
| `hardware.py` | `HardwareProfile` detection: CPU cores, RAM, GPU presence/VRAM, recommended worker count for parallel processing. |
| `video_io.py` | `discover_videos()` finds all valid video files in a directory; `get_video_info()` extracts resolution, FPS, frame count, codec. |
| `validations.py` | `validate_video_file()` — checks file existence, readability, codec support. `validate_motion_metadata()` — post-processing validation of extracted results (designed for future pipeline integration). |
| `metrics.py` | `@track` decorator for execution timing. Thread-safe `MetricsCollector` aggregates per-function stats. Metrics are embedded in `_metadata.json` output and printed as a table at pipeline end. |

#### `config/presets/` — Configuration System

Presets are JSON files discovered by filename stem. The active preset defines all tunable parameters:

- **Optical flow algorithm and parameters** (Farneback: pyramid levels, window size, iterations, etc.)
- **Motion threshold** for stable/unstable classification
- **Window detection** rules (minimum duration, merge gap)
- **Output** settings (codec, metadata toggle)
- **GPU** preferences (enabled, device ID)

#### `tests/` — Test Suite

| Folder | Tests | Runtime | Coverage |
|--------|-------|---------|----------|
| `fast/` | 30 | ~2s | Config loader, hardware detection, motion assessment enum |
| `slow/` | 31 | ~6.5min | Optical flow, analyzer, downscaler, slicer, full pipeline |

Reference outputs in `tests/slow/reference_sample.json` ensure reproducible results across changes.

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
| `output` | `codec` | string | "mp4v" | FourCC codec. `mp4v` = MPEG-4, `avc1` = H.264 (if available). |
| `output` | `write_metadata` | bool | true | Write `_metadata.json` with full processing details. |
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

Every pipeline run collects per-function timing metrics. These are:
- Printed as a summary table at the end of each command
- Embedded in the `metrics` field of `_metadata.json`

Example output:
```
EXECUTION METRICS
Function                        Calls  Total(s)   Avg(ms)   Min(ms)   Max(ms)  Errors
-------------------------------------------------------------------------------------
compute_motion_scores               1    26.865  26864.56  26864.56  26864.56       0
detect_stable_windows               1     0.001      0.58      0.58      0.58       0
slice_video                         1    44.443  44442.59  44442.59  44442.59       0
-------------------------------------------------------------------------------------
Total: 3 calls, 71.308s, 0 errors
```

---

## Output Files

| File | When | Contents |
|------|------|----------|
| `{video}_sliced/{video}_N.mp4` | Windows detected | Extracted stable clips (original quality) |
| `{video}_metadata.json` | `write_metadata: true` | Config, motion stats, windows, assessment, metrics |
| `{dir}_features.csv` | Batch + `--output csv` | Per-video features table |
| `{dir}_features.pkl` | Batch + `--output pkl` | Full features + per-frame scores |

---

## Performance

Benchmarked on RTX 4070 SUPER + Intel Core (10 physical cores):

| Operation | Speed |
|-----------|-------|
| GPU optical flow (320x180) | ~8.4 ms/frame (~120 fps analysis) |
| Full pipeline (4K 19s video) | ~71s (analyze 27s + slice 44s) |
| Batch 4 videos parallel | ~45s total (4 workers) |

---

## Documentation Index

| File | Description |
|------|-------------|
| [setup.md](setup.md) | Install CUDA toolkit, cuDNN, and OpenCV with GPU acceleration |
| [setup.localLLM.md](setup.localLLM.md) | Configure IntelliJ with a local LLM (Ollama/Qwen) for AI-assisted development |
| [productionize.todo.md](productionize.todo.md) | Roadmap to package Thea as a distributable offline .exe with installer |
