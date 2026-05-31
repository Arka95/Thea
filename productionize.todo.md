# Productionize Thea — Todo & Guide

> **One-liner**: Turn Thea into a distributable offline Windows application (.exe + installer) that extracts stock-footage from videos using GPU acceleration (with CPU fallback), usable via CLI and a local UI.

---

## Phase 1: Code Architecture — GPU/CPU Fallback

These changes ensure the tool works on any Windows machine, GPU or not.

- [ ] **1.1 Create a device abstraction layer** — A module (`device.py`) that detects NVIDIA GPU availability at runtime and exposes a unified interface for optical flow regardless of backend.
- [ ] **1.2 Implement CUDA optical flow path** — Use `cv2.cuda.OpticalFlowDual_TVL1` or `cv2.cuda.FarnebackOpticalFlow` for GPU-accelerated processing.
- [ ] **1.3 Implement CPU optical flow fallback** — Use `cv2.calcOpticalFlowFarneback` as the automatic fallback when no GPU is detected.
- [ ] **1.4 Add runtime GPU detection** — `cv2.cuda.getCudaEnabledDeviceCount() > 0` check at startup, log which backend is active.
- [ ] **1.5 Test both paths** — Verify identical output (within tolerance) between GPU and CPU paths on the same input video.

---

## Phase 2: CLI Interface

Make the tool invokable from command line with clear arguments.

- [ ] **2.1 Add argparse CLI entry point** — `thea.py` or `__main__.py` with args: `--input`, `--output-dir`, `--min-duration`, `--gpu/--no-gpu`.
- [ ] **2.2 Add progress reporting** — Print progress percentage to stdout (useful for both CLI users and UI integration later).
- [ ] **2.3 Add exit codes** — 0=success, 1=input error, 2=processing error. Enables scripting.
- [ ] **2.4 Add `--version` and `--help`** — Standard CLI flags.
- [ ] **2.5 Validate inputs** — Check file exists, codec is supported, disk space available before processing.

---

## Phase 3: UI (Local Offline)

A simple local GUI for non-technical users. No server, no browser — runs natively.

- [ ] **3.1 Choose UI framework** — Recommended: `Dear PyGui` (fast, GPU-rendered, single file) or `tkinter` (zero deps, ships with Python). Alternative: `PyQt6` (heavier but more polished).
- [ ] **3.2 Design minimal UI** — File picker → settings (min duration, GPU toggle) → Start button → progress bar → output folder link.
- [ ] **3.3 Wire UI to processing engine** — Run video processing in a background thread, update progress bar via callback.
- [ ] **3.4 Add drag-and-drop support** — Allow dragging video files onto the window.
- [ ] **3.5 Add system tray / notification** — Notify when processing completes (useful for long videos).

---

## Phase 4: Packaging into .exe

Bundle everything into a standalone executable that runs without Python installed.

### 4.1 Dependency Audit & Trim

- [ ] **4.1.1 Remove unused OpenCV modules** — When building OpenCV, disable modules you don't use (e.g., `highgui`, `ml`, `photo`, `stitching`) to shrink binary size.
- [ ] **4.1.2 List bare-minimum dependencies** — Only these are needed at runtime:
  ```
  opencv (custom CUDA build — only core, imgproc, video, videoio, cudaoptflow, cudawarping)
  numpy
  scipy (only if used for stabilization math — otherwise remove)
  ffmpeg-python (or bundle ffmpeg.exe directly)
  ```
- [ ] **4.1.3 Bundle ffmpeg.exe** — Instead of `ffmpeg-python` calling system ffmpeg, ship a static ffmpeg build (~80MB, or trimmed build ~30MB) alongside the exe.

### 4.2 PyInstaller Packaging

