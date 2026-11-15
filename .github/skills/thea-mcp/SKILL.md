---
name: thea-mcp
description: Use Thea CLI or MCP tools to analyze, index, slice, merge, crop, pan and caption existing video.
user-invocable: true
---

# Thea video commands

Read `AGENTS.md`, `README.md` and `docs\mcp\README.md` for current contracts.
The root `mcp_server.py` launcher is configured as `thea` in `.vscode\mcp.json`.
Use an available client's tool-discovery mechanism before invoking MCP tools.
Do not assume configuration alone makes tools available in the current client.

Tools are `presets`, `downscale`, `analyze`, `slice`, `pipeline`, `merge`,
`crop`, `centercrop`, `ratiocrop`, `pan`, `caption` and `index`. Names match
`thea <command>`; `thea-index` remains an indexing alias. CLI hyphenated options
use underscored MCP parameters. Use existing Python APIs rather than subprocess
CLI invocation when developing inside Thea.

## Common calls

- Full-duration portrait pan: `pan({"path": "C:\\videos\\clip.mp4"})`.
  Default is 9:16, left-to-right; vertical-only travel uses top-to-bottom.
  Supply a complete `resolutionx`/`resolutiony` pair or `ratiox`/`ratioy` pair,
  never both. `duration` trims from the beginning; it never changes playback speed.
- Crop: `crop({"path": "C:\\videos\\clip.mp4", "width": 1000, "height": 600, "x": 100, "y": 200})`.
  Coordinates are the crop's top-left in displayed-source pixels.
- Caption: `caption({"path": "C:\\videos\\clip.mp4", "model": "your-vision-model"})`.
  The selected image-capable endpoint must already be running. Never invent a
  model ID or treat editor text-only models as vision models.
- Index: `index({"root": "C:\\videos", "db": "C:\\catalogue\\videos.sqlite3"})`.
  Always give `root` explicitly. Without `db` the catalogue is temporary.

Pass `output_path` for crop/pan/merge destinations. Processing `output` is a
directory except analyze, where it is `csv`/`pkl` for batch reports. Settings
and optional local overrides determine default output locations.

Check MCP `is_error` before reading `structured_content`. Report the actual
returned path; crop/pan no-ops may return the source without creating a file.
Preserve source footage and existing output protections. Caption credentials
come from `api_key_env` (default `THEA_CAPTION_API_KEY`), not tool arguments
containing the secret itself. Do not start a model, download weights or run
real media unless the user's task calls for it. No video generation.
