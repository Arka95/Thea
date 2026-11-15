# Shared utilities

[Back to Thea](../../README.md) | [Developer guide](dev.readme.md)

`utils` contains reusable infrastructure used by multiple processing modules.
Use `utils.config_loader.load_preset` for motion configuration and
`utils.settings.resolve_data_dir` for settings-based pipeline output.

Other helpers cover supported codecs, FFmpeg discovery, video discovery and
metadata, validation, hardware profiles, pipeline CSV records and existing
execution metrics. See [configuration](../configuration.md) for the public
settings contract; hardware/media helpers can perform real I/O when called.
