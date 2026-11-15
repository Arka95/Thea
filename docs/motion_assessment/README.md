# Motion assessment

[Back to Thea](../../README.md) | [Developer guide](dev.readme.md)

```python
from motion_assessment.analyzer import compute_motion_scores, detect_stable_windows
from utils.config_loader import load_preset

config = load_preset("cinematic")
result = compute_motion_scores(r"E:\videos\analysis.mp4", config)
windows = detect_stable_windows(
    result["motion_scores"], result["video_info"]["fps"], config
)
```

Motion scoring reads frames and computes optical flow. Stable-window detection
smooths/thresholds scores and applies minimum-duration/merge-gap rules.
`MotionAssessment` classifies scores at the configured analysis width.
See [configuration](../configuration.md) for thresholds and presets.

This is real media processing. Importing the API is not permission to probe
hardware or process a source video.
