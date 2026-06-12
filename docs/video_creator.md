# Video Creator Setup — LTX-Video 2 + ComfyUI (Local, Free, GPU-Accelerated)

> Generate 10-20 second AI videos locally on RTX 4070 SUPER (12 GB VRAM) using LTX-Video 2 with reference clip input.

> **🤖 LLM Auto-Setup Note:** All paths, commands, and model links are absolute and copy-pasteable for automated setup.

---

## Table of Contents

1. [Hardware Constraints](#hardware-constraints)
2. [Model Choice Rationale](#model-choice-rationale)
3. [🔧 Step 1: Install ComfyUI](#-step-1-install-comfyui)
4. [🔧 Step 2: Install LTX-Video Node](#-step-2-install-ltx-video-node)
5. [🔧 Step 3: Download Models](#-step-3-download-models)
6. [🔧 Step 4: First Run](#-step-4-first-run)
7. [Optimal Parameters for 720p](#optimal-parameters-for-720p)
8. [Performance Benchmarks](#performance-benchmarks)
9. [Workflow: Reference Clip → New Video](#workflow-reference-clip--new-video)
10. [Constraints & Limitations](#constraints--limitations)
11. [Troubleshooting](#troubleshooting)

---

## Hardware Constraints

| Component | Spec | Impact |
|-----------|------|--------|
| **GPU** | RTX 4070 SUPER | Ada Lovelace, NVFP4 capable |
| **VRAM** | 12 GB | Limits resolution & frame count |
| **Max safe resolution** | 1280×720 (720p) | Beyond this risks OOM |
| **Max frames per gen** | ~180 (7.5s @24fps) or ~128 (5.3s) | Longer clips = split into segments |
| **Precision** | FP8 or NVFP4 | NVFP4 is ~25-30% faster on Ada |
| **CUDA** | 13.3 (already installed) | Compatible with PyTorch 2.3+ |

### VRAM Budget (720p generation):
```
Model (Q6 GGUF):     ~5-6 GB
VAE decode:          ~2-3 GB
Text encoder:        ~2-3 GB
Working memory:      ~1-2 GB
─────────────────────────────
Total:               ~10-12 GB ← fits your 12 GB
```

---

## Model Choice Rationale

| Model | VRAM fit | Quality | Speed | Verdict |
|-------|----------|---------|-------|---------|
| **LTX-Video 2.3 (Q6)** | ✅ Comfortable | Good | ⚡ Fast | **← CHOSEN** |
| LTX-Video 2.3 (Q8) | ⚠️ Tight | Better | Fast | Alternative if Q6 looks soft |
| Wan 2.2 (Q4) | ⚠️ Very tight | Best | 🐢 3x slower | Only for final renders |
| HunyuanVideo | ❌ 14GB+ | Excellent | Slow | Won't fit |

**LTX-Video 2.3 (Q6 GGUF)** is the optimal choice:
- Designed for consumer GPUs
- Fastest generation of all open models
- Native image-to-video (reference clip support)
- Active ComfyUI plugin with low-VRAM modes
- Fully open source, no API keys

---

## 🔧 Step 1: Install ComfyUI

```powershell
# Clone ComfyUI
cd C:\Projects
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install PyTorch with CUDA 12.x support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install ComfyUI dependencies
pip install -r requirements.txt

# Install xFormers for memory optimization
pip install xformers
```

### Verify CUDA works:
```powershell
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0)}')"
# Expected: CUDA: True, Device: NVIDIA GeForce RTX 4070 SUPER
```

---

## 🔧 Step 2: Install LTX-Video Node

```powershell
cd C:\Projects\ComfyUI\custom_nodes
git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git
cd ComfyUI-LTXVideo
pip install -r requirements.txt
```

Also install GGUF support node:
```powershell
cd C:\Projects\ComfyUI\custom_nodes
git clone https://github.com/city96/ComfyUI-GGUF.git
```

---

## 🔧 Step 3: Download Models

### Required files:

| File | Size | Location | Download from |
|------|------|----------|---------------|
| LTX-2.3 GGUF (Q6) | ~12 GB | `models/checkpoints/` | [HuggingFace](https://huggingface.co/Lightricks/LTX-2.3/tree/main) |
| VAE (video) | ~300 MB | `models/vae/` | [HuggingFace](https://huggingface.co/Lightricks/LTX-2.3/tree/main) |
| Text encoder | ~5 GB | `models/text_encoders/` | [HuggingFace](https://huggingface.co/google/gemma-3b-it) |

### Download commands:
```powershell
# Install huggingface CLI if needed
pip install huggingface-hub

# Download quantized model (Q6 — best quality/VRAM balance for 12GB)
huggingface-cli download Lightricks/LTX-2.3 --include "*.gguf" --local-dir C:\Projects\ComfyUI\models\checkpoints\LTX-Video

# Download VAE
huggingface-cli download Lightricks/LTX-2.3 --include "*vae*" --local-dir C:\Projects\ComfyUI\models\vae

# Download text encoder (Gemma 3B — fits VRAM)
huggingface-cli download google/gemma-3b-it --local-dir C:\Projects\ComfyUI\models\text_encoders\gemma-3b
```

### File placement:
```
C:\Projects\ComfyUI\
├── models\
│   ├── checkpoints\LTX-Video\       ← GGUF model files
│   ├── vae\                          ← VAE safetensors
│   ├── text_encoders\gemma-3b\       ← Text encoder
│   └── loras\                        ← Optional LoRAs
└── custom_nodes\
    ├── ComfyUI-LTXVideo\             ← LTX node
    └── ComfyUI-GGUF\                 ← GGUF loader
```

---

## 🔧 Step 4: First Run

```powershell
cd C:\Projects\ComfyUI

# Set VRAM optimization
$env:PYTORCH_CUDA_ALLOC_CONF = "max_split_size_mb:128"

# Launch with low-VRAM mode
python main.py --lowvram --preview-method auto
```

Open browser at: **http://127.0.0.1:8188**

### Quick test:
1. Right-click canvas → Add Node → search "LTXVideo"
2. If nodes appear, installation is successful
3. Load a sample workflow from ComfyUI-LTXVideo repo's `examples/` folder

---

## Optimal Parameters for 720p

### Recommended settings (RTX 4070 SUPER, 12 GB, 720p target):

| Parameter | Fast | Balanced | Quality |
|-----------|------|----------|---------|
| **Resolution** | 768×448 | 1280×720 | 1280×720 |
| **FPS** | 24 | 24 | 24 |
| **Frames** | 120 (5s) | 120 (5s) | 180 (7.5s) |
| **Steps** | 14-16 | 20-24 | 30-36 |
| **CFG (guidance)** | 3.5 | 4.0-4.5 | 4.2 |
| **Sampler** | UniPC | DPM++ 2M Karras | DPM++ 2M Karras |
| **Scheduler** | Normal | Karras | Karras |
| **Denoise** | 0.65 | 0.60 | 0.55 |
| **Motion scale** | 0.5 | 0.55 | 0.45 |
| **Precision** | FP8 | FP8 | FP8 |
| **Gen time (est.)** | ~1.5 min/5s | ~2.5 min/5s | ~4 min/7.5s |

### For 10-20 second videos:
Since max safe frames at 720p is ~180 (7.5s), generate in segments:
- **10s video** = 2 segments of 5s (overlap last 1s for smooth transitions)
- **20s video** = 4 segments of 5s (overlap each)

### Key parameter explanations:

| Parameter | What it does | Too low | Too high |
|-----------|-------------|---------|----------|
| **Steps** | Denoising iterations | Blurry, artifacts | Diminishing returns, slow |
| **CFG** | Prompt adherence strength | Ignores prompt | Oversaturated, artifacts |
| **Denoise** | How much to change from reference | Barely changes input | Ignores reference entirely |
| **Motion scale** | Amount of movement | Static/frozen | Jittery, unrealistic |
| **Frames** | Total frames generated | Short clip | OOM risk |

---

## Performance Benchmarks

### Expected generation times (RTX 4070 SUPER, LTX-2.3 Q6, 720p):

| Clip length | Frames | Fast (16 steps) | Balanced (24 steps) |
|-------------|--------|-----------------|---------------------|
| 5 seconds | 120 | ~1.5 min | ~2.5 min |
| 7.5 seconds | 180 | ~2.5 min | ~4 min |
| 10 seconds | 240 (2 segments) | ~3.5 min | ~5.5 min |
| 20 seconds | 480 (4 segments) | ~7 min | ~11 min |

### With reference clip input (image-to-video):
- Reference encoding: +30-45 seconds
- Total for 10s with reference: **~4-6 min**
- Total for 20s with reference: **~8-12 min**

### GPU monitoring during generation:
```powershell
# Run in separate terminal while generating
nvidia-smi -l 2
# Expected: ~10-11.5 GB VRAM used, ~95-100% GPU utilization
```

---

## Workflow: Reference Clip → New Video

### Image-to-Video (single reference frame):
1. Extract a key frame from your 10s reference clip
2. Use it as the starting image in LTXVideo I2V node
3. Provide text prompt describing desired motion/scene
4. Generate 5-7.5s segments and stitch

### Video-to-Video (style transfer from reference):
1. Load reference clip into LTXVideo V2V node
2. Set denoise to 0.55-0.65 (lower = more faithful to reference)
3. Add text prompt for desired modifications
4. Output matches reference motion with new style/content

### ComfyUI workflow pattern:
```
[Load Reference Image/Video]
        ↓
[LTXVideo Encode (VAE)]
        ↓
[Text Prompt → Gemma Encoder]
        ↓
[LTXVideo Sampler]  ← steps, CFG, denoise, frames
        ↓
[LTXVideo Decode (VAE)]
        ↓
[Save Video (MP4)]
```

### Stitching multiple segments:
```powershell
# Use FFmpeg to concatenate segments with crossfade
ffmpeg -i segment1.mp4 -i segment2.mp4 -filter_complex "[0:v][1:v]xfade=transition=fade:duration=1:offset=4" -c:v libx264 output.mp4
```

---

## Constraints & Limitations

### Hard limits (12 GB VRAM):
| Constraint | Limit | Workaround |
|------------|-------|------------|
| Max resolution | 1280×720 | Upscale after generation |
| Max frames/generation | ~180 @ 720p | Segment and stitch |
| Max video length (single pass) | ~7.5s @ 24fps | Multi-segment workflow |
| 4K generation | ❌ Not possible | Generate 720p, upscale with Real-ESRGAN |
| Concurrent generations | 1 at a time | Queue in ComfyUI |

### Quality constraints:
| Issue | Cause | Mitigation |
|-------|-------|------------|
| Flickering | Low steps or high CFG | Use 20+ steps, CFG 3.5-4.5 |
| Blurry output | Too few steps or Q4 model | Use Q6 model, 24+ steps |
| Motion artifacts | High motion scale | Keep motion_scale 0.4-0.6 |
| Segment seams | No overlap between clips | Overlap last 24 frames (1s) |
| Text doesn't appear | Model limitation | LTX-2 can't reliably render text |
| Hands/fingers | Common AI limitation | Shorter clips, careful prompting |

### What this setup CAN do well:
- ✅ Cinematic camera movements (pan, zoom, dolly)
- ✅ Nature scenes, landscapes, abstract motion
- ✅ Product shots with slow rotation
- ✅ Style transfer from reference clips
- ✅ B-roll generation for stock footage
- ✅ Consistent style across segments (with reference)

### What it struggles with:
- ⚠️ Realistic human faces (especially close-up)
- ⚠️ Text/logos in video
- ⚠️ Complex multi-character interactions
- ⚠️ Very long continuous motion (>8s single pass)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CUDA out of memory | Lower resolution to 768×448, reduce frames to 120, use `--lowvram` |
| Model not loading | Check file paths match exactly, verify GGUF node installed |
| Black/corrupted output | Update PyTorch, check VAE is loaded correctly |
| Very slow generation | Ensure GPU is being used (`nvidia-smi`), not CPU fallback |
| ComfyUI won't start | Check Python version (3.10-3.11), reinstall torch with CUDA |
| Nodes missing | Restart ComfyUI after installing custom nodes |
| Segmentation/stitching artifacts | Increase overlap frames, use consistent seed across segments |

### Reset environment:
```powershell
cd C:\Projects\ComfyUI
.\venv\Scripts\Activate.ps1
pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install --upgrade xformers
python main.py --lowvram
```

---

## Quick Reference Card

```powershell
# Start ComfyUI (every time)
cd C:\Projects\ComfyUI
.\venv\Scripts\Activate.ps1
$env:PYTORCH_CUDA_ALLOC_CONF = "max_split_size_mb:128"
python main.py --lowvram --preview-method auto

# Open in browser
# http://127.0.0.1:8188

# Monitor GPU
nvidia-smi -l 2

# Stitch segments (FFmpeg)
ffmpeg -i seg1.mp4 -i seg2.mp4 -filter_complex "[0:v][1:v]xfade=transition=fade:duration=1:offset=4" out.mp4
```

---

## Links

| Resource | URL |
|----------|-----|
| ComfyUI | https://github.com/comfyanonymous/ComfyUI |
| LTX-Video node | https://github.com/Lightricks/ComfyUI-LTXVideo |
| LTX-2.3 models | https://huggingface.co/Lightricks/LTX-2.3 |
| GGUF node | https://github.com/city96/ComfyUI-GGUF |
| LTX docs | https://docs.ltx.video/ |
| ComfyUI GGUF guide | https://dev.to/gary_yan_86eb77d35e0070f5/how-to-install-and-configure-ltx-2-gguf-models-in-comfyui-complete-2026-guide-1d3m |
