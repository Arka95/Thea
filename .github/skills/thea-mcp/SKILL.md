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
`crop`, `centercrop`, `ratiocrop`, `pan`, `caption`, `index`, `importindex`
and `search`. Names match
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
- Index: `index({"root": "C:\\videos"})`.
  Always give `root` explicitly. Every catalogue tool uses configured
  `data_dir\video-index.sqlite3`; per-command `db` is no longer supported.
  Add `report_path` pointing to a new JSON for full path/count audits. Inspect
  `scan.complete`, `scan.limited`, per-directory counts and errors; top-level
  `distinct` includes earlier database contents. Do not equate discovered paths
  with distinct content hashes or claim a live scan is an atomic snapshot.
  Writable catalogue operations atomically remove retired metadata columns.
  Inspect `schema.columns` and `schema.removed_columns` in the index response.
  Reload an existing server process after code changes before applying migration.
- Import old catalogues: `importindex({"paths": ["E:\\Thea\\old.sqlite3"]})`.
  Sources remain untouched; retain them until the merge is verified.
- Search: `search({"query": "drone footage in Arunachal for nature", "limit": 10})`.
  Return the ranked paths and descriptions; do not claim metadata-only matches
  are visually verified. No custom SQL/client-side selection loop is needed.
  Results include all retained fields and array-valued `tags`; `score` and
  `exists` are computed, never stored. Search is read-only.

Persist only the slim organizing schema: identity, device, basic video properties,
description, user-managed tags and the five requested location fields.
`creation_time` prefers embedded recording time; filesystem creation time is the
fallback, never modification time. Reindexing preserves known recording times.
Do not copy codec/audio/container/probe data or arbitrary file tags into records.
Use `index` with `probe=True` when embedded metadata must be extracted.

Caption accepts a file or directory and saves successful text into
`videos.description`. It automatically supplies indexed country/state context,
marking folder inference approximate. Directory mode is recursive/sequential;
inspect `complete` and per-file `errors`. Failed inference retains existing
descriptions. Do not equate generated text with reviewed visual accuracy.
Temporary JPEG cleanup belongs to the core captioner and runs on success or
failure. `sample.image_path` is null after cleanup. Supply `contact_sheet` only
to retain an explicit new JPEG; never remove user-provided images.

Pass `output_path` for crop/pan/merge destinations. Processing `output` is a
directory except analyze, where it is `csv`/`pkl` for batch reports. Settings
and optional local overrides determine default output locations.

Check MCP `is_error` before reading `structured_content`. Report the actual
returned path; crop/pan no-ops may return the source without creating a file.
Preserve source footage and existing output protections. Caption credentials
come from `api_key_env` (default `THEA_CAPTION_API_KEY`), not tool arguments
containing the secret itself. Do not start a model, download weights or run
real media unless the user's task calls for it. No video generation.
