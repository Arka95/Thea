# Setup: OpenCV with CUDA (GPU Acceleration)

This guide documents the verified steps to set up OpenCV with CUDA support for GPU-accelerated optical flow and video processing on Windows.

---

## Versions Used (Verified Working — May 2026)

| Component | Version | Download URL |
|-----------|---------|-------------|
| NVIDIA Driver | 596.49 | https://www.nvidia.com/drivers |
| CUDA Toolkit | 13.3 (V13.3.33) | https://developer.nvidia.com/cuda-downloads |
| cuDNN | 9.23.0 | https://developer.nvidia.com/cudnn-downloads?target_os=Windows&target_arch=x86_64&target_version=11&target_type=exe_local |
| OpenCV (CUDA wheel) | 4.13.0.90 (built with CUDA 13.1) | https://github.com/cudawarped/opencv-python-cuda-wheels/releases/tag/4.13.0.90 |
| Python | 3.12.10 | https://www.python.org/downloads/ |
| GPU | RTX 4070 SUPER (Compute 8.9) | — |
| OS | Windows 11 | — |

---

## Windows Install Paths (Where Things End Up)

| Component | Install Path |
|-----------|-------------|
| CUDA Toolkit | `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\` |
| CUDA Runtime DLLs | `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin\x64\` |
| CUDA Static Libs | `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\lib\x64\` |
| cuDNN | `C:\Program Files\NVIDIA\CUDNN\v9.23\` |
| cuDNN DLLs | `C:\Program Files\NVIDIA\CUDNN\v9.23\bin\13.3\x64\` |
| cuDNN Headers | `C:\Program Files\NVIDIA\CUDNN\v9.23\include\13.3\` |
| cuDNN Libs | `C:\Program Files\NVIDIA\CUDNN\v9.23\lib\13.3\` |
| OpenCV (pip wheel) | `C:\Users\<user>\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_...\LocalCache\local-packages\Python312\site-packages\cv2\` |
| OpenCV config.py | `<cv2 path above>\config.py` |
| Python (MS Store) | `C:\Users\<user>\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.12_...\python.exe` |

### How to find the active OpenCV being used

```powershell
python -c "import cv2, os; print(os.path.dirname(cv2.__file__))"
```

On this machine:
```
C:\Users\bhowmikarka\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\site-packages\cv2
```

---

## Prerequisites

- **GPU**: NVIDIA GPU with Compute Capability ≥ 7.5
- **OS**: Windows 10/11
- **Python 3.12+**
- **NVIDIA Driver**: 525+ (standard Game Ready / Studio driver)

---

## Step 1: Install CUDA Toolkit 13.3

1. Download from: https://developer.nvidia.com/cuda-downloads
   - Select: Windows → x86_64 → 11 → exe (local)
2. Run the installer → **Express** installation
3. Open a **new** terminal and verify:
   ```
   nvcc --version
   ```
   Expected: `Cuda compilation tools, release 13.3`

4. Confirm DLLs are present:
   ```
   dir "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin\x64\cudart64_13.dll"
   ```

### CUDA Toolkit via pip? (No)

NVIDIA provides runtime packages on pip (`nvidia-cuda-runtime-cu13`, etc.). These are only for **running** pre-built CUDA apps (PyTorch, etc.) — they don't include the full runtime DLLs that OpenCV loads.

| Approach | Use Case | Provides |
|----------|----------|----------|
| `pip install nvidia-cuda-runtime-cu13` | Running PyTorch/TensorFlow | Subset of runtime DLLs |
| Full CUDA Toolkit installer | Using CUDA OpenCV (prebuilt or source) | All runtime DLLs, nvcc, headers, static libs |

> Even for the prebuilt wheel path, you need the full toolkit because OpenCV loads CUDA DLLs from the toolkit's `bin\x64\` directory at runtime.

---

## Step 2: Install cuDNN 9.23

1. Download from: https://developer.nvidia.com/cudnn-downloads?target_os=Windows&target_arch=x86_64&target_version=11&target_type=exe_local
2. Run the `.exe` installer — it places files automatically
3. Verify:
   ```
   dir "C:\Program Files\NVIDIA\CUDNN\v9.23\bin\13.3\x64\cudnn64_9.dll"
   ```

Resulting directory structure:
```
C:\Program Files\NVIDIA\CUDNN\v9.23\
├── bin\
│   ├── 12.9\x64\    ← DLLs for CUDA 12.9
│   └── 13.3\x64\    ← DLLs for CUDA 13.3 (ours)
├── include\
│   ├── 12.9\        ← headers for CUDA 12.9
│   └── 13.3\        ← headers for CUDA 13.3 (ours)
└── lib\
    ├── 12.9\        ← link libs for CUDA 12.9
    └── 13.3\        ← link libs for CUDA 13.3 (ours)
