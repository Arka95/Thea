---
name: video-pipeline-architect
description: Evaluate and refactor Thea's video processing architecture. Assess component interactions, data flow, and scalability. Use for architectural decisions, major refactoring, or extending the pipeline.
user-invocable: true
disable-model-invocation: false
---

# Video Pipeline Architect Skill

Make architectural decisions for the Thea video processing system.

## When to Use This Skill

- Design new features that affect multiple components
- Evaluate trade-offs between accuracy/speed/complexity
- Plan major refactoring efforts
- Design integration with new codecs or motion analysis methods
- Assess scalability for batch processing

## Thea Architecture Overview

```
Input Video
    ↓
[Motion Assessment] ← GPU-accelerated optical flow + motion categories
    ↓
[Slicer] ← Segments based on motion, preserves quality
    ↓
[Downscaler] ← Adaptive resolution per segment
    ↓
Output (H.265 or custom codec)
```

### Component Responsibilities

| Component | Input | Output | Tech Stack |
|-----------|-------|--------|-----------|
| Motion Assessment | Video frames | Motion vectors + categories | OpenCV, PyTorch, GPU |
| Slicer | Frames + motion | Segment boundaries | FFmpeg, decision logic |
| Downscaler | Frames + metadata | Resized frames | OpenCV, H.264/H.265 |
| Config Loader | JSON presets | Runtime parameters | Python JSON |

## Architectural Patterns

### Pattern 1: Stream-Based Processing
**Current**: Processes entire video in memory buffers
**Consideration**: For very large videos, use frame generators
```python
def frame_generator(video_path):
    # Yield frames one at a time
    # Reduces memory footprint
```

### Pattern 2: Preset System
**Current**: YAML/JSON presets (action, cinematic, permissive, strict)
**Extension**: Add learned presets from user feedback

### Pattern 3: GPU Acceleration
**Current**: Motion assessment on GPU, others on CPU
**Consideration**: Move downscaling to GPU for real-time processing

### Pattern 4: Modular Codec Support
**Current**: FFmpeg-based encoding
**Opportunity**: Abstract codec interface for VP9, AV1 support

## Design Decisions to Make

### When Adding Features

1. **Does it fit existing components?** (Enhancement)
   - Add motion categories → Motion Assessment
   - New codec preset → Config/Downscaler

2. **Does it require new component?** (Extension)
   - Audio processing → New module
   - Subtitle generation → New module

3. **Does it cross-cut concerns?** (Refactoring)
   - Performance monitoring → Observability layer
   - Quality metrics → Evaluation framework

## Scalability Considerations

- **Batch Processing**: Design for multiple videos in queue
- **Distributed**: Consider FFmpeg/GPU bottleneck
- **Caching**: Motion assessment results are expensive
- **Versioning**: Config versioning for reproducibility

## Code Review Checklist for Architectural Changes

- [ ] Component boundaries respected
- [ ] Data flow is unidirectional (or explicitly managed)
- [ ] No circular dependencies
- [ ] Config-driven where appropriate
- [ ] GPU usage efficient
- [ ] Memory doesn't leak across frames
- [ ] Error handling doesn't hide failures
