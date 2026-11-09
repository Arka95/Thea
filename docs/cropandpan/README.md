# Crop and pan

[Thea README](../../readme.md) | [Developer guide](dev.readme.md)

```python
from src.cropandpan import crop, centercrop, ratiocrop, pan

crop("clip.mp4", 1000, 600, 100, 200, output_path=r"E:\Thea\cropandpan\crop.mp4")
centercrop("clip.mp4", 1080, 1080, output_path=r"E:\Thea\cropandpan\square.mp4")
ratiocrop("clip.mp4", 9, 16, output_path=r"E:\Thea\cropandpan\portrait.mp4")
pan("clip.mp4", duration=5, output_path=r"E:\Thea\cropandpan\pan.mp4")

# A 3840x2160 source: 1000x600 crop, right-to-left over the first five seconds.
pan("clip.mp4", 1000, 600, 2840, 780, 0, 780, 5,
    output_path=r"E:\Thea\cropandpan\reverse.mp4")

# Diagonal, or a ratio instead of pixel dimensions.
pan("clip.mp4", 1000, 600, 0, 0, 2840, 1560, 5,
    output_path=r"E:\Thea\cropandpan\diagonal.mp4")
pan("clip.mp4", ratiox=1, ratioy=1, duration=5,
    output_path=r"E:\Thea\cropandpan\square-pan.mp4")
```

## Conventions and validation

Follow FFmpeg: **width before height**, coordinates in pixels from the displayed
video's top-left. `x` increases rightward; `y` increases downward. Both pan
endpoints specify the crop's **top-left**, not its center or opposite corners.
Dimensions and coordinates must be integers; dimensions must be positive,
coordinates nonnegative, and the complete rectangle must stay inside the frame.
Right-angle rotation metadata is respected, as with FFmpeg's default autorotation.

`crop(video, width, height, x, y)` fixes the rectangle. `centercrop(video, width,
height)` centers it, rounding the position down to an integer pixel.
`ratiocrop(video, ratiox, ratioy)` chooses the largest centered rectangle with the
exact requested display aspect ratio, accounting for sample aspect ratio and
source pixel-format alignment. Ratios must be positive, finite numbers.
For example, 9:16 from 3840x2160 `yuv420p` is **1206x2144**: the largest exact
9:16 rectangle with even dimensions. Explicit dimensions are rejected, not
silently rounded, when incompatible with source chroma subsampling.

`pan(video, resolutionx=None, resolutiony=None, startx=None, starty=None,
endx=None, endy=None, duration=None, *, ratiox=None, ratioy=None)` accepts a
complete dimension pair or a complete ratio pair, never both.
Without either, it uses 9:16. Without coordinates, it traverses left-to-right,
or top-to-bottom when the fitted crop only has vertical room. Specify endpoints
to reverse direction. Specifying just one axis keeps the other centered;
specifying both permits diagonal movement. Positions interpolate linearly at
the original frame timestamps, with pixel/frame granularity.

Duration is in seconds and defaults to the source video's duration. A five-second
pan produces approximately five seconds from the **beginning** of the source;
only crop movement changes, never video or audio playback speed.
Audio packets and video frames impose normal duration granularity.
Zero, nonfinite, negative, unknown or longer-than-source durations are rejected.

## Encoding and outputs

Functions return an absolute output path as a string. When no cropping/movement
or trimming is necessary, they return the **original path**, without creating a
file, even if `output_path` was supplied.
Otherwise the default is
`<resolved data_dir>\cropandpan\<source>_<operation>_<timestamp>.<source extension>`.
`output_path` bypasses configured data-directory resolution.
Unavailable configured drives fail normally; there is no silent drive fallback.

Cropping and panning re-encode video using the **source codec and pixel format**,
not the original encoder settings or bitrate. Common codecs use software
encoders such as libx264/libx265; others use the matching native encoder name.
Missing encoders, incompatible output containers and unsupported formats fail
clearly, without a codec fallback. Audio streams are copied. Only the first
non-cover-art video and all audio streams are included; extra video, subtitle
and data streams are not included. Source metadata is copied where compatible.
The slicer's `reencode` setting does not disable these necessary transformations.

Source files and existing destinations are never overwritten. Encoding uses a
temporary sibling directory; results are probed before publication and partial
files are removed on failure. There are Python APIs, not new `main.py` commands.
