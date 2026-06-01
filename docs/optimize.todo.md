# Optimization Roadmap

Findings from a full code review targeting parallelization, batching, caching, and best practices for OpenCV + Python on RTX 4070 SUPER (12GB VRAM, 10 cores, 32GB RAM).

---

## Priority Order (Biggest Impact First)

| # | Optimization | Expected Gain | Complexity |
|---|-------------|---------------|------------|
| 1 | Cache analysis results | Skip ~60% of pipeline on re-runs | Low |
| 2 | Frame prefetch thread | 20-40% speedup on motion assessment | Medium |
| 3 | Reduce per-frame Python allocations | 10-15% speedup in hot loop | Low |
| 4 | Parallel FFmpeg slicing | Faster multi-window extraction | Low |
| 5 | Async CUDA stream overlap | 10-20% GPU utilization improvement | High |
| 6 | NVDEC hardware decoding | Major speedup for 4K source videos | High |

---

## 1. Cache Analysis Results

**Problem:** `compute_motion_scores()` re-runs optical flow on every pipeline invocation even if the video hasn't changed.

**Location:** `main.py:317-318`, `motion_assessment/analyzer.py`

**Solution:** Cache motion scores and metadata in `data_dir/analysis_cache/{video_base}.npz`.

**Cache contents:**
```
- raw_scores: np.float32 array (per-frame raw magnitudes)
- motion_scores: np.float32 array (smoothed)
- motion_stats: dict (mean, max, std, percentiles)
- video_info: dict (fps, total_frames, duration)
```

**File format recommendation:**
| Format | Pros | Cons | Verdict |
|--------|------|------|---------|
| `.npz` | Compact, fast load, numpy-native | No complex metadata | **Best for arrays** |
| `.npz` + `.json` sidecar | Arrays + metadata | Two files | **Recommended combo** |
| HDF5 | Structured, partial reads | Heavy dependency | Overkill |
| Pickle | Easy | Security risk, fragile across versions | Avoid |

**Cache invalidation key:**
```python
cache_key = f"{file_size}_{file_mtime}_{config_hash}_{pipeline_version}"
```
- `file_size + mtime` is cheap and catches most changes
- `config_hash` ensures re-analysis if optical flow params change
- Full file hash (SHA256) only if paranoid about content changes without mtime update

**Implementation:**
```python
# In analyzer.py or a new utils/analysis_cache.py
def get_cache_path(video_path, data_dir, config):
    base = os.path.splitext(os.path.basename(video_path))[0]
    return os.path.join(data_dir, "analysis_cache", f"{base}.npz")

def is_cache_valid(cache_path, video_path, config):
    if not os.path.exists(cache_path):
        return False
    meta = json.load(open(cache_path.replace('.npz', '.json')))
    stat = os.stat(video_path)
    return (meta["file_size"] == stat.st_size
            and meta["file_mtime"] == stat.st_mtime
            and meta["config_hash"] == hash_config(config))
```

---

## 2. Frame Prefetch Thread (Producer/Consumer)

**Problem:** In `analyzer.py:57-84`, frame decode (`cap.read()`) and GPU compute run sequentially on the same thread. Decode blocks GPU.

**Location:** `motion_assessment/analyzer.py:57-84`

**Solution:** Spawn a decode thread that fills a queue with preprocessed grayscale frames while the main thread runs optical flow.

```python
import threading
from queue import Queue

def _frame_producer(cap, analysis_w, analysis_h, queue, total_frames):
    """Decode and resize frames in background thread."""
    for _ in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            queue.put(None)
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if analysis_w != frame.shape[1]:
            gray = cv2.resize(gray, (analysis_w, analysis_h), interpolation=cv2.INTER_AREA)
        queue.put(gray)
    queue.put(None)  # sentinel

# In compute_motion_scores:
frame_queue = Queue(maxsize=8)  # buffer 8 frames
producer = threading.Thread(target=_frame_producer, args=(cap, analysis_w, analysis_h, frame_queue, total_frames))
producer.start()
```

**Expected gain:** 20-40% on GPU path (decode and GPU compute overlap). Less benefit on CPU path since both compete for cores.

**Consideration:** Queue size of 8 balances memory (~4MB for 320x180 grayscale * 8) vs latency hiding.

---

## 3. Reduce Per-Frame Python Allocations

**Problem:** Hot loop in `analyzer.py:65-82` creates a Python dict per frame and appends to lists.

**Location:** `motion_assessment/analyzer.py:65-82`

**Solution:**
- Preallocate numpy arrays for scores instead of list append
- Make `frame_metadata` collection optional (gated by a flag)

```python
# Before (current):
raw_scores_list = []
for i in range(...):
    magnitude = flow_calculator.compute(prev_gray, gray)
    raw_scores_list.append(magnitude)

# After (optimized):
raw_scores = np.empty(total_frames - 1, dtype=np.float32)
for i in range(...):
    raw_scores[i] = flow_calculator.compute(prev_gray, gray)
```

