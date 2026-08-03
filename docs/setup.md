# Thea Project Setup

This is the main setup entry point for Thea. Complete the guides in this order:

1. **System tools and acceleration:** [`setup.gpu.md`](setup.gpu.md)
2. **Python project environment:** this guide
3. **Optional local AI tooling:** [`setup.local-llm-mcp.md`](setup.local-llm-mcp.md)

The local AI setup is optional. The GPU/tool and Python setup steps are required.

## Verified Python environment

Validated on 2026-08-03:

| Component | Version |
|-----------|---------|
| Python | 3.12.10 |
| pip | 26.2 |
| OpenCV | 4.13.0.90 |
| NumPy | 2.5.1 |
| SciPy | 1.18.0 |
| pytest | 9.1.1 |

## 1. Complete the system tool setup

Follow [`setup.gpu.md`](setup.gpu.md) first. It installs FFmpeg and, for GPU
mode, the NVIDIA driver, CUDA Toolkit, and cuDNN. It also explains whether to
select `requirements-cpu.txt` or `requirements-cuda.txt`.

## 2. Create the project-local environment

Install Python 3.12 when it is not already available:

```powershell
winget install --id Python.Python.3.12 --exact
```

Open a new PowerShell window, then run:

```powershell
cd C:\projects\Thea
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

All Thea Python commands must use this `.venv`. Do not install project
dependencies into the global Python environment.

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

Do not install both OpenCV variants into the same `.venv`. If switching modes,
delete and recreate `.venv`.

## Requirements layout

| File | Responsibility |
|------|----------------|
| `requirements.txt` | Shared runtime packages, excluding OpenCV |
| `requirements-cpu.txt` | Shared runtime plus PyPI CPU OpenCV |
| `requirements-cuda.txt` | Shared runtime plus the verified CUDA OpenCV wheel |
| `requirements-dev.txt` | Shared runtime plus tests, linting, and profiling |
| `requirements-mcp.txt` | Optional Python dependency for Thea's Git MCP server |

## 4. Verify the Python project

With `.venv` activated:

```powershell
python -m pip check
python main.py presets
python -m pytest tests tools\tests -q
```

Expected result:

```text
178 passed
```

For GPU mode, also run the GPU verification command from `setup.gpu.md`.

## Daily usage

Activate the environment whenever opening a new terminal:

```powershell
cd C:\projects\Thea
.\.venv\Scripts\Activate.ps1
```

Alternatively, invoke the environment explicitly:

```powershell
.\.venv\Scripts\python.exe main.py presets
.\.venv\Scripts\python.exe -m pytest tests tools\tests
```

## Optional final step

To use Qwen 3 and Thea's project MCP servers from VS Code, continue with:

[`setup.local-llm-mcp.md`](setup.local-llm-mcp.md)
