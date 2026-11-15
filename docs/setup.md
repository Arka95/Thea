# Thea Project Setup

[Back to Thea](../README.md) | [Developer guide](dev.readme.md)

This is the main setup entry point for Thea. Complete the guides in this order:

1. **System tools and acceleration:** [`setup.gpu.md`](setup.gpu.md)
2. **Python project environment:** this guide
3. **Optional local AI tooling:** [`setup.local-llm-mcp.md`](setup.local-llm-mcp.md)

The local AI setup is optional. The GPU/tool and Python setup steps are required.

## 1. Complete the system tool setup

Follow [`setup.gpu.md`](setup.gpu.md) first. It installs FFmpeg and, for GPU
mode, the NVIDIA driver, CUDA Toolkit, and cuDNN. It also explains whether to
select `requirements-cpu.txt` or `requirements-cuda.txt`.

## 2. Select a compatible Python environment

Prefer the existing shared workspace Python environment when its dependencies
are compatible. Do not install into an unrelated system interpreter.
Thea's existing ignored `.venv` is retained as a CUDA/OpenCV isolation exception:
do not replace its working backend merely to consolidate directories.

The commands below create that isolated environment only when one is needed;
otherwise activate the compatible shared environment and skip creation.

Install Python 3.12 when it is not already available:

```powershell
winget install --id Python.Python.3.12 --exact
```

Open a new PowerShell window, then run:

```powershell
cd C:\projectWorkspace\Thea
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Run installation, tests and CLI commands with the selected interpreter.
Do not install both CPU and CUDA OpenCV into the same environment or replace
another project's working stack.

The repository already ignores `.venv/` in `.gitignore`.

## 3. Install project and developer dependencies

Install the shared runtime, tests, quality tools, and profiler:

```powershell
python -m pip install -r requirements-dev.txt
```

Then install exactly one OpenCV variant.

### CUDA GPU mode

```powershell
python -m pip install -r requirements-cuda.txt
```

Complete the
[`Configure CUDA OpenCV DLL paths`](setup.gpu.md#configure-cuda-opencv-dll-paths)
section before importing OpenCV.

### CPU mode

```powershell
python -m pip install -r requirements-cpu.txt
```

CPU mode does not require CUDA or cuDNN. Thea automatically falls back to its
CPU optical-flow implementation when no CUDA device is available.

If switching modes, create a separately named ignored `.venv-*` environment
rather than deleting or mutating the working one.

### Register the source checkout

After runtime dependencies and exactly one OpenCV variant are installed:

```powershell
python -m pip install --no-deps -e .
```

This registers the `src` packages and the `thea`/`thea-index` entry points
without changing the selected runtime stack. A standalone wheel deployment is
not yet supported because settings/presets remain checkout-relative.

## Requirements layout

| File | Responsibility |
|------|----------------|
| `pyproject.toml` | Editable packaging, console entry points, supported Python and unit-test discovery |
| `requirements.txt` | Shared runtime packages, excluding OpenCV |
| `requirements-cpu.txt` | Shared runtime plus PyPI CPU OpenCV |
| `requirements-cuda.txt` | Shared runtime plus the verified CUDA OpenCV wheel |
| `requirements-dev.txt` | Shared runtime plus tests, linting, and profiling |
| `requirements-mcp.txt` | Optional Python dependency for Thea's Git MCP server |

## 4. Verify the Python project

With the selected environment activated:

```powershell
python -m pip check
python -m main presets
# check that tests pass
python -m pytest -q
```


Real-media/GPU/dataset checks are not part of this default unit command.
Only when explicitly requested, use `python -m pytest src\integration_tests -q`
and the GPU verification steps from `setup.gpu.md`.

## Daily usage

Activate the selected environment whenever opening a new terminal. For the
existing isolated CUDA environment:

```powershell
cd C:\projectWorkspace\Thea
.\.venv\Scripts\Activate.ps1
```

Alternatively, invoke the environment explicitly:

```powershell
.\.venv\Scripts\python.exe -m main presets
.\.venv\Scripts\python.exe -m pytest
```

## Optional final step

To use Qwen 3 and Thea's project MCP servers from VS Code, continue with:

[`setup.local-llm-mcp.md`](setup.local-llm-mcp.md)
