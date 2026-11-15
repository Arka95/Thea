# Thea MCP commands

[Back to Thea](../../README.md) | [Developer guide](dev.readme.md)

The local stdio server exposes the same operations as the
[complete CLI reference](../../README.md#usage). It does not start a model,
download weights, or process media merely by being imported or listing tools.

## Setup

Select the existing compatible Thea environment first. The optional dependency
is declared as `mcp>=2.0,<3` in `pyproject.toml`.
For an already-provisioned runtime, install just the SDK and refresh entry points
without replacing the existing video/CUDA packages:

```powershell
python -m pip install "mcp>=2.0,<3"
python -m pip install --no-deps -e .
```

In a new compatible environment, `python -m pip install -e ".[mcp]"` installs
the runtime and optional SDK together. No additional CLI extra of the SDK is
required.

The checked-in `.vscode\mcp.json` defines the `thea` connection using this
checkout's `.venv` and root launcher. Adjust the Python executable if your
selected environment differs. Other clients can use an absolute executable and
script path:

```json
{
  "command": "C:\\projectWorkspace\\Thea\\.venv\\Scripts\\python.exe",
  "args": ["C:\\projectWorkspace\\Thea\\mcp_server.py"],
  "cwd": "C:\\projectWorkspace\\Thea"
}
```

`thea-mcp` is an equivalent installed launcher. A client starts/stops the stdio
process; no persistent web server is required. Diagnostics use stderr and stdout
is reserved for MCP. Filesystem paths refer to the server's machine.

## Tools and parameters

| MCP tool | Corresponding CLI | Parameters |
|----------|-------------------|------------|
| `presets` | `thea presets` | None |
| `downscale` | `thea downscale PATH` | `path`, `preset`, `config`, `output`, `width`, `lossless` |
| `analyze` | `thea analyze PATH` | `path`, `preset`, `config`, `output`, `output_path` |
| `slice` | `thea slice PATH` | `path`, `preset`, `config`, `output` |
| `pipeline` | `thea pipeline PATH` | `path`, `preset`, `config`, `output` |
| `merge` | `thea merge` | `paths` or `manifest`, plus `output_path` |
| `crop` | `thea crop PATH WIDTH HEIGHT X Y` | `path`, `width`, `height`, `x`, `y`, `output_path` |
| `centercrop` | `thea centercrop PATH WIDTH HEIGHT` | `path`, `width`, `height`, `output_path` |
| `ratiocrop` | `thea ratiocrop PATH RATIOX RATIOY` | `path`, `ratiox`, `ratioy`, `output_path` |
| `pan` | `thea pan PATH` | `path`, `resolutionx`, `resolutiony`, `ratiox`, `ratioy`, `startx`, `starty`, `endx`, `endy`, `duration`, `output_path` |
| `caption` | `thea caption PATH --model MODEL` | `path`, `model`, `base_url`, `api_key_env`, `timeout_sec`, `contact_sheet`, `sampling_video`, `sample_count`, `frame_width`, `frame_height`, `columns`, `location_in_metadata`, `timestamp_in_metadata`, `context` |
| `index` | `thea index` / `thea-index` | `root`, `limit`, `db`, `probe`, `geocode`, `infer_loc` |

CLI hyphens become underscores in MCP parameter names. Defaults match the CLI.
`output` means a directory for downscale/slice/pipeline but a batch-report format
(`csv`/`pkl`) for analyze. A custom `config` overrides `preset`.
Pass an explicit indexing `root`; the legacy default remains `D:\`.

## Examples

Call tool `pan` with:

```json
{"path": "C:\\videos\\clip.mp4"}
```

This uses the original video's full duration, a largest-fitting exact 9:16 crop,
and left-to-right travel without changing playback speed. If only vertical
travel is available it moves top-to-bottom. Optional `output_path` selects a new
destination; otherwise configured `data_dir\cropandpan` is used.
The [crop/pan contract](../cropandpan/README.md) still applies.

Call tool `caption` with:

```json
{
  "path": "C:\\videos\\clip.mp4",
  "model": "your-image-capable-model",
  "base_url": "http://localhost:1234/v1",
  "location_in_metadata": true
}
```

The endpoint must already serve the selected image-capable model. Set
`THEA_CAPTION_API_KEY` in the server's environment when authentication is needed,
or name another variable with `api_key_env`. The result includes the caption,
model, contact-sheet path and sampling metadata. Existing contact sheets are
not overwritten by this command.

## Results and failures

Tools return JSON in MCP `structured_content` and readable content. Crop/pan
return `{"output": "<absolute path>"}`; a no-op can return the source path.
Motion analysis returns statistics/windows rather than per-frame score arrays.
Batch analysis reports its saved file and compact results; pipeline returns
source, analysis copy, clips, windows and metadata per input.
Index returns save-attempt/distinct counts and up to eight sample records.

Check `is_error` before using a result. Expected path/argument errors provide
actionable messages. Existing processing behavior, including legacy output
overwrite/failure policies, remains owned by each underlying operation.
Operations are serialized inside a server process so process-local metrics and
media work from separate requests do not overlap.
