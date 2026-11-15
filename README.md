# Thea

Thea extracts stable stock-footage clips using OpenCV motion analysis and FFmpeg.
It also indexes video metadata, merges compatible clips, crops/pans footage, and
provides optional sampled-frame captioning. All operations are available through
the CLI and the [Thea MCP server](docs/mcp/README.md).

## Setup

Follow [Python setup](docs/setup.md) and [CPU/GPU setup](docs/setup.gpu.md).
Keep an existing CUDA environment intact. After selecting and activating the
appropriate environment, install the source checkout:

```powershell
python -m pip install --no-deps -e .
```

Thea currently supports an **editable repository checkout**, not a standalone
wheel deployment: runtime configuration remains under the repository's `config`.

## Usage

Both processing/index CLI entry points and all twelve `thea` subcommands are listed below.
`PATH` accepts a video file or directory for `downscale`, `analyze`, `slice`,
and `pipeline`. These four commands accept `--preset NAME` (default:
`cinematic`) and `--config FILE` (overrides the preset).

| Command | Purpose | Additional arguments/options |
|---------|---------|------------------------------|
| `thea presets` | List available presets | None |
| `thea downscale PATH` | Create smaller analysis copies | `--output DIR`, `--width PIXELS` (default: 320), `--lossless` (FFV1 AVI) |
| `thea analyze PATH` | Assess motion and find stable windows | Batch reports: `--output {csv,pkl}` (default: csv), `--output-path FILE` |
| `thea slice PATH` | Analyze the input and extract stable clips | `--output DIR` |
| `thea pipeline PATH` | Downscale, analyze, slice the original, and write metadata/logs | `--output DIR` overrides the run's output root |
| `thea merge [PATHS ...]` | Join at least two compatible clips in playback order without re-encoding | Use ordered paths **or** `--manifest FILE`, not both; `--output-path FILE` |
| `thea crop PATH WIDTH HEIGHT X Y` | Crop a pixel rectangle at top-left X,Y | `--output-path FILE` |
| `thea centercrop PATH WIDTH HEIGHT` | Center a pixel-sized crop | `--output-path FILE` |
| `thea ratiocrop PATH RATIOX RATIOY` | Center the largest exact aspect-ratio crop | `--output-path FILE` |
| `thea pan PATH` | Move a crop; defaults to 9:16, full source duration, left-to-right | `--resolutionx`, `--resolutiony`, `--ratiox`, `--ratioy`, `--startx`, `--starty`, `--endx`, `--endy`, `--duration`, `--output-path` |
| `thea caption PATH --model MODEL` | Sample frames and request a caption from a running vision endpoint | Endpoint, sampling, output and context options below |
| `thea index [ROOT] [LIMIT]` / `thea-index [ROOT] [LIMIT]` | Recursively index video metadata | `--db FILE`, `--probe`, `--geocode`, `--infer-loc` |

Pan accepts a complete pixel-dimension pair or ratio pair, not both. Coordinates
refer to the crop's top-left. Without horizontal travel it pans vertically.
Crop/pan preserve the existing API's codec, audio, duration and no-overwrite
contracts; see [crop/pan](docs/cropandpan/README.md).

Caption requires an image-capable `--model`; Thea does not download/start it.
Options: `--base-url` (default `http://localhost:1234/v1`),
`--api-key-env` (default `THEA_CAPTION_API_KEY`), `--timeout-sec` (120),
`--contact-sheet` (new JPEG; default unique file under `data_dir\captions`),
`--sampling-video`, `--sample-count` (12), `--frame-width` (176),
`--frame-height` (144), `--columns` (4), `--location-in-metadata`,
`--timestamp-in-metadata`, and `--context`. Credentials are read from the named
environment variable, not passed as CLI secrets.