```

---

## Step 3: Install Prebuilt CUDA OpenCV Wheel (Recommended)

Building from source with CUDA 13.3 currently fails (see Appendix A). Use a prebuilt wheel instead.

### 3a: Check for Compatible Wheels

Repository: https://github.com/cudawarped/opencv-python-cuda-wheels/releases

Match these **three things**:

| Factor | How to check yours | Compatibility rule |
|--------|-------------------|-------------------|
| **CUDA version** | `nvcc --version` | Major version must match. CUDA 13.3 works with wheels built for 13.0/13.1 (forward-compatible) |
| **Python version** | `python --version` | Must be compatible. This wheel uses `cp37-abi3` (stable ABI), works with Python 3.7+ |
| **GPU Compute Capability** | `nvidia-smi --query-gpu=compute_cap --format=csv` | Your arch must be in the wheel's `CUDA_ARCH_BIN` list. Release 4.13.0.90 covers: 7.5, 8.0, 8.6, **8.9**, 9.0, 10.0, 12.0 |

### 3b: Download the Wheel

```powershell
# Download (185 MB)
Invoke-WebRequest -Uri "https://github.com/cudawarped/opencv-python-cuda-wheels/releases/download/4.13.0.90/opencv_contrib_python-4.13.0.90-cp37-abi3-win_amd64.whl" -OutFile opencv_cuda.whl
```

Wheel details:
- Built with: CUDA 13.1, cuDNN 9.17.1, Video Codec SDK 13.0
- GPU archs included: 7.5, 8.0, 8.6, **8.9**, 9.0, 10.0, 12.0
- Uses stable ABI (`cp37-abi3`) — works with Python 3.7 through 3.14+

### 3c: Install

```powershell
pip uninstall opencv-python opencv-contrib-python -y
pip install opencv_cuda.whl
```

### 3d: Configure DLL Paths

The wheel needs to find CUDA and cuDNN DLLs at runtime. Edit `cv2/config.py`:

1. Find the file:
   ```powershell
   python -c "import importlib.util; print(importlib.util.find_spec('cv2').submodule_search_locations[0] + '\\config.py')"
   ```

2. Edit it to contain:
   ```python
   import os

   BINARIES_PATHS = [
       os.path.join(os.path.join(LOADER_DIR, '../../'), 'x64/vc17/bin'),
       os.path.join(os.getenv('CUDA_PATH', 'C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.3'), 'bin/x64'),
       'C:/Program Files/NVIDIA/CUDNN/v9.23/bin/13.3/x64'
   ] + BINARIES_PATHS
   ```

> **Key gotcha**: CUDA 13.3 puts DLLs in `bin/x64/` (not `bin/`). cuDNN 9.23 puts DLLs in `bin/13.3/x64/` (not `bin/13.3/`). Getting these wrong causes `ImportError: DLL load failed`.

---

## Step 4: Verify Installation

```python
import cv2
print(f'OpenCV version: {cv2.__version__}')            # 4.13.0
print(f'CUDA devices: {cv2.cuda.getCudaEnabledDeviceCount()}')  # 1
flow = cv2.cuda.FarnebackOpticalFlow.create()          # Should not error
print('CUDA Farneback Optical Flow: available')
```

Expected output:
```
OpenCV version: 4.13.0
CUDA devices: 1
CUDA Farneback Optical Flow: available
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ImportError: DLL load failed` | Check `cv2/config.py` paths. CUDA DLLs are in `bin/x64/`, cuDNN in `bin/13.3/x64/` |
| `CUDA devices: 0` | Verify NVIDIA driver: `nvidia-smi`. Ensure toolkit is installed (not just driver) |
| cuDNN functions fail | Ensure cuDNN CUDA major version matches toolkit (both 13.x) |
| `nvcc` not found | Open new terminal after install; check PATH includes CUDA toolkit |
| Wrong OpenCV loaded | Run `python -c "import cv2, os; print(os.path.dirname(cv2.__file__))"` to check which cv2 is active |
| Multiple OpenCV installs conflict | `pip list | findstr opencv` — uninstall all, then install only the CUDA wheel |

---

## Project Integration

The Thea project uses this CUDA-enabled OpenCV via pip. `requirements.txt` specifies:
```
opencv-contrib-python==4.13.0.90
```

No `.pth` files or system PATH changes needed beyond the one-time `cv2/config.py` edit (Step 3d).

---

---

## Appendix A: Building from Source (Reference — Currently Broken with CUDA 13.3)

> **Status (May 2026)**: Building OpenCV from source with CUDA 13.3 fails due to `nvcc` template parsing changes in the `cudev` contrib module (`opencv_contrib/modules/cudev/include/opencv2/cudev/grid/copy.hpp`). Both the `4.13.0` tag and latest `4.x` branch are affected. Use prebuilt wheels until upstream fixes this.

If a future CUDA or OpenCV version resolves this, here are the build requirements:

### Build Prerequisites

```powershell
# Visual Studio Build Tools (C++ compiler, no IDE needed)
winget install Microsoft.VisualStudio.2022.BuildTools --override "--add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --add Microsoft.Component.MSBuild --passive --wait"

