# UPCSACLE V2 — RIFE INTEGRATION GUIDE

## OVERVIEW

RIFE-NCNN-Vulkan sẽ thay thế minterpolate để:
1. GPU offload (RTX 5060 Ti) — **5-10x faster**
2. Better temporal quality
3. Lower CPU utilization (<30%)

## PHASE 2.1.1: VENDOR RIFE

### Files to Download

**1. rife-ncnn-vulkan.exe** (Windows)
- Source: https://github.com/nihui/rife-ncnn-vulkan/releases
- Binary includes: rife-ncnn-vulkan.exe + vcomp140.dll
- Size: ~2 MB
- License: Check GitHub repo (Apache-2.0?)

**2. Model files** (bundled with binary, verify)
- RIFE model already included in executable

### Installation Steps

```bash
# 1. Download
curl -L https://github.com/nihui/rife-ncnn-vulkan/releases/download/v3.2.1/rife-ncnn-vulkan-3.2.1-windows.zip \
    -o apps\upscalevideo\vendor\engine\rife.zip

# 2. Extract
Expand-Archive apps\upscalevideo\vendor\engine\rife.zip \
    apps\upscalevideo\vendor\engine\ -Force

# 3. Verify
ls apps\upscalevideo\vendor\engine\rife*.exe apps\upscalevideo\vendor\engine\vcomp*.dll
```

### Test Command

```bash
# Extract frames
ffmpeg -i input.mp4 -vf "fps=30" frames/f%05d.png

# Interpolate with RIFE (2x FPS)
rife-ncnn-vulkan.exe -i frames/ -o frames_interp/

# Rebuild video
ffmpeg -framerate 60 -i frames_interp/f%05d.png -i audio.mp3 \
    -c:a copy -c:v libx264 -crf 20 -pix_fmt yuv420p output.mp4
```

### FFmpeg Filter Integration

When binary is available, update `apps/upscalevideo/ff.py`:

```python
# Use RIFE filter if binary exists
rife_exe = Path("apps/upscalevideo/vendor/engine/rife-ncnn-vulkan.exe")
if rife_exe.exists():
    filters.append("rife=0")  # Requires rife-ncnn-vulkan build
else:
    filters.append("minterpolate=fps=60:...")  # Fallback
```

---

## CURRENT STATUS

**Phase 2.1.1: SKIPPED**

Reason: RIFE binary not available for download in this session.

Alternative: Proceed with Phase 2.2 (PNG I/O optimization) — lower effort, immediate impact.

---

## NEXT: PHASE 2.2 — PNG I/O OPTIMIZATION

See: `docs/UPSCALE_V2/04_BOTTLENECKS.md`

Key improvement: Batch PNG writes to reduce disk I/O overhead.
