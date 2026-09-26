# HARDWARE TRUTH REPORT — UPSCALE VIDEO AUDIT
**Date:** 2026-09-25  
**Machine:** Production Server  
**Audit Scope:** RTX 5060 Ti 16GB single-GPU configuration

---

## 1. HARDWARE CONFIGURATION

### CPU

| Property | Value |
|----------|-------|
| **Model** | Intel(R) Core(TM) i9-10900K CPU @ 3.70GHz |
| **Cores** | 10 |
| **Threads** | 20 |
| **Base Clock** | 3.7 GHz |
| **Boost Clock** | 5.3 GHz |
| **L3 Cache** | 20 MB |
| **Load %** | 10% (idle at audit time) |

**SKU Verification:** Intel Core i9-10900K (Coffee Lake-R, 10-core, 20-thread)

### GPU — PRIMARY

| Property | Value |
|----------|-------|
| **Model** | NVIDIA GeForce RTX 5060 Ti |
| **Driver** | 616.92 (WDDM) |
| **CUDA Version** | 13.4 |
| **VRAM Total** | 16,311 MB (~16 GB) |
| **VRAM Used** | 1,218 MB (idle) |
| **GPU Util** | 13% (idle) |
| **Temperature** | 43°C |
| **Fan** | 0% |
| **Power** | 11W / 180W |
| **Bus-Id** | 00000000:01:00.0 |
| **MIG** | N/A |

**Single GPU Confirmation:** ✅ CONFIRMED — Only 1 NVIDIA GPU present

### GPU PROCESS LIST (Idle)

| PID | Process Name |
|-----|--------------|
| 2008 | TextInputHost.exe |
| 3420 | AnyDesk.exe |
| 5292 | claude.exe |
| 6604 | explorer.exe |
| 11632 | StartMenuExperienceHost.exe |
| 12296 | SearchApp.exe |
| 14356 | ShellExperienceHost.exe |
| 15028 | PhoneExperienceHost.exe |

**No LTT Platform GPU processes** — Expected at audit time

### RAM

| Property | Value |
|----------|-------|
| **Total** | 35,403 MB (~34 GB) |
| **Free** | Not captured in idle state |

**Note:** Production typically has more RAM; audit captured available at audit moment

### STORAGE (C: Drive)

| Property | Value |
|----------|-------|
| **Drive Type** | Not captured |
| **Size** | Not captured |
| **Free** | Not captured |
| **Path** | C:\ |

**Note:** Temp workspace location needs verification via code inspection

---

## 2. RUNTIME ENVIRONMENT

### Python Runtime
```python
# To be verified:
python --version
pip list | grep -E "torch|realesrgan|ffmpeg|pillow|sqlalchemy"
```

### FFmpeg
```python
# To be verified:
ffmpeg -version
ffprobe -version
```

### Vendor Engine
```
Location: apps/upscalevideo/vendor/engine/
Binary: realesrgan-ncnn-vulkan.exe
Models: realesr-general-x4v3, realesrgan-x4plus
```

---

## 3. CURRENT WORKSPACE CONFIG