- [ ] **4.2.1 Install PyInstaller** — `pip install pyinstaller`
- [ ] **4.2.2 Create .spec file** — Defines what to include/exclude:
  ```python
  # thea.spec
  a = Analysis(
      ['thea.py'],
      datas=[
          ('ffmpeg.exe', '.'),  # bundle ffmpeg
      ],
      binaries=[
          # CUDA runtime DLLs (only these are needed, NOT the full toolkit)
          ('C:/Projects/opencv_build/install/x64/vc17/bin/*.dll', '.'),
          ('C:/Program Files/NVIDIA/CUDNN/v9.23/bin/13.3/*.dll', '.'),
          # CUDA runtime (from toolkit install)
          ('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.2/bin/cudart64_*.dll', '.'),
          ('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.2/bin/cublas64_*.dll', '.'),
          ('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.2/bin/cufft64_*.dll', '.'),
          ('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.2/bin/nppial64_*.dll', '.'),
          ('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.2/bin/nppicc64_*.dll', '.'),
          ('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.2/bin/nppif64_*.dll', '.'),
      ],
      hiddenimports=['numpy', 'cv2'],
      excludes=['tkinter', 'matplotlib', 'pytest', 'PIL'],  # trim unused
  )
  exe = EXE(a, name='thea', console=True, icon='thea.ico')
  ```
- [ ] **4.2.3 Build the exe** — `pyinstaller thea.spec --noconfirm`
- [ ] **4.2.4 Test on a clean machine** — Copy `dist\thea\` folder to a machine without Python and verify it runs.

### 4.3 Alternative: Nuitka (Smaller/Faster Binary)

- [ ] **4.3.1 Install Nuitka** — `pip install nuitka`
- [ ] **4.3.2 Build** —
  ```
  nuitka --standalone --onefile --enable-plugin=numpy --include-data-files=ffmpeg.exe=ffmpeg.exe thea.py
  ```
- [ ] **4.3.3 Compare size/performance** — Nuitka compiles Python to C, often producing smaller and faster executables than PyInstaller.

---

## Phase 5: Installer Creation

Wrap the exe + DLLs into a proper Windows installer.

### Option A: Inno Setup (Recommended — free, lightweight, widely used)

- [ ] **5.1 Install Inno Setup** — Download from https://jrsoftware.org/isinfo.php
- [ ] **5.2 Create .iss script** —
  ```iss
  [Setup]
  AppName=Thea Video Extractor
  AppVersion=1.0.0
  DefaultDirName={autopf}\Thea
  DefaultGroupName=Thea
  OutputBaseFilename=thea-setup-1.0.0
  Compression=lzma2/ultra64
  SetupIconFile=thea.ico

  [Files]
  Source: "dist\thea\*"; DestDir: "{app}"; Flags: recursesubdirs

  [Icons]
  Name: "{group}\Thea"; Filename: "{app}\thea.exe"
  Name: "{commondesktop}\Thea"; Filename: "{app}\thea.exe"

  [Registry]
  ; Add to PATH so CLI works from any terminal
  Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; \
    ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; \
    Check: NeedsAddPath('{app}')
  ```
- [ ] **5.3 Build installer** — Compile `.iss` → produces `thea-setup-1.0.0.exe` (~150-300MB depending on CUDA DLLs).
- [ ] **5.4 Test install/uninstall cycle** — Verify clean install, PATH registration, desktop shortcut, and clean uninstall.

### Option B: MSIX (Windows Store style, sandboxed)

- [ ] **5.5 Create MSIX package** — If you want Microsoft Store distribution later. More restrictive but auto-updates.

---

## Phase 6: Distribution & Updates

- [ ] **6.1 Code-sign the exe and installer** — Prevents "Windows protected your PC" SmartScreen warnings. Get a code signing certificate (DigiCert, Sectigo, or free via SignPath for open source).
- [ ] **6.2 Add auto-update mechanism** — Embed a version check that pings a URL for new releases (can be a GitHub Releases JSON endpoint).
- [ ] **6.3 Create GitHub Releases workflow** — CI builds the exe + installer on tag push, uploads as release assets.
- [ ] **6.4 Write user-facing README** — Install instructions, system requirements (Windows 10+, NVIDIA GPU optional), usage examples.

---

## Minimum System Requirements (End User)

| Component | Required | Notes |
|-----------|----------|-------|
| OS | Windows 10 64-bit+ | |
| RAM | 8GB+ | For 4K video processing |
| GPU | Optional (NVIDIA recommended) | Falls back to CPU if absent |
| NVIDIA Driver | 525+ (if GPU present) | Standard Game Ready driver |
| Disk | 500MB for install + working space | |
| CUDA Toolkit | ❌ NOT required | Runtime DLLs bundled |
| Python | ❌ NOT required | Bundled in exe |

---

## CUDA DLLs to Ship (Bare Minimum)

These are the only CUDA files needed at runtime (NOT the full 4GB toolkit):

```
cudart64_130.dll          (~1MB)   — CUDA runtime
cublas64_13.dll           (~100MB) — Matrix math (used by optical flow)
cublasLt64_13.dll         (~150MB) — cuBLAS helper
cufft64_11.dll            (~50MB)  — FFT operations
nppial64_13.dll           (~5MB)   — NPP image arithmetic
nppicc64_13.dll           (~3MB)   — NPP color conversion
nppif64_13.dll            (~5MB)   — NPP image filtering
cudnn64_9.dll             (~300MB) — cuDNN (only if using DNN module)
```

> **Total CUDA overhead**: ~200-600MB depending on which modules are used. If you skip DNN (not needed for optical flow), you can drop cuDNN entirely and save ~300MB.

---

## CLI Usage (End User)

After installation:

```powershell
# Basic usage
thea --input "C:\Videos\vacation.mp4"

