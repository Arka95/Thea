---
name: config-validator
description: Validate Thea configuration files (presets, settings, codecs). Check for inconsistencies, unsupported options, and edge cases. Use before deployment or when modifying config files.
user-invocable: true
disable-model-invocation: false
---

# Config Validator Skill

Validate and audit Thea's configuration system.

## When to Use This Skill

- Validate new preset files before committing
- Check for unsupported codec combinations
- Ensure config consistency across presets
- Validate user-provided configuration
- Audit settings for edge cases

## Configuration Files Structure

```
config/
├── presets/          # Motion/quality profiles
│   ├── action.json
│   ├── cinematic.json
│   ├── permissive.json
│   └── strict.json
└── settings/         # System configuration
    ├── settings.json
    └── supported_codecs.txt
```

## Validation Rules

### Preset Validation (presets/*.json)

**Required Fields**:
- `name` (string): Preset identifier
- `motion_thresholds` (object): Motion detection parameters
- `quality_level` (int): 0-100 scale
- `codec_preference` (string): codec name

**Motion Thresholds Structure**:
```json
{
  "optical_flow_magnitude": [min, max],
  "category_thresholds": {
    "static": [0, 5],
    "slow": [5, 15],
    "medium": [15, 30],
    "fast": [30, 100]
  }
}
```

**Quality Level Constraints**:
- 0-30: Aggressive compression (low quality)
- 31-70: Balanced (recommended)
- 71-100: High quality (large files)

### Codec Validation (settings/supported_codecs.txt)

**Valid Codecs**: h.264, h.265, vp9, av1, prores
**Check**:
- Codec listed in supported list
- Encoder available on system
- Bitrate within codec range
- Profile level supported

### Settings Validation (settings/settings.json)

**Performance Settings**:
- `gpu_memory_limit`: 1-12GB (for RTX 3080)
- `thread_pool_size`: 1-CPU_COUNT
- `frame_buffer_size`: 1-100

**Quality Settings**:
- Motion analysis resolution: 480p-1080p
- Interpolation method: supported OpenCV methods
- Color space: RGB, YUV, or system default

## Validation Process

### Step 1: Schema Check
```python
# Verify JSON structure matches schema
# All required fields present
# No unknown fields
```

### Step 2: Value Range Check
```python
# Quality level in [0, 100]
# Motion thresholds in valid range
# File paths readable
```

### Step 3: Consistency Check
```python
# All presets use same codec list
# No conflicting motion categories
# Settings compatible with presets
```

### Step 4: System Compatibility Check
```python
# Requested codecs installed
# GPU memory sufficient
# CPU cores available >= thread_pool_size
```

## Validation Report Output

Produce a structured report:
```
✓ Preset: action.json
  ✓ Schema valid
  ✓ Value ranges OK
  ⚠ Warning: H.265 encoder not found (fallback to H.264)
  
✗ Preset: experimental.json
  ✗ Missing required field: 'quality_level'
  ✗ Invalid motion threshold: 'fast' < 'medium'
```

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Invalid codec | Typo or unsupported | Check supported_codecs.txt |
| Motion thresholds overlap | Range error | Ensure min ≤ max, no overlap |
| Quality too aggressive | Settings mismatch | Use presets/cinematic for balanced |
| GPU memory exceeded | Buffer size too large | Reduce frame_buffer_size |

## Integration with CI/CD

Add to pre-commit or CI pipeline:
```bash
python -m thea.config_validator config/ --strict
```

Exit code 0 = valid, 1 = errors, 2 = warnings only
