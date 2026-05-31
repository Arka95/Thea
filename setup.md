# Setup: OpenCV with CUDA (GPU Acceleration)

This guide walks through building OpenCV 4.13.0 from source with CUDA support for GPU-accelerated optical flow and video processing.

## Prerequisites

- **GPU**: NVIDIA GPU with Compute Capability 5.0+ (RTX 4070 SUPER = 8.9)
- **OS**: Windows 10/11
- **Visual Studio 2022** (with C++ Desktop Development workload)
- **Python 3.12+**
- **Git**

---

## Step 1: Install CUDA Toolkit 13.2

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

### Option A: Full Installer (Required for building OpenCV)

1. Download from: https://developer.nvidia.com/cuda-downloads
   - Select: Windows → x86_64 → 11 → exe (local)
2. Run the installer and choose **Express** installation
3. After install, open a **new** terminal and verify:
   ```
   nvcc --version
   ```
   Expected output should show `release 13.2`.

4. Confirm the install path exists:
   ```
   dir "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.2"
   ```

### Option B: pip install (Only if using pre-built CUDA packages, NOT for building OpenCV)

If you're working on a different project that only needs CUDA runtime (e.g., running PyTorch):
```powershell
pip install nvidia-cuda-runtime-cu13 nvidia-cuda-nvcc-cu13 nvidia-cublas-cu13
```
> ⚠️ This will **not** work for our OpenCV CUDA build. Use Option A above.

---

## Step 2: Install cuDNN 9.23

1. Download from: https://developer.nvidia.com/cudnn-downloads?target_os=Windows&target_arch=x86_64&target_version=11&target_type=exe_local
   - Select the version compatible with CUDA 13.x
2. Run the `.exe` installer — it will automatically place files in the correct CUDA directories
3. Verify cuDNN is installed:
   ```
   dir "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.2\bin\cudnn*.dll"
   ```
   You should see `cudnn64_9.dll` (or similar).

---

## Step 3: Clone OpenCV Source

```powershell
mkdir C:\Projects\opencv_build
git clone --depth 1 --branch 4.13.0 https://github.com/opencv/opencv.git C:\Projects\opencv_build\opencv
git clone --depth 1 --branch 4.13.0 https://github.com/opencv/opencv_contrib.git C:\Projects\opencv_build\opencv_contrib
```

---

## Step 4: Configure CMake Build

Open a **Developer Command Prompt for VS 2022** (or PowerShell with VS env loaded):

```powershell
mkdir C:\Projects\opencv_build\build
cd C:\Projects\opencv_build\build

cmake -G "Visual Studio 17 2022" -A x64 ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DCMAKE_INSTALL_PREFIX=C:\Projects\opencv_build\install ^
  -DOPENCV_EXTRA_MODULES_PATH=C:\Projects\opencv_build\opencv_contrib\modules ^
  -DWITH_CUDA=ON ^
  -DWITH_CUDNN=ON ^
  -DOPENCV_DNN_CUDA=ON ^
  -DENABLE_FAST_MATH=ON ^
  -DCUDA_FAST_MATH=ON ^
  -DCUDA_ARCH_BIN=8.9 ^
  -DWITH_NVCUVID=ON ^
  -DWITH_NVCUVENC=ON ^
  -DBUILD_opencv_python3=ON ^
  -DPYTHON3_EXECUTABLE=python ^
  -DBUILD_TESTS=OFF ^
  -DBUILD_PERF_TESTS=OFF ^
  -DBUILD_EXAMPLES=OFF ^
  -DBUILD_opencv_world=ON ^
  ..\opencv
```

> **Note**: Set `CUDA_ARCH_BIN` to your GPU's compute capability. RTX 4070 SUPER = `8.9`. Check yours with `nvidia-smi --query-gpu=compute_cap --format=csv`.

---

## Step 5: Build OpenCV

```powershell
cmake --build . --config Release --parallel 12
```

This will take 30-60 minutes depending on your CPU. The `--parallel 12` flag uses 12 cores.

---

## Step 6: Install

```powershell
cmake --install . --config Release
```

This installs to `C:\Projects\opencv_build\install\`.

---

## Step 7: Configure Python to Use CUDA OpenCV

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

## Step 8: Verify CUDA OpenCV

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
| `nvcc` not found | Restart terminal; check `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.2\bin` is in PATH |
| CMake can't find CUDA | Set `CUDA_TOOLKIT_ROOT_DIR` explicitly in CMake command |
| cuDNN not detected | Ensure cuDNN DLLs are in the CUDA `bin\` directory |
| Python binding not built | Check CMake output for `Python 3` section; ensure `PYTHON3_EXECUTABLE` points to correct python |
| `ImportError: DLL load failed` | Add OpenCV's bin directory to system PATH |
| Build fails with compute capability error | Ensure `CUDA_ARCH_BIN` matches your GPU |

---

## Project Integration

After setup, the Thea project uses this CUDA-enabled OpenCV automatically. The `requirements.txt` lists `opencv-python` but the `.pth` file ensures Python loads the locally-built CUDA version instead.
