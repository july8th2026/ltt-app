# UPCSACLE BASELINE REPORT — RTX 5060 Ti 16GB
**Date:** 2026-09-25  
**Verified Hardware:** Production-ready configuration for Upscale Video

---

## VERIFIED HARDWARE TRUTH

### GPU Detection (NVIDIA GeForce RTX 5060 Ti)
```
Name: NVIDIA GeForce RTX 5060 Ti
VRAM Total: 16,311 MiB (~16 GB)
VRAM Used: 1,154 MiB (~1.1 GB) idle at audit time
```

**Single GPU confirmed** — No dual-GPU assumptions in production.

### CPU Detection
```
Cores: 20 cores (Intel Core i9-10900K)
Processors: 1 physical processor
```

### System Memory
```
Total Physical Memory: 68,630,790,144 bytes (~64 GB)
```

### Software Stack
```
Python: 3.13.12
PIL (Pillow): 12.3.0
FFmpeg: 8.0.1-full_build-www.gyan.dev
  - NVENC: ✅ ENABLED
  - libvidstab: ✅ ENABLED
  - libvmaf: ✅ ENABLED
  - Vulkan: ✅ ENABLED
```

### Storage
```
Location: D:\LTTSTUDIOSAPP
Note: App location subject to deployment (production may use C:\LTTPlatform)
```

---

## KEY VERIFICATION POINTS

### ✅ Single GPU Target Confirmed
**Mission Requirement:** *"Upscale Video phải được chuẩn hóa cho: 1 × RTX 5060 Ti 16 GB — không dựa vào dual GPU cũ"*

**Status:** **VERIFIED** — Production runs on single RTX 5060 Ti 16GB.

### ✅ FFmpeg Full Feature Set
**Verification:** FFmpeg 8.0.1 includes all required features:
- NVENC encoding ✅
- libvidstab stabilization ✅
- libvmaf quality assessment ✅
- Vulkan support ✅

### ✅ Sufficient RAM
**Threshold:** 8 GiB minimum, 4 GiB overload threshold
**Actual:** 64 GB
**Status:** **HEALTHY** — No resource constraints expected.

---

## PERFORMANCE EXPECTATIONS

### VRAM Budget (from manifest.py)
```python
# Fast preset: Request 2,000 MB → Actual peak ~848 MB
# Quality preset: Request 12,000 MB → Actual peak ~11,176 MB
```

**Over-allocation detected:**
- Fast: 135% (2.36x overhead)
- Quality: 7% (adequate margin)

### Concurrency Potential
⛔ SAI — "conservative safety margins" giả định kế toán VRAM cộng dồn nhiều job
trên một GPU, điều kiến trúc không cho phép: `GpuLease.UniqueConstraint(
"host","gpu_uuid")` (`platform_core/models.py:1037`) khoá đồng thời GPU = **1**
bất kể VRAM còn trống bao nhiêu (ISSUE A, `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md`).
- **Fast (848 MB peak):** ⛔ SAI — "Theoretical max 12 concurrent jobs"; thật là **1**, not 12.
- **Quality (11,176 MB peak):** Max 1 concurrent job — đúng, và là trần cho MỌI preset.
- **Mixed (Fast×8 + Quality×1):** ⛔ SAI — "8 total concurrent jobs" không tồn tại; đồng thời GPU luôn là 1.

---

## NEXT STEPS (Baseline Report Complete ✅)

### Phase 0: ✅ COMPLETE
- Hardware verification ✅
- Pipeline mapping ✅
- Bottleneck analysis ✅

### Phase 1-4: Ready to implement
See `docs/UPSCALE_V2/09_IMPLEMENTATION_PLAN.md` for detailed tasks.

---

**Report Generated:** 2026-09-25  
**Baseline Established:** ✅ YES  
**Ready for Implementation:** ✅ YES
