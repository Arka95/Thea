# Merger development

[Back to Thea](../../README.md) | [Usage](README.md)

`src\merger\merger.py` owns manifest parsing, stream-compatibility checks,
temporary concat inputs, FFmpeg execution, output validation and exclusive
publication. It reuses probing from `tools.video_meta_strategy` and executable
discovery/metrics from `utils`.

The CLI chooses a default data-root destination; the Python API receives its
explicit output. Preserve input order, stream-copy behavior and refusal to
overwrite inputs/existing destinations.

```powershell
python -m pytest src\merger\tests -q
```

These unit tests fake probes and FFmpeg while testing actual temporary-file
cleanup, manifest handling, race/failure cases and CLI dispatch. They do not
encode real video.
