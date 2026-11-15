# Motion assessment development

[Back to Thea](../../README.md) | [Usage](README.md)

`assessment.py` owns categories and threshold scaling. `optical_flow.py` owns
Farneback CPU/CUDA implementations and calculator selection. `analyzer.py`
owns frame traversal, scores, smoothing and stable-window detection. Keep those
boundaries and existing fallback behavior intact when changing another module.

Classification unit tests:

```powershell
python -m pytest src\motion_assessment\tests -q
```

Real optical flow, frame decoding and reference windows are tested separately
in `src\integration_tests\test_optical_flow.py` and `test_analyzer.py`. They may
use a GPU and the tracked sample; run only when explicitly requested. Presets
remain in root `config`, not beside the relocated source.
