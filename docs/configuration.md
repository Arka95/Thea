# Configuration

[Back to Thea](../README.md) | [Developer guide](dev.readme.md)

Shared pipeline settings live in `config\settings\settings.json`; an optional ignored `settings.local.json` in the same folder overrides individual keys. Relative configured paths resolve from the repository root, not the current working directory. Fresh checkouts default to `data`. Explicitly setting an empty string retains the legacy source-relative behavior:

```json
{
  "data_dir": "data",
  "data_collection": true,
  "reencode": false
}
```

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `data_dir` | string | `"data"` | Repository-relative or absolute output root. Explicit `""` selects legacy source-relative resolution. |
| `data_collection` | bool | `true` | When `true`, appends results to `video_meta.csv` and `pipeline_stats.csv` in `data_dir`. |
| `reencode` | bool | `false` | When `false`, slicing uses FFmpeg stream copy (lossless, fast). When `true`, re-encodes with OpenCV using `output.codec` from the active preset. |

### Data Directory Resolution

Normally output goes to `<repository>\data`, independent of the working directory. A machine-local override can select another drive. Only when `data_dir` is explicitly empty (`""`) does Thea resolve output from the source path:

| Input | Resolved `data_dir` |
|-------|---------------------|
| `python -m main pipeline sample.mp4` | `./Thea/` (parent of file + `/Thea`) |
| `python -m main pipeline ./videos/` | `./videos/Thea/` (source dir + `/Thea`) |
| `data_dir: "E:/Thea"` in settings | `E:/Thea/` (used as-is) |

### Data Directory Structure

```
data_dir/
├── downscaled/        Downscaled videos (cached, skipped on re-runs)
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
| `output` | `write_metadata` | bool | true | Present in presets; current CLI analysis/pipeline writes metadata unconditionally. |
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

## Local overrides and precedence

1. Built-in fallback values (`data`, logging disabled, stream-copy slicing).
2. Tracked `config\settings\settings.json`.
3. Ignored `config\settings\settings.local.json`, overriding only supplied keys.

`data_dir` must be a string; `data_collection` and `reencode` must be booleans. Invalid JSON or types fail instead of silently ignoring configuration. The existing machine output location was preserved in the ignored local file during migration. Do not copy machine-specific paths into tracked defaults.

CLI `--config` overrides `--preset` for motion configuration. Explicit output arguments keep their existing command-specific behavior; see the module guides. Preset validation lives in `src\utils\config_loader.py`.
