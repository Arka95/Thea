---
name: performance-profiler
description: Profile GPU/CPU/memory usage in video processing pipeline. Identify bottlenecks, CUDA optimization opportunities, and memory leaks. Use when optimizing for speed or reducing resource consumption.
user-invocable: true
disable-model-invocation: false
---

# Performance Profiler Skill

Analyze and optimize the Thea video processing pipeline for performance.

## When to Use This Skill

- Identify GPU memory bottlenecks in motion assessment
- Profile CPU usage in downscaling/slicing operations
- Detect memory leaks in long-running pipelines
- Compare performance between CUDA and CPU paths
- Benchmark codec encoding/decoding operations

## Profiling Strategy

### 1. GPU Profiling (NVIDIA)
```bash
# Monitor GPU usage in real-time
nvidia-smi -l 1  # Update every second

# Profile with nsys (NVIDIA Systems Tools)
nsys profile -t cuda,cudnn python main.py
```

### 2. Memory Profiling
```bash
# GPU memory via pycuda
from pycuda.tools import DeviceData

# CPU memory via memory_profiler
@profile
def video_processing():
    # your code here
```

### 3. CPU Profiling
```bash
# cProfile for function-level profiling
python -m cProfile -s cumulative main.py

# Line profiler for line-by-line analysis
kernprof -l -v script.py
```

## Key Performance Metrics

| Component | Target | Tool |
|-----------|--------|------|
| Motion Assessment | <100ms/frame | nsys profile |
| Downscaling | <50ms/frame | cProfile |
| Slicer (FFmpeg) | Real-time or faster | time measurements |
| Memory (GPU) | <4GB for 1080p | nvidia-smi |
| Memory (CPU) | <2GB baseline | memory_profiler |

## Optimization Patterns

### CUDA Optimization
- Check if GPU is being used: `nvidia-smi | grep python`
- Profile kernel execution: `nvidia-smi --query-gpu=utilization.gpu --format=csv -lps 1`
- Reduce memory copies between GPU/CPU
- Batch operations when possible

### Memory Optimization
- Use generators instead of lists for frame streams
- Clear GPU cache between batches: `torch.cuda.empty_cache()`
- Profile with `tracemalloc` for allocation tracking
- Monitor memory growth over time

### CPU Optimization
- Parallelize with multiprocessing where GIL allows
- Use FFmpeg subprocess efficiently (avoid buffering)
- Cache motion assessment results
- Vectorize NumPy operations

## Deliverables

When profiling, produce:
1. **Bottleneck Report**: Which function/operation takes most time
2. **Memory Report**: Peak usage per component
3. **Recommendations**: Specific optimizations with expected impact
4. **Regression Test**: Baseline metrics to prevent performance regression
