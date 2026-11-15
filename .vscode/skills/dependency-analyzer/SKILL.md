---
name: dependency-analyzer
description: Analyze Thea's actual Python and system dependencies for updates, vulnerabilities, and compatibility risks.
user-invocable: true
disable-model-invocation: false
---

# Dependency Analyzer

Analyze only dependencies used by Thea's source, tests, workspace tasks, and
documented project tooling.

## Dependency sources

| File | Scope |
|------|-------|
| `requirements.txt` | Platform-independent runtime |
| `requirements-cuda.txt` | Runtime plus CUDA-enabled OpenCV |
| `requirements-cpu.txt` | Runtime plus CPU OpenCV |
| `requirements-dev.txt` | Tests, quality tools, and profiling |
| `requirements-mcp.txt` | Optional Git MCP client dependency |
| `docs/setup.gpu.md` | NVIDIA, CUDA, cuDNN, FFmpeg, and OpenCV mode |
| `docs/setup.md` | Project-local Python environment |

Do not infer dependencies from unrelated experiments or optional documentation.

## Verified environment

Validated together on Windows on 2026-08-03:

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | 3.12.10 | Runtime |
| NVIDIA driver | 591.86 | GPU driver |
| CUDA Toolkit | 13.3 (`V13.3.73`) | CUDA runtime and compiler |
| cuDNN | 9.23.0.39 | DLL dependency of the CUDA OpenCV wheel |
| OpenCV CUDA wheel | 4.13.0.90 | Video I/O and CUDA optical flow |
| FFmpeg | 8.1.2 | Lossless slicing and metadata probing |
| NumPy | 2.5.1 | Array operations |
| SciPy | 1.18.0 | Motion-score smoothing |
| imageio-ffmpeg | 0.6.0 | Managed FFmpeg fallback |
| reverse-geocoder | 1.5.1 | Offline coordinate lookup |
| pycountry | 26.2.16 | Country metadata |
| pytest | 9.1.1 | Test runner |

## Workflow

1. Activate the project environment:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. Check requirement consistency:

   ```powershell
   python -m pip check
   python -m pip list --outdated
   ```

3. Confirm the CUDA wheel was not replaced by a CPU wheel:

   ```powershell
   python -c "import cv2; print(cv2.__version__); print(cv2.cuda.getCudaEnabledDeviceCount())"
   ```

4. Run dependency and security checks when installed:

   ```powershell
   python -m pip install pip-audit
   python -m pip_audit
   bandit -r . -ll
   ```

5. Run the complete test suite:

   ```powershell
   python -m pytest tests tools\tests -q
   ```

## Compatibility rules

- Keep Python packages inside `.venv`.
- Install OpenCV through `requirements-cuda.txt` or `requirements-cpu.txt`;
  installing `opencv-contrib-python` directly from PyPI selects the CPU wheel.
- CUDA 13.3 can run the OpenCV wheel built with CUDA 13.1.
- Keep cuDNN's CUDA major version aligned with the toolkit.
- After recreating `.venv`, restore the DLL paths in `cv2/config.py` as
  documented in `docs/setup.gpu.md`.
- Treat OpenCV, CUDA, cuDNN, NumPy major versions, and Python upgrades as
  high-risk changes requiring the complete test suite and a GPU smoke test.