# Windows SDK (provides rc.exe resource compiler needed for linking)
winget install Microsoft.WindowsSDK.10.0.26100 --accept-package-agreements --accept-source-agreements
```

Build Tools install to: `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\`

### Clone Source

```powershell
git clone --depth 1 --branch 4.x https://github.com/opencv/opencv.git C:\Projects\opencv_build\opencv
git clone --depth 1 --branch 4.x https://github.com/opencv/opencv_contrib.git C:\Projects\opencv_build\opencv_contrib
```

### CMake Configure (via batch file — vcvars64 must be loaded first)

```batch
@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
set PATH=<path-to-ninja>;<CUDA-toolkit>\bin;%PATH%
set CUDA_PATH=C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.3
cd /d "C:\Projects\opencv_build\build"

cmake -G Ninja ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DCMAKE_INSTALL_PREFIX=C:/Projects/opencv_build/install ^
  -DOPENCV_EXTRA_MODULES_PATH=C:/Projects/opencv_build/opencv_contrib/modules ^
  -DWITH_CUDA=ON -DWITH_CUDNN=ON -DOPENCV_DNN_CUDA=ON ^
  -DENABLE_FAST_MATH=ON -DCUDA_FAST_MATH=ON ^
  -DCUDA_ARCH_BIN=8.9 ^
  -DCUDA_TOOLKIT_ROOT_DIR="C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.3" ^
  -DCUDNN_INCLUDE_DIR="C:/Program Files/NVIDIA/CUDNN/v9.23/include/13.3" ^
  -DCUDNN_LIBRARY="C:/Program Files/NVIDIA/CUDNN/v9.23/lib/13.3/cudnn.lib" ^
  -DBUILD_opencv_python3=ON -DBUILD_TESTS=OFF -DBUILD_PERF_TESTS=OFF ^
  -DBUILD_EXAMPLES=OFF -DBUILD_opencv_world=ON ^
  ../opencv
```

> **Important**: Use forward slashes (`/`) in all CMake path values to avoid `Invalid character escape` errors with CMake's `FindCUDA.cmake`.

### Build & Install

```powershell
cmake --build . --config Release --parallel 12   # 30-60 min
cmake --install . --config Release
```

### Configure Python (source build only)

```powershell
pip uninstall opencv-python opencv-contrib-python -y
$sitePackages = python -c "import site; print(site.getsitepackages()[0])"
Set-Content "$sitePackages\opencv_cuda.pth" "C:\Projects\opencv_build\install\python"
# Also add to system PATH: C:\Projects\opencv_build\install\x64\vc17\bin
```