# Custom output directory and minimum clip duration
thea --input "video.mp4" --output-dir "C:\Clips" --min-duration 8

# Force CPU mode (skip GPU even if available)
thea --input "video.mp4" --no-gpu

# Batch process a folder
thea --input "C:\Videos\*.mp4" --output-dir "C:\AllClips"
```

---

## UI Usage (End User)

After installation, launch from Start Menu or desktop shortcut:

1. **Open** → Click "Select Video" or drag-and-drop a file
2. **Configure** → Adjust minimum clip duration (default: 5s), toggle GPU
3. **Process** → Click "Extract Clips" → progress bar shows status
4. **Output** → Click "Open Output Folder" when done

---

## File Size Estimates (Final Package)

| Component | Size |
|-----------|------|
| Python runtime (bundled) | ~30MB |
| OpenCV CUDA build (trimmed) | ~80MB |
| CUDA runtime DLLs | ~200MB (without cuDNN) |
| ffmpeg.exe (static) | ~80MB |
| numpy + scipy | ~30MB |
| App code | <1MB |
| **Total (uncompressed)** | **~420MB** |
| **Installer (LZMA compressed)** | **~150-200MB** |

---

## Quick Reference: Build vs Runtime

```
┌─────────────────────────────────────────────────────────┐
│                  YOUR BUILD MACHINE                       │
│                                                          │
│  CUDA Toolkit 13.2 (full) ─── needed to compile OpenCV  │
│  cuDNN 9.23 (dev) ─────────── needed to compile OpenCV  │
│  Visual Studio 2022 ───────── C++ compiler               │
│  CMake ────────────────────── build system               │
│  Python 3.12 ──────────────── builds python bindings     │
│                                                          │
│  Output: thea.exe + DLLs (ships to users)               │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  END USER MACHINE                         │
│                                                          │
│  thea-setup-1.0.0.exe (installer)                       │
│    └── thea.exe                                          │
│    └── opencv_world4130.dll (CUDA-enabled)              │
│    └── cudart64_130.dll (runtime only)                  │
│    └── cublas64_13.dll                                  │
│    └── ffmpeg.exe                                        │
│    └── ... other runtime DLLs                           │
│                                                          │
│  NO Python, NO CUDA Toolkit, NO Visual Studio needed    │
│  Just needs: Windows 10+ and NVIDIA driver (for GPU)    │
└─────────────────────────────────────────────────────────┘
```
