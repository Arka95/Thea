# Utilities development

[Back to Thea](../../README.md) | [Usage](README.md)

`paths.py` owns repository/config/data roots for the editable checkout.
`config_loader.py` discovers and validates presets; `settings.py` merges shared
and optional local settings and resolves output paths. Do not duplicate parent
traversal in consumers or add per-file environment/config precedence.

`ffmpeg.py`, `video_io.py` and `validations.py` provide media helpers.
`hardware.py` detects capabilities; `metrics.py` and `pipeline_logger.py` own
the current timing/CSV machinery. The migration preserves those existing
measurement semantics rather than introducing another instrumentation layer.

```powershell
python -m pytest src\utils\tests -q
```

Hardware tests fake CPU/RAM/GPU responses rather than probing the host.
Settings tests cover merged overrides, invalid types/JSON, repository-relative
paths, missing files, legacy source-relative paths and CSV output. Preset tests
resolve the actual root `config` directory after relocation.
