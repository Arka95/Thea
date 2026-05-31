This tool helps extract stock-footage grade cinematics from videos by:

What is a good stock video window slice:

a minimum of 5 seconds footage without any unusual stutters, irregular camera movement, disruptive or inconsistent panning.


1. extracting a time based start and end window  of stable shots based on optical flow. There can be multiple such windows
2. each extracted window-slice of video is then trimmed and stored as a separate video with the name {original_video_name}_{slice_number}.{extension} . The sliced video should have the same encoding/quality as the original
3. all sliced videos would be in a folder {original_video_name}_sliced in the root directory

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Process a single video (uses config.json)
python video_slicer.py sample.MP4

# Batch process a directory
python batch_extract.py ./my_videos --output csv
```

---

## Configuration Guide

All settings are in `config.json`. Edit this file to tune extraction behavior for your footage type.

### Configuration Parameters

| Section | Parameter | Type | Default | Description |
|---------|-----------|------|---------|-------------|
| `analysis` | `max_width` | int | 320 | Downscale width for motion analysis. Lower = faster but less precise. Higher (640+) detects finer motion but slower. |
| `analysis` | `motion_smoothing_sigma` | float | 5 | Temporal Gaussian smoothing of motion scores. Higher = smoother curve, less sensitive to single-frame spikes. Lower = more responsive. |
| `optical_flow` | `algorithm` | string | "farneback" | Optical flow algorithm. Currently supported: `farneback`. |
| `optical_flow.farneback` | `pyr_scale` | float | 0.5 | Pyramid scale (0-1). Lower = finer detail at each level. 0.5 is standard. |
| `optical_flow.farneback` | `levels` | int | 5 | Pyramid levels. More levels = handles larger motion between frames. 3-5 for cinematic. |
| `optical_flow.farneback` | `winsize` | int | 21 | Averaging window size. Larger = smoother flow, better for global camera motion. Smaller = more local detail. |
| `optical_flow.farneback` | `iterations` | int | 5 | Solver iterations per pyramid level. More = more accurate but slower. |
| `optical_flow.farneback` | `poly_n` | int | 7 | Polynomial expansion neighborhood. 5 = faster, 7 = smoother. |
| `optical_flow.farneback` | `poly_sigma` | float | 1.5 | Gaussian std for polynomial expansion. Use 1.2 for poly_n=5, 1.5 for poly_n=7. |
| `optical_flow.farneback` | `flags` | int | 0 | OpenCV flags. 0 = default. Use `256` (OPTFLOW_FARNEBACK_GAUSSIAN) for Gaussian window. |
| `window_detection` | `motion_threshold` | float | 0.5 | **Key parameter.** Max mean motion score for a frame to be "stable". See Motion Assessment table below. |
| `window_detection` | `min_duration_sec` | float | 3.0 | Minimum clip duration. Windows shorter than this are discarded. |
| `window_detection` | `merge_gap_sec` | float | 1.0 | Merge stable windows separated by this many seconds or less of instability. Prevents micro-splits. |
| `output` | `codec` | string | "mp4v" | FourCC codec for output clips. `mp4v` = MPEG-4, `avc1` = H.264 (if available). |
| `output` | `write_metadata` | bool | true | Write a `_metadata.json` file with full processing details per run. |
| `gpu` | `enabled` | bool | true | Attempt to use CUDA GPU for optical flow. Falls back to CPU automatically if unavailable. |
| `gpu` | `device_id` | int | 0 | GPU device index (for multi-GPU systems). |

### Motion Assessment Categories

Motion scores are measured as **mean pixel displacement at analysis resolution** (default 320px width):

| Category | Score Range | Description | Stock Footage? |
|----------|-------------|-------------|----------------|
| `static` | 0.00 - 0.05 | Tripod/locked camera, no visible motion | Yes |
| `very_stable` | 0.05 - 0.20 | Slow dolly, slider, or imperceptible drift | Yes |
| `stable` | 0.20 - 0.50 | Smooth pan/tilt or gentle tracking shot | Yes |
| `moderate` | 0.50 - 1.00 | Fast pan, stabilized handheld, or intentional camera movement | Borderline |
| `unstable` | 1.00 - 2.00 | Jerky handheld, whip pan, or irregular camera motion | No |
| `very_unstable` | 2.00 - 5.00 | Extreme shake, rapid direction change | No |
| `cut` | 5.00+ | Scene cut, flash, or abrupt transition | No |

### Threshold Presets (What to Use When)

| Preset | `motion_threshold` | Best For | Expected Result |
|--------|-------------------|----------|-----------------|
| **Strict** | 0.20 | Static b-roll overlays, timelapse base plates | Only locked-off/slider shots extracted |
| **Cinematic** (default) | 0.50 | Stock footage, film clips, smooth camera work | Pans/tilts included, handheld excluded |
| **Permissive** | 1.00 | Action footage, vlog clips with stabilization | Most motion passes, only jerky/extreme excluded |
| **Action** | 2.00 | Maximum extraction, minimal filtering | Nearly everything except scene cuts |

### Example Configurations

**For slow cinematic drone footage:**
```json
{
  "window_detection": { "motion_threshold": 0.30, "min_duration_sec": 8.0, "merge_gap_sec": 2.0 },
  "optical_flow": { "farneback": { "winsize": 31, "levels": 5, "iterations": 7 } }
}
```
*Explanation: Strict threshold (drone footage should be very smooth), longer minimum clips, large flow window for slow global motion.*

**For handheld interview/vlog footage:**
```json
{
  "window_detection": { "motion_threshold": 1.5, "min_duration_sec": 3.0, "merge_gap_sec": 0.5 },
  "optical_flow": { "farneback": { "winsize": 15, "levels": 3, "iterations": 3 } }
}
```
*Explanation: Permissive threshold (expect some sway), shorter clips acceptable, smaller flow window (faster processing, local detail matters).*

**For security/surveillance footage (extract activity segments):**
```json
{
  "window_detection": { "motion_threshold": 0.05, "min_duration_sec": 2.0, "merge_gap_sec": 3.0 },
  "analysis": { "max_width": 160, "motion_smoothing_sigma": 10 }
}
```
*Explanation: Very strict threshold (static scenes ARE the interesting ones here — invert logic in post), heavy smoothing, low resolution for speed.*

**For 4K high-framerate sports footage:**
```json
{
  "window_detection": { "motion_threshold": 2.0, "min_duration_sec": 2.0, "merge_gap_sec": 0.3 },
  "analysis": { "max_width": 480 },
  "optical_flow": { "farneback": { "winsize": 11, "levels": 3, "iterations": 3 } }
}
```
*Explanation: Very permissive (sports is fast), short clips okay, low merge gap (preserve actual pauses), higher analysis res for accuracy, fast flow settings.*

---

## Pipeline Architecture

```
video_slicer.py          CLI entry point, config loading, orchestration
  |
  +-- optical_flow.py    GPU/CPU flow computation (reusable calculator factory)
  +-- video_processing.py   Video I/O, motion scoring, window detection, slicing
  +-- motion_assessment.py  Motion classification enum and thresholds
  +-- hardware.py        Hardware detection for parallelization
  +-- batch_extract.py   Batch directory processing (parallel)
  +-- config.json        User configuration
```

### Output Files

| File | When | Contents |
|------|------|----------|
| `{video}_sliced/{video}_N.mp4` | When windows found | Extracted stable clips |
| `{video}_metadata.json` | When `write_metadata: true` | Full run metadata, stats, config used |
| `{dir}_features.csv` | Batch mode (--output csv) | Per-video features table |
| `{dir}_features.pkl` | Batch mode (--output pkl) | Full features + per-frame scores |

---

## Documentation Index

| File | Description |
|------|-------------|
| [setup.md](setup.md) | Install OpenCV with CUDA/cuDNN for GPU-accelerated processing |
| [setup.localLLM.md](setup.localLLM.md) | Configure IntelliJ with a local LLM (Ollama/Qwen) for AI-assisted development |
| [productionize.todo.md](productionize.todo.md) | Step-by-step roadmap to package Thea as a distributable offline .exe with installer |
