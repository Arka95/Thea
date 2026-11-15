# Slicer

[Back to Thea](../../README.md) | [Developer guide](dev.readme.md)

```powershell
thea slice "E:\videos\clip.mp4" --preset cinematic
```

The Python API is `slicer.slice_video(video_path, windows, config, output_dir)`.
Windows contain start/end seconds. With `reencode: false`, FFmpeg copies source
streams; `true` selects the existing OpenCV re-encoding path and preset codec.
Stream-copy boundaries retain FFmpeg/keyframe behavior rather than promising
frame-exact cuts.

The CLI supplies the resolved `sliced` data folder. Direct API callers should
pass `output_dir`; the legacy fallback is `<video-name>_sliced` relative to the
working directory. Existing slice outputs can be overwritten by the legacy
encoder commands; this relocation does not change that policy.
