# Shared utilities

[Back to Thea](../../README.md) | [Developer guide](dev.readme.md)

`utils` contains reusable infrastructure used by multiple processing modules.
Use `utils.config_loader.load_preset` for motion configuration and
`utils.settings.resolve_data_dir` for settings-based pipeline output.

Other helpers cover supported codecs, FFmpeg discovery, video discovery and
metadata, validation, hardware profiles, pipeline CSV records and existing
execution metrics. See [configuration](../configuration.md) for the public
settings contract; hardware/media helpers can perform real I/O when called.

`get_catalogue_path()` is the single source for the persistent
`data_dir\video-index.sqlite3` path, independent of the scanned source directory.
The shared dispatcher records command wall duration/outcome for CLI and MCP.
Metrics retain at most 2,048 process-local spans; telemetry failures cannot
replace application results. Error metrics contain the error type, not its
message. Function-span sums include nested work and are not elapsed wall time.
Child-process spans are not aggregated; the parent command duration still
covers its wait. MCP serializes operations and resets its own collector per call.