Use `thea --help`, `thea COMMAND --help`, or `thea-index --help` for parser help;
`-h` is also supported. For indexing, pass `ROOT` explicitly (its current default
is `D:\`); optional `LIMIT` caps the number of indexed videos. Without `--db`,
the catalogue is in-memory only. `--geocode` and `--infer-loc` imply `--probe`;
see [indexing](docs/tools/README.md) for location inference behavior.

### Examples

```powershell
thea presets
thea pipeline "E:\videos\clip.mp4" --preset cinematic
thea analyze "E:\videos" --preset strict --output pkl --output-path "E:\reports\motion.pkl"
thea slice "E:\videos\clip.mp4" --preset permissive --output "E:\exports\clips"
thea downscale "E:\videos\clip.mp4" --width 640
thea merge first.mp4 second.mp4 --output-path "E:\exports\joined.mp4"
thea merge --manifest "E:\videos\clips.txt" --output-path "E:\exports\joined.mp4"
thea crop "E:\videos\clip.mp4" 1000 600 100 200
thea centercrop "E:\videos\clip.mp4" 1080 1080
thea ratiocrop "E:\videos\clip.mp4" 9 16
thea pan "E:\videos\clip.mp4"
thea caption "E:\videos\clip.mp4" --model "your-vision-model"
thea index "E:\videos" --db ".\data\videos.sqlite3"
thea-index "E:\videos" --db ".\data\videos.sqlite3" --probe
thea-index "E:\videos" 100 --db ".\data\videos.sqlite3" --geocode --infer-loc
```

`python -m main` is equivalent to `thea`; `python -m tools.walkdir` is equivalent
to `thea-index`. CLI options and Python package names are preserved. The old
root `main.py` moved to `src\main.py`; update launchers from `python main.py` to
`python -m main` after editable installation.

Fresh checkouts write pipeline output to `data`. Machine-specific output
locations belong in ignored `config\settings\settings.local.json`. See
[configuration](docs/configuration.md) for precedence and legacy path behavior.

Crop/pan, caption and index commands print JSON results; Python APIs remain
available. Other commands retain their existing human-readable logs.

## MCP

The root `mcp_server.py` launcher and `thea-mcp` entry point serve all twelve
commands as identically named MCP tools over stdio. Install the optional
`mcp` extra into the selected environment; see [MCP setup and examples](docs/mcp/README.md).
The checked-in `.vscode\mcp.json` includes a `thea` connection; existing external
connections are unchanged. Usage guidance lives in
`.github\skills\thea-mcp\SKILL.md`.

## Project and module index

| Document | Dev guide | Purpose |
|----------|-----------|---------|
| [Setup](docs/setup.md) | [Project development](docs/dev.readme.md) | Environment, editable install, architecture, tests, and ownership |
| [Configuration](docs/configuration.md) | [Video algorithm/model research](docs/analysis.md) | Presets/settings and research into motion, quality, captioning, and fidelity |
| [Pipeline](docs/pipeline/README.md) | [Development](docs/pipeline/dev.readme.md) | Unified CLI and video-processing orchestration |
| [Motion assessment](docs/motion_assessment/README.md) | [Development](docs/motion_assessment/dev.readme.md) | Optical flow, motion categories, and stable windows |
| [Downscaler](docs/downscaler/README.md) | [Development](docs/downscaler/dev.readme.md) | Single and batch downscaling |
| [Slicer](docs/slicer/README.md) | [Development](docs/slicer/dev.readme.md) | Stable-window clip extraction |
| [Merger](docs/merger/README.md) | [Development](docs/merger/dev.readme.md) | Ordered stream-copy concatenation |
| [Crop and pan](docs/cropandpan/README.md) | [Development](docs/cropandpan/dev.readme.md) | Validated crop, ratio fitting, and linear panning |
| [Video catalogue](docs/tools/README.md) | [Development](docs/tools/dev.readme.md) | Metadata, storage, search, geocoding, and indexing |
| [Sampled captioner](docs/sampled_captioner/README.md) | [Development](docs/sampled_captioner/dev.readme.md) | Contact-sheet sampling and optional vision backend |
| [MCP commands](docs/mcp/README.md) | [Development](docs/mcp/dev.readme.md) | Stdio server, matching CLI tools, structured results, and client configuration |
| [Shared utilities](docs/utils/README.md) | [Development](docs/utils/dev.readme.md) | Paths, configuration, FFmpeg discovery, logging, and metrics |
| [Agent tooling](docs/agents/README.md) | [Agent instructions](AGENTS.md) | Instruction precedence, skills, prompts, and external MCP clients |
| [Optional local AI setup](docs/setup.local-llm-mcp.md) | [CPU/GPU setup](docs/setup.gpu.md) | Existing editor and local-model integration guides |
| [Open work](docs/todo/README.md) | [Video research](docs/analysis.md) | Verified follow-ups and historical roadmaps |
