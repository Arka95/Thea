# Video Merging

[Back to Thea](../../README.md) | [Developer guide](dev.readme.md)

Merge an ordered list of compatible clips without re-encoding:

```powershell
python -m main merge clip1.mp4 clip2.mp4 --output-path "E:\Thea\merged\trip.mp4"
python -m main merge --manifest "E:\Thea\clips.txt" --output-path "E:\Thea\merged\trip.mp4"
```

The manifest is UTF-8 text with one video path per line, in playback order.
Relative paths are resolved beside the manifest. There is no clip-count cap;
use manifests for large selections to avoid command-line length limits.

The Python API is `merger.merge_videos(video_paths, output_path)`.
Keep catalogue selection in `VideoSearch` or `IStore.query()`; pass the resulting
ordered paths to the merger. To order a catalogue selection by recording time,
use `order_by="creation_time"`.

The command defaults to `<resolved data_dir>\merged\merge_<timestamp>.mp4`;
`--output-path` overrides that location without using the configured data directory.
Inputs and existing outputs are never overwritten. All compatible streams,
including audio, are copied. Stream compatibility is checked first; differing
codecs, dimensions, audio layouts or time bases fail rather than silently
re-encode. Output is checked before publishing, and temporary files are cleaned
up on failure.
