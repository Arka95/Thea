# Slicer development

[Back to Thea](../../README.md) | [Usage](README.md)

`src\slicer\slicer.py` owns the stream-copy and re-encoding implementations.
Settings choose the mode; `utils.ffmpeg` discovers FFmpeg and `utils.metrics`
tracks execution. The caller owns stable-window detection and the destination.

`src\integration_tests\test_slicer.py` performs real encoding and is opt-in.
There is no isolated slicer unit suite yet. Keep that boundary explicit; add
future mocked subprocess/capture tests under `src\slicer\tests` only for behavior
actually changed. Existing overwrite/failure semantics remain follow-up work,
not part of this structural migration.
