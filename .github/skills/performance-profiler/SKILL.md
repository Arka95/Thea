---
name: performance-profiler
description: Investigate Thea performance using existing metrics and explicitly authorized profiling.
user-invocable: true
disable-model-invocation: false
---

# Performance profiling

Follow `AGENTS.md`. Read the affected module and `src\utils\metrics.py` before
adding instrumentation. Thea uses OpenCV/FFmpeg; do not assume a Torch runtime.

- Use existing measurements first. Real media, GPU probes, long benchmarks,
  model calls and profiling require an explicit request and a bounded workload.
- Preserve the selected environment/device, inputs, outputs, and cache semantics.
  Do not install a profiler or clear another process's GPU/model cache.
- Record workload, provider/runtime, environment, wall time and nested spans
  separately. Do not claim a speedup without comparable measured runs.
- Keep diagnostics bounded, local and ignored under `data\diagnostics`. Each
  run owns its records; do not log source/media contents or sensitive arguments.
- `scripts\benchmark_hash.py ROOT [LIMIT]` and
  `scripts\explore_metadata.py ROOT [LIMIT]` are explicit, real-file diagnostics,
  not unit checks. Both write unique reports under `data\diagnostics`.
- Report the bottleneck, measured evidence, limits, and smallest justified fix.
