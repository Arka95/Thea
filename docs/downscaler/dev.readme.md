# Downscaler development

[Back to Thea](../../README.md) | [Usage](README.md)

`src\downscaler\downscaler.py` owns OpenCV capture/writer lifecycle, resizing and
batch worker orchestration. It reuses `utils.video_io` and `utils.metrics`;
it does not own preset or data-root discovery.

There are no isolated downscaler unit tests yet. The relocated
`src\integration_tests\test_downscaler.py` uses real media/OpenCV and is opt-in.
Do not silently pull it into default unit collection. A future focused change
can introduce fake capture/writer tests under `src\downscaler\tests`.