**Also:** `detect_stable_windows()` slices the motion_scores array repeatedly. Use cumulative sum arrays for O(1) mean/max computation over ranges:

```python
cumsum = np.cumsum(motion_scores)
# mean of scores[a:b] = (cumsum[b] - cumsum[a]) / (b - a)
```

---

## 4. Parallel FFmpeg Slicing

**Problem:** `slicer.py:38-61` runs FFmpeg processes sequentially, one per window.

**Location:** `slicer/slicer.py:38-61`

**Solution:** Launch all FFmpeg processes in parallel since windows are independent and FFmpeg stream-copy is I/O-bound:

```python
from concurrent.futures import ThreadPoolExecutor

def _slice_ffmpeg(video_path, windows, out_folder, base_name, src_ext):
    ffmpeg = _get_ffmpeg_exe()
    
    def _run_one(idx_window):
        idx, window = idx_window
        # ... build cmd, subprocess.run ...
        return out_path
    
    with ThreadPoolExecutor(max_workers=min(len(windows), 4)) as pool:
        output_files = list(pool.map(_run_one, enumerate(windows)))
```

**Expected gain:** Near-linear speedup for many windows (limited by disk I/O). For 3 windows, ~2-3x faster.

**Risk:** Disk contention if source is on HDD. Fine for SSD.

---

## 5. Async CUDA Stream Overlap

**Problem:** In `optical_flow.py:65-68`, frame upload, compute, and download are synchronous.

**Location:** `motion_assessment/optical_flow.py:62-83`

**Solution:** Use CUDA streams to overlap upload of frame N+1 while computing flow on frame N:

```python
stream1 = cv2.cuda_Stream()
stream2 = cv2.cuda_Stream()

# Frame N: compute on stream1
# Frame N+1: upload on stream2 (overlaps with stream1 compute)
```

**Complexity:** High — requires restructuring the flow calculator to manage multiple streams and pinned memory.

**Expected gain:** 10-20% on GPU-bound workloads. Larger gain on 4K analysis resolution where transfer time is significant.

**Prerequisite:** The OpenCV CUDA build must support stream-aware operations (the cudawarped wheel does).

---

## 6. NVDEC Hardware Video Decoding

**Problem:** `cv2.VideoCapture` uses CPU-based decoding (FFmpeg software decode). For 4K video, decode is a significant bottleneck.

**Location:** All `cv2.VideoCapture` calls (`analyzer.py:38`, `downscaler.py:44`)

**Solution:** Use OpenCV's CUDA video reader if available:

```python
# Check if NVDEC is available
if cv2.cuda.getCudaEnabledDeviceCount() > 0:
    reader = cv2.cudacodec.createVideoReader(video_path)
    ret, gpu_frame = reader.nextFrame()  # decoded directly on GPU
```

**Benefits:**
- Decode happens on GPU's dedicated NVDEC hardware (doesn't compete with CUDA cores)
- Frame is already on GPU — no host-to-device transfer needed for optical flow
- RTX 4070 SUPER has 1 NVDEC engine supporting H.264/H.265/VP9/AV1

**Challenges:**
- Not all OpenCV builds include `cudacodec` module
- Output is in NV12/BGR format on GPU — may need format conversion
- May not work with all container formats

**Expected gain:** 2-5x faster frame acquisition for 4K content.

---

## Additional Improvements

### Settings File Reads

**Problem:** `is_data_collection_enabled()` and `is_reencode_enabled()` read `settings.json` from disk on every call.

**Location:** `utils/settings.py:56-72`

**Solution:** Load settings once at startup, cache in a module-level singleton:

```python
_cached_settings = None

def _get_settings():
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = _load_raw_settings()
    return _cached_settings
```

### Optical Flow Algorithm Alternatives

For faster-but-less-accurate flow (sufficient for window detection):

| Algorithm | Speed | Accuracy | GPU Support |
|-----------|-------|----------|-------------|
| Farneback (current) | Medium | High | Yes |
| Lucas-Kanade (sparse) | Fast | Low (sparse points) | Yes |
| DIS (Dense Inverse Search) | **Very fast** | Medium | CPU only |
| NVIDIA Optical Flow SDK | **Fastest** | High | GPU-native |

**NVIDIA Optical Flow SDK** (`cv2.cuda.NvidiaOpticalFlow_2_0`) uses dedicated hardware on RTX cards. Could be 5-10x faster than Farneback for equivalent quality. Worth investigating for the RTX 4070 SUPER.

### Memory-Mapped Batch Output

For batch processing of many videos, memory-map the output CSV to avoid repeated file open/close:

