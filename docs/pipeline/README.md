# Pipeline and CLI

[Back to Thea](../../README.md) | [Developer guide](dev.readme.md)

After editable installation, use `thea` or `python -m main`.

| Command | Responsibility |
|---------|----------------|
| `pipeline PATH` | Downscale for analysis, find stable windows, slice the original, and write metadata/logs |
| `analyze PATH` | Analyze one video or a directory; batch output supports CSV/pickle |
| `slice PATH` | Analyze and extract windows without a separate downscale stage |
| `downscale PATH` | Produce single or batch analysis copies |
| `presets` | List checked-in presets without processing media |
| `merge PATHS...` | Concatenate compatible clips; see [merger](../merger/README.md) |
| `crop`, `centercrop`, `ratiocrop`, `pan` | Transform one source video; see [crop/pan](../cropandpan/README.md) |
| `caption PATH --model MODEL` | Caption sampled frames through a selected vision endpoint |
| `index [ROOT] [LIMIT]` | Index metadata; alias of `thea-index` |

```powershell
thea pipeline "E:\videos\clip.mp4" --preset cinematic
thea analyze "E:\videos" --preset strict --output pkl
thea downscale "E:\videos\clip.mp4" --width 640 --lossless
```

Processing commands accept a file or directory. Use `--help` on the specific
command for its supported overrides; not every similarly named argument has
identical behavior. Presets, settings and output records are documented in
[configuration](../configuration.md).
All commands also have [matching MCP tools](../mcp/README.md), sharing the same
dispatcher and parameter defaults. `pipeline --output DIR` selects the output
root for that run.
