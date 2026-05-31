# Setup: OpenCV with CUDA (GPU Acceleration)

This guide walks through getting OpenCV with CUDA support for GPU-accelerated optical flow and video processing. There are two paths — using a prebuilt wheel (fast) or building from source (optimized for your exact GPU).

## Prerequisites

- **GPU**: NVIDIA GPU with Compute Capability 5.0+ (RTX 4070 SUPER = 8.9)
- **OS**: Windows 10/11
- **Python 3.12+**
- **Git**
- **NVIDIA Driver**: 525+ (standard Game Ready / Studio driver)

---

## Step 1: Install CUDA Toolkit

### Why the full installer (not pip)?

NVIDIA provides CUDA runtime packages on pip (`nvidia-cuda-runtime-cu13`, `nvidia-cuda-nvcc-cu13`, etc.). These are sufficient for **running** pre-built CUDA applications (e.g., PyTorch, TensorFlow). However, **building OpenCV from source** requires:

- The `nvcc` compiler with full headers to compile OpenCV's CUDA kernels
- Static libraries (`cudart_static.lib`) for linking
- cuDNN development headers (`cudnn.h`) for compile-time integration

The pip packages only ship runtime DLLs and lack the development headers/static libs that CMake needs during the build process.

| Approach | Use Case | Provides |
|----------|----------|----------|
| `pip install nvidia-cuda-runtime-cu13` | Running pre-built CUDA apps (PyTorch, etc.) | Runtime DLLs only |
| Full CUDA Toolkit installer | Compiling CUDA code from source (our case) | nvcc, headers, static libs, tools |

### Option A: Full Installer (Required for building OpenCV from source)

1. Download from: https://developer.nvidia.com/cuda-downloads
   - Select: Windows → x86_64 → 11 → exe (local)
2. Run the installer and choose **Express** installation
3. After install, open a **new** terminal and verify:
   ```
   nvcc --version
   ```

4. Confirm the install path exists (adjust version number as needed):
   ```
   dir "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3"
   ```

### Option B: pip install (Only if using prebuilt wheels, NOT for building from source)

If you're using prebuilt CUDA wheels or other pre-built CUDA packages (e.g., PyTorch):
```powershell
pip install nvidia-cuda-runtime-cu13 nvidia-cuda-nvcc-cu13 nvidia-cublas-cu13
```
> ⚠️ This will **not** work for building OpenCV from source. Use Option A for that.

---

## Step 2: Install cuDNN 9.23

1. Download from: https://developer.nvidia.com/cudnn-downloads?target_os=Windows&target_arch=x86_64&target_version=11&target_type=exe_local
   - Select the version compatible with your CUDA toolkit version
2. Run the `.exe` installer — it automatically places files in the correct directories
3. Verify cuDNN is installed:
   ```
   dir "C:\Program Files\NVIDIA\CUDNN\v9.23\bin\13.3\cudnn*.dll"
   ```

---

## Step 3: Check for Prebuilt CUDA OpenCV Wheels (Recommended First)

Before spending 30-60 minutes building from source, check if a compatible prebuilt wheel exists.

### Source: cudawarped/opencv-python-cuda-wheels

Repository: https://github.com/cudawarped/opencv-python-cuda-wheels/releases

### How to check compatibility

You need to match **three things**:

| Factor | How to check | Example |
|--------|-------------|---------|
| **CUDA version** | `nvcc --version` | CUDA 13.3 → wheels built for 13.0/13.1 are compatible (forward-compatible runtime) |
| **Python version** | `python --version` | Python 3.12 → look for `cp312` in wheel filename |
| **GPU Compute Capability** | `nvidia-smi --query-gpu=compute_cap --format=csv` | 8.9 → must be within the wheel's arch range (usually 7.5-12.1) |

### Compatibility rules

- **CUDA version**: Wheels built for CUDA 13.0 or 13.1 work with CUDA 13.3 installed (runtime is backward-compatible with newer drivers/toolkits). The major version must match.
- **Python version**: Must be exact match (cp312 = Python 3.12 only).
- **GPU arch**: Your compute capability must be within the range the wheel was compiled for. Check the release notes — typically `CUDA_ARCH_BIN=7.5;8.0;8.6;8.9;9.0;10.0;12.0`.

### Wheel filename format

```
opencv_contrib_python_cuda-4.13.0.20250811-cp312-cp312-win_amd64.whl
│                          │               │     │     │
│                          │               │     │     └── Platform (Windows 64-bit)
│                          │               │     └── Python ABI
│                          │               └── Python version (3.12)
│                          └── OpenCV version + build date
└── Package name (with CUDA + contrib)
```

### Installation (if compatible wheel found)

```powershell
# Remove existing opencv
pip uninstall opencv-python opencv-contrib-python -y

# Install the CUDA wheel (download .whl first, or use direct URL)
pip install opencv_contrib_python_cuda-4.13.0.20250811-cp312-cp312-win_amd64.whl
```

### When to build from source instead

- No wheel matches your Python version
- You need a newer OpenCV version than what's available
- You want maximum performance (wheel compiled for your exact GPU arch only = smaller binary, slightly faster)
- You need specific modules enabled/disabled
- Your CUDA major version doesn't match any available wheel

---

## Step 4: Build from Source (If No Compatible Wheel Found)

### 4a: Install Build Tools

You need a C++ compiler. Install **Visual Studio Build Tools** (no IDE required):

```powershell
# Run in admin PowerShell
winget install Microsoft.VisualStudio.2022.BuildTools --override "--add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --add Microsoft.Component.MSBuild --passive --wait"
```

You also need the **Windows SDK**:
```powershell
winget install Microsoft.WindowsSDK.10.0.26100 --accept-package-agreements --accept-source-agreements
```