```python
# Or just batch writes and flush periodically
buffer = []
for video in videos:
    buffer.append(row)
    if len(buffer) >= 10:
        flush_to_csv(buffer)
        buffer.clear()
```

---

## Summary: Implementation Phases

### Phase 1 (Quick wins, <1 day each)
- [ ] Analysis result caching with `.npz` + `.json` sidecar
- [ ] Preallocate numpy arrays in hot loop
- [ ] Parallel FFmpeg slicing with ThreadPoolExecutor
- [ ] Cache settings.json reads in a module singleton

### Phase 2 (Medium effort, 1-2 days each)
- [ ] Frame prefetch thread in analyzer
- [ ] Cumulative array for window detection mean/max
- [ ] Investigate NVIDIA Optical Flow SDK as Farneback alternative

### Phase 3 (Significant effort, research required)
- [ ] CUDA stream overlap for upload/compute pipelining
- [ ] NVDEC hardware decode integration
- [ ] DIS optical flow as a "fast mode" option

---

## Code Structure & Interface Notes

> Context: This is a local dev tool / MVP, not a web service. Keep it simple, avoid enterprise boilerplate.

### What's Working Well (Keep As-Is)

- **Flat module structure** — `motion_assessment/`, `downscaler/`, `slicer/`, `utils/` is the right granularity. No need for deeper nesting.
- **Functions over classes** — Most logic is pure functions (`compute_motion_scores`, `slice_video`, `downscale_video`). This is correct for a pipeline tool. Don't wrap in classes unless state truly needs to persist across calls.
- **Single CLI entry point** — `main.py` with subcommands is clean. No need for a plugin system or command registry.
- **JSON presets** — Simple, git-friendly, user-editable. Better than YAML/TOML for this use case.

### Suggested Simplifications

| Current | Issue | Suggestion |
|---------|-------|------------|
| `utils/settings.py` reads disk on every `is_reencode_enabled()` call | Unnecessary I/O in hot paths | Load once at startup, pass as a dict through the pipeline |
| `utils/pipeline_logger.py` imports `MotionAssessment` internally | Circular-ish dependency | Pass `overall_assessment` string as a parameter instead |
| `_write_video_metadata()` lives in `main.py` | It's a utility, not CLI logic | Move to `utils/` or keep but accept it's fine for an MVP |
| `config` dict threaded through every function | Verbose but explicit | Fine for now. Don't introduce a global config object — explicit is better |

### Interfaces to Stabilize (Before Adding More Features)

These function signatures are your internal API. Keep them stable:

```python
# Core pipeline functions — these are the "contracts"
compute_motion_scores(video_path: str, config: dict) -> dict
detect_stable_windows(scores: list, fps: float, config: dict) -> list[dict]
downscale_video(src: str, dst: str, max_width: int, codec: str, lossless: bool) -> dict
slice_video(video_path: str, windows: list, config: dict, output_dir: str) -> list[str]
resolve_data_dir(source_path: str) -> str
```

If you add caching (Phase 1), wrap it at the call site in `main.py`, not inside `compute_motion_scores` itself. Keep the core functions pure — they do computation, not I/O decisions.

### What NOT to Do (MVP Anti-Patterns)

- ❌ **Don't add an abstract base class for flow calculators** — `create_flow_calculator()` factory is sufficient. Two implementations (GPU/CPU) don't justify an ABC.
- ❌ **Don't add a dependency injection container** — pass config/settings explicitly.
- ❌ **Don't split `main.py` into a `cli/` package** — one file with ~400 lines is manageable.
- ❌ **Don't add async/await** — this is CPU/GPU-bound work, not I/O-bound web requests. Use threads/processes where needed.
- ❌ **Don't add type checking (mypy) enforcement** — type hints are nice documentation but strict checking adds friction for a solo dev tool.
- ❌ **Don't create interfaces/protocols for settings** — a dict is fine. You're the only consumer.

### Worth Doing If It Gets Messier

- **If `main.py` exceeds ~600 lines:** Extract `_run_single_pipeline` and batch logic into a `pipeline.py` module.
- **If you add more flow algorithms:** Consider a simple registry dict (`{"farneback": FarnebackGPU, "dis": DISFlow}`) instead of if/else chains.
- **If preset validation grows:** Use a lightweight schema (just a dict of `{key: (type, min, max)}`) rather than pulling in jsonschema/pydantic.
- **If batch processing needs progress tracking:** A simple callback function beats a full observer pattern.

### File I/O Pattern to Adopt

For caching and metadata, standardize on this pattern throughout:

```python
# Read: check exists -> load -> validate freshness
# Write: ensure dir -> write tmp -> rename (atomic)
# Never: read-modify-write without locking in parallel workers

def _atomic_write_json(path, data):
    """Write JSON atomically to avoid partial reads."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)  # atomic on same filesystem
```

This prevents corrupted metadata if the pipeline crashes mid-write.

