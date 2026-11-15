# Thea GPU and System Tool Setup

This guide covers only system tools and OpenCV acceleration selection. Python
project compilation and package installation are handled by
[`setup.md`](setup.md).

## Choose an acceleration mode

| Mode | OpenCV requirements file | System requirements |
|------|--------------------------|---------------------|
| CUDA GPU | `requirements-cuda.txt` | NVIDIA GPU, driver, CUDA 13.3, cuDNN 9.23 |
| CPU | `requirements-cpu.txt` | FFmpeg only |

GPU mode is recommended for Thea's optical-flow workload. CPU mode remains
fully supported but is slower.

## Verified GPU toolchain

Validated together on 2026-08-03:

| Component | Version |
|-----------|---------|
| NVIDIA driver | 591.86 |
| CUDA Toolkit | 13.3 (`V13.3.73`) |
| cuDNN | 9.23.0.39 for CUDA 13 |
| OpenCV CUDA wheel | 4.13.0.90, built with CUDA 13.1 |
| FFmpeg | 8.1.2 |
| GPU | RTX 4070 SUPER, compute capability 8.9 |

The exact driver version does not need to match. Use a current driver that
supports CUDA 13 and the installed GPU.

## Install FFmpeg

FFmpeg is required in both CPU and GPU modes:

```powershell
winget install --id Gyan.FFmpeg --exact
```

Open a new terminal and verify:

```powershell
ffmpeg -version
ffprobe -version
```

CPU users can now continue with [`setup.md`](setup.md) and select
`requirements-cpu.txt`.

## Install the NVIDIA GPU toolchain

The remaining sections are required only for CUDA GPU mode.

### NVIDIA driver

Install a current NVIDIA Game Ready or Studio driver:

```text
https://www.nvidia.com/drivers
```

Verify:

```powershell
nvidia-smi
```

### CUDA Toolkit 13.3

```powershell
winget install --id Nvidia.CUDA --exact --version 13.3
```

Approve the administrator prompt and open a new terminal.

Verify:

```powershell
nvcc --version
Test-Path "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3\bin\x64\cudart64_13.dll"
```

### cuDNN 9.23.0.39 for CUDA 13

Download and verify NVIDIA's official archive:

```powershell
$url = "https://developer.download.nvidia.com/compute/cudnn/redist/cudnn/windows-x86_64/cudnn-windows-x86_64-9.23.0.39_cuda13-archive.zip"
$zip = "$env:TEMP\cudnn-windows-x86_64-9.23.0.39_cuda13-archive.zip"

curl.exe -L --fail --output $zip $url

$expected = "34b10a27a2949f1c36766f045375b6dae44a478f47696a3d6acbf5b9b03077a0"
$actual = (Get-FileHash -Algorithm SHA256 $zip).Hash.ToLowerInvariant()
if ($actual -ne $expected) {
    throw "cuDNN archive hash mismatch"
}

Expand-Archive -LiteralPath $zip -DestinationPath "$env:TEMP\cudnn-9.23.0.39"
```

Open an administrator PowerShell window:

```powershell
$src = "$env:TEMP\cudnn-9.23.0.39\cudnn-windows-x86_64-9.23.0.39_cuda13-archive"
$dst = "C:\Program Files\NVIDIA\CUDNN\v9.23"

New-Item -ItemType Directory -Force `
    "$dst\bin\13.3\x64", `
    "$dst\include\13.3", `
    "$dst\lib\13.3" | Out-Null

Copy-Item "$src\bin\x64\*" "$dst\bin\13.3\x64" -Force
Copy-Item "$src\include\*" "$dst\include\13.3" -Force
Copy-Item "$src\lib\x64\*" "$dst\lib\13.3" -Force
Copy-Item "$src\LICENSE" "$dst\LICENSE" -Force
```

Verify:

```powershell
Test-Path "C:\Program Files\NVIDIA\CUDNN\v9.23\bin\13.3\x64\cudnn64_9.dll"
```

Continue with [`setup.md`](setup.md), create `.venv`, and install
`requirements-cuda.txt`.

## Configure CUDA OpenCV DLL paths

Run this section only after `requirements-cuda.txt` has been installed into
`.venv`.

Find the wheel loader:

```powershell
.\.venv\Scripts\python.exe -c "import site; print(site.getsitepackages()[0] + '\cv2\config.py')"
```

Edit `.venv\Lib\site-packages\cv2\config.py` so `BINARIES_PATHS` contains:

```python
import os

BINARIES_PATHS = [
    os.path.join(os.path.join(LOADER_DIR, "../../"), "x64/vc17/bin"),
    os.path.join(
        os.getenv(
            "CUDA_PATH",
            "C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.3",
        ),
        "bin/x64",
    ),
    "C:/Program Files/NVIDIA/CUDNN/v9.23/bin/13.3/x64",
] + BINARIES_PATHS
```

This generated `.venv` file must be updated again whenever `.venv` is
recreated.

## Verify GPU OpenCV

```powershell
.\.venv\Scripts\python.exe -c "import cv2; print(f'OpenCV {cv2.__version__}'); print(f'CUDA devices: {cv2.cuda.getCudaEnabledDeviceCount()}'); cv2.cuda.FarnebackOpticalFlow.create(); print('CUDA Farneback: available')"
```

Expected:

```text
OpenCV 4.13.0
CUDA devices: 1
CUDA Farneback: available
```

## Troubleshooting

| Problem | Resolution |
|---------|------------|
| `nvcc` is not found | Open a new terminal and confirm CUDA's `bin` directory is on the machine `PATH`. |
| OpenCV fails with a DLL error | Check the CUDA and cuDNN entries in `cv2/config.py`; both require their `x64` directories. |
| CUDA device count is `0` | Update the NVIDIA driver and verify the GPU is supported by the wheel. |
| CPU OpenCV was installed accidentally | Recreate `.venv` and install `requirements-cuda.txt`. |
| GPU mode is unavailable | Recreate `.venv`, install `requirements-cpu.txt`, and use Thea's CPU fallback. |
