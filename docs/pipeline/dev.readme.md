# Pipeline development

[Back to Thea](../../README.md) | [Usage](README.md)

`src\main.py` owns argument parsing, command dispatch, processing orchestration,
batch workers and metadata publication. `build_parser` and `main` retain their
existing callable names; packaging publishes `main:main` as `thea`.

`_run_single_pipeline` reuses an existing downscaled file by pathname, otherwise
creates an analysis copy, computes motion/windows and slices the original.
It then writes metadata and optionally CSV records. The migration does not
change cache identity, algorithm/device selection, timestamps, output naming,
or the existing serial batch-pipeline behavior.

Batch analysis uses `ProcessPoolExecutor`; workers import the installed modules
normally. Configuration/presets are loaded before dispatch. Shared settings
resolution is in `utils.settings`, not in the CLI.

CLI parsing and merge dispatch are covered by
`python -m pytest src\merger\tests -q`. Full media orchestration lives in the
explicitly opt-in `src\integration_tests\test_main_pipeline.py`; it is not a unit
smoke test. `python -m main --help` and `thea presets` are non-processing checks.
