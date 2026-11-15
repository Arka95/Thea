# Downscaler

[Back to Thea](../../README.md) | [Developer guide](dev.readme.md)

```powershell
thea downscale "E:\videos\clip.mp4" --width 640
thea downscale "E:\videos" --width 640 --lossless
```

Python APIs are `downscaler.downscale_video` and `downscaler.batch_downscale`.
They create analysis copies while preserving FPS and aspect ratio.
Normal mode uses the configured codec and area interpolation; lossless mode
selects FFV1, LANCZOS4 and `.avi` output.

CLI output defaults to the resolved data directory's `downscaled` folder.
Explicit API output paths and CLI `--output` remain supported.