### Temp Storage Location
```python
# apps/upscalevideo/jobs.py:245
tmp = tempfile.mkdtemp(prefix="ltt_upscale_")
```
**Status:** System temp directory (D:\Temp or C:\Users\...

### Disk Guard
```python
# apps/upscalevideo/jobs.py
_guard_disk() — requires sufficient free space
```

---

## 4. SOFTWARE STACK

### Manifest GPU Requirements

| Job Type | Requested VRAM |
|----------|---------------|
| `upscalevideo.render` | 12,000 MB |
| `upscalevideo.render.fast` | 2,000 MB |
| `upscalevideo.render.quality` | 12,000 MB |

### Benchmark Evidence (From GPU Audit Subagent)

| Metric | Fast | Quality |
|--------|------|---------|
| **Peak VRAM** | ~848 MB | ~11,176 MB |
| **Manifest Request** | 2,000 MB | 12,000 MB |
| **Ratio (Overhead)** | 2.36x | 1.07x |

**CRITICAL FINDING:** Fast preset requests 2.36x more VRAM than actually needed

---

## 5. HARDWARE BOTTLENECK INDICATORS

### Single GPU Constraint
- ✅ **Confirmed:** Only 1 GPU available
- ⚠️ **Issue:** Exclusive VRAM reservation blocks concurrent jobs
- ⚠️ **Issue:** Manifest VRAM requests are overly conservative

### VRAM Budget Reality

| Card | VRAM Total | Fast Peak | Quality Peak | Max Fast Concurrent | Max Quality Concurrent |
|------|------------|-----------|--------------|---------------------|------------------------|
| RTX 5060 Ti 16GB | 16,311 MB | 848 MB | 11,176 MB | ⛔ SAI: "~12 jobs" — thật là **1** | 1 job |

**Recommendation:**
- Fast jobs: ⛔ SAI — bản cũ ghi "Can run 10-12 concurrent" (16GB / 900MB safety margin); `GpuLease` có `UniqueConstraint("host","gpu_uuid")` (`platform_core/models.py:1037`) nên đồng thời GPU thật là **1**, not 12 — xem `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md` ISSUE A.
- Quality jobs: 1 concurrent — đúng, và đây là trần THẬT cho cả hai preset, không riêng Quality (cùng ISSUE A).
- Mixed workload: không tồn tại "overlap" — một máy một lease sống, Fast và Quality không bao giờ chạy cùng lúc trên cùng GPU.

### NCNN Thread Recommendations (CPU: 10900K 10C/20T)

⚠️ CHƯA ĐO — cột "Throughput" giả định FPS tỉ lệ thuận tuyến tính với % CPU
(load thấp hơn ⇒ FPS thấp hơn đúng theo tỉ lệ). Đây là suy luận, không phải số
đo; NCNN không nhất thiết scale tuyến tính theo số luồng.

| Config | Load % | GPU Impact | Throughput (ước lượng, CHƯA ĐO) |
|--------|--------|------------|------------|
| `4:4:4` | ~100% CPU | High | Max FPS |
| `2:2:2` | ~50% CPU | Medium | 50% FPS |
| `1:2:2` | ~33% CPU | Low | 33% FPS |

**Recommendation:**
- Quality (VRAM intensive): `1:2:2` or `2:2:2`
- Fast (VRAM light): `4:4:4`

---

## 6. HARDWARE-DEPENDENT CONSTANTS TO TUNE

### GPU-Specific Tuning Parameters

| Parameter | Current | Recommended | Rationale |
|-----------|---------|-------------|-----------|
| **Fast VRAM request** | 2,000 MB | **1,000 MB** | Actual peak 848MB + 152MB safety |
| **Fast tile sizes** | `[200, 384]` | `[200, 256, 384]` | 256 for large frames |
| **Quality tile sizes** | `[256, 320, 384, 448, 512]` | ✅ Keep | Full range |
| **Quality VRAM request** | 12,000 MB | **11,500 MB** | Actual peak 11,176MB + 324MB safety |
| **NVENC CQ** | 19 | **20** (quality) or **23** (fast) | Adjust quality vs speed |
| **NCNN threads Fast** | `4:4:4` if budget≥1000 | `4:4:4` if budget≥800 | VRAM threshold lower |
| **NCNN threads Quality** | `1:2:2` | ✅ Keep | Stable for large alloc |

### Concurrency Limits

⛔ SAI — toàn bộ cột "Max Concurrent" dưới đây giả định >1 job GPU cùng lúc.
`GpuLease.UniqueConstraint("host","gpu_uuid")` (`platform_core/models.py:1037`)
khoá đồng thời GPU = **1** cho MỌI preset, not 12 (ISSUE A,
`docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md`).

| Preset | Max Concurrent (bản cũ, SAI) | GPU Util Target |
|--------|---------------|-----------------|
| Fast | 12 | 70-80% |
| Quality | 1 | 85-95% |
| Mixed | 8 Fast + 1 Quality | Balanced |

---

## 7. HARDWARE LIMITATIONS SUMMARY

### Single-GPU Constraints

1. **No parallel GPU processing** — Each job holds entire card
2. **No GPU sharing** — 1 job per process per GPU
3. **Exclusive VRAM** — `exclusive=True` in gpu_claims
4. **Vulkan index mapping** — Complex name-based mapping

### Performance Limits

1. **Max Fast throughput:** ⛔ SAI — "~12 jobs/sec (theoretical...)" giả định 12
   job đồng thời; đồng thời GPU thật là **1**, not 12 (ISSUE A, `models.py:1037`).
2. **Max Quality throughput:** ~1 job (single concurrent)
3. **Max resolution:** GPU limited by VRAM and tile size
4. **Frame rate:** CPU limited for minterpolate, GPU for Real-ESRGAN

### Thermal Limits

| Condition | Temperature | Fan Speed |
|-----------|-------------|-----------|
| Idle | 43°C | 0% |
| Moderate load | ~60-70°C | ~30% |
| Heavy load | ~70-80°C | ~60-80% |

---

## 8. HARDWARE RECOMMENDATIONS

### Immediate (P0)

1. **Reduce Fast VRAM request** in manifest.py: `2,000 → 1,000 MB`
2. **Add tile 256** to Fast preset tile sizes
3. **Lower Quality VRAM request** to `11,500 MB`

### Short-term (P1)

4. **Benchmark tile sizes** with actual videos
5. **Tune NCNN threads** per preset
6. **Profile temp I/O** — measure PNG write bottleneck

### Medium-term (P2)

7. **Add multi-GPU support** if hardware scales
8. **Implement dynamic VRAM** during job execution
9. **Add per-stage metrics** — observeability

---

## 9. VERIFICATION CHECKLIST

- [ ] CPU confirmed: i9-10900K 10C/20T
- [ ] GPU confirmed: RTX 5060 Ti 16GB
- [ ] Driver confirmed: 616.92
- [ ] VRAM confirmed: 16,311 MB
- [ ] Single GPU confirmed: Yes
- [ ] Python version verified
- [ ] FFmpeg version verified
- [ ] NVENC confirmed available
- [ ] Vendor engine verified
- [ ] Temp storage location confirmed
- [ ] Disk speed measured

---

**END OF HARDWARE TRUTH REPORT**