### 4b: Clone OpenCV Source

```powershell
mkdir C:\Projects\opencv_build
cd C:\Projects\opencv_build

# Use the latest 4.x branch (better CUDA compatibility than tagged releases)
git clone --depth 1 --branch 4.x https://github.com/opencv/opencv.git
git clone --depth 1 --branch 4.x https://github.com/opencv/opencv_contrib.git
```

> **Note**: Tagged releases (e.g., 4.13.0) may have CUDA compatibility issues with newer toolkit versions. The `4.x` branch includes fixes.

### 4c: Configure CMake Build

Create a `configure.bat` file:

```batch
@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
set PATH=C:\Program Files\Microsoft Visual Studio\2022\Enterprise\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin;%PATH%
set CUDA_PATH=C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.3
cd /d "C:\Projects\opencv_build\build"

cmake -G Ninja ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DCMAKE_INSTALL_PREFIX=C:/Projects/opencv_build/install ^
  -DOPENCV_EXTRA_MODULES_PATH=C:/Projects/opencv_build/opencv_contrib/modules ^
  -DWITH_CUDA=ON ^
  -DWITH_CUDNN=ON ^
  -DOPENCV_DNN_CUDA=ON ^
  -DENABLE_FAST_MATH=ON ^
  -DCUDA_FAST_MATH=ON ^
  -DCUDA_ARCH_BIN=8.9 ^
  -DCUDA_TOOLKIT_ROOT_DIR="C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.3" ^
  -DWITH_NVCUVID=ON ^
  -DWITH_NVCUVENC=ON ^
  -DBUILD_opencv_python3=ON ^
  -DPYTHON3_EXECUTABLE=C:/Users/bhowmikarka/AppData/Local/Microsoft/WindowsApps/PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0/python.exe ^
  -DCUDNN_INCLUDE_DIR="C:/Program Files/NVIDIA/CUDNN/v9.23/include/13.3" ^
  -DCUDNN_LIBRARY="C:/Program Files/NVIDIA/CUDNN/v9.23/lib/13.3/cudnn.lib" ^
  -DBUILD_TESTS=OFF ^
  -DBUILD_PERF_TESTS=OFF ^
  -DBUILD_EXAMPLES=OFF ^
  -DBUILD_opencv_world=ON ^
  ../opencv
```

> **Important**: Use forward slashes (`/`) in CMake paths to avoid escape character issues. Set `CUDA_ARCH_BIN` to your GPU's compute capability. Check with: `nvidia-smi --query-gpu=compute_cap --format=csv`.

Run it:
```powershell
mkdir C:\Projects\opencv_build\build
C:\Projects\opencv_build\configure.bat
```

Verify the CMake output shows:
```
NVIDIA CUDA:  YES
cuDNN:        YES
Python 3:     (your python path)
```

### 4d: Build OpenCV

Create a `build.bat`:
```batch
@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
set PATH=C:\Program Files\Microsoft Visual Studio\2022\Enterprise\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin;%PATH%
cd /d "C:\Projects\opencv_build\build"
cmake --build . --config Release --parallel 12
```

```powershell
C:\Projects\opencv_build\build.bat
```

This takes 30-60 minutes. The `--parallel 12` flag uses 12 CPU cores.

### 4e: Install

```batch
cmake --install . --config Release
```

This installs to `C:\Projects\opencv_build\install\`.

---

## Step 5: Configure Python to Use CUDA OpenCV

> Skip this if you used a prebuilt wheel from Step 3 — pip handles this automatically.

1. Find the built Python binding:
   ```
   dir C:\Projects\opencv_build\install\python\cv2\*.pyd
   ```

2. Remove the pip-installed opencv-python (if any):
   ```
   pip uninstall opencv-python opencv-contrib-python -y
   ```

3. Add the built OpenCV to your Python path. Create/edit a `.pth` file:
   ```powershell
   $pythonSitePackages = python -c "import site; print(site.getsitepackages()[0])"
   Set-Content "$pythonSitePackages\opencv_cuda.pth" "C:\Projects\opencv_build\install\python"
   ```

4. Add DLLs to system PATH (add to your environment variables permanently):
   ```
   C:\Projects\opencv_build\install\x64\vc17\bin
   ```

---

## Step 6: Verify CUDA OpenCV

```python
import cv2
print(cv2.__version__)          # Should print 4.13.0
print(cv2.cuda.getCudaEnabledDeviceCount())  # Should print 1 or more
print(cv2.getBuildInformation()) # Look for "NVIDIA CUDA: YES" in output
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `nvcc` not found | Restart terminal; check `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin` is in PATH |
| CMake can't find CUDA | Set `CUDA_TOOLKIT_ROOT_DIR` explicitly with **forward slashes** in CMake command |
| CMake `Invalid character escape '\P'` | Use forward slashes (`/`) not backslashes (`\`) in all CMake path variables |
| OpenCV 4.13.0 tag fails with CUDA 13.3 | Use the `4.x` branch instead of a tagged release — it has compatibility fixes |
| cuDNN not detected | Ensure cuDNN DLLs are in the CUDA `bin\` directory |
| Python binding not built | Check CMake output for `Python 3` section; ensure `PYTHON3_EXECUTABLE` points to correct python |
| `ImportError: DLL load failed` | Add OpenCV's bin directory to system PATH |
| Build fails with compute capability error | Ensure `CUDA_ARCH_BIN` matches your GPU |

---

## Project Integration

After setup, the Thea project uses this CUDA-enabled OpenCV automatically. The `requirements.txt` lists `opencv-python` but the `.pth` file ensures Python loads the locally-built CUDA version instead.
