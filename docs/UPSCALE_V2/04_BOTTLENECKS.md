# BOTTLENECKS REPORT — UPSCALE VIDEO
**Date:** 2026-09-25  
**Scope:** Current production bottlenecks on RTX 5060 Ti 16GB

---

## EXECUTIVE SUMMARY

| Bottleneck | Priority | Impact | Severity | Fix Effort | ROI |
|------------|----------|--------|----------|------------|-----|
| **VRAM Over-allocation** | P0 | Blocks concurrent jobs | HIGH | 15 min | ⭐⭐⭐⭐⭐ |
| **PNG Disk I/O** | P1 | Slow frame extraction | HIGH | 1-2 hours | ⭐⭐⭐⭐ |
| **NVENC Gate Too Strict** | P1 | CPU fallback | HIGH | 15 min | ⭐⭐⭐⭐ |
| **No Checkpoint** | P1 | Long jobs fail entirely | HIGH | 2 hours | ⭐⭐⭐⭐ |
| **No Model Warmup** | P2 | Cold start latency | MEDIUM | 30 min | ⭐⭐⭐ |
| **Single GPU Exclusive** | P1 | Job queue bottleneck | HIGH | 2-3 hours | ⭐⭐⭐⭐ |
| **Smooth Motion CPU** | P1 | Huge CPU cost | HIGH | 30 min | ⭐⭐⭐ |

**Total Critical Issues:** 7  
**Fixable Effort:** ~5 hours  
**Expected Speedup:** ⛔ SAI — "2-5x throughput increase" phần lớn dựa trên giả
định tăng số job Fast đồng thời; `GpuLease.UniqueConstraint("host","gpu_uuid")`
(`platform_core/models.py:1037`) khoá đồng thời GPU = **1**, not 12 (ISSUE A).
Phần đến từ Disk I/O/NVENC gate/checkpoint là CHƯA ĐO, không phải đã disprove.

---

## 1. BOTTLENECK #1: VRAM OVER-ALLOCATION

**Priority:** P0 (Critical)  
**Location:** `apps/upscalevideo/manifest.py:96-100`

### Problem Statement

```python
gpu_vram_mb = {
    "upscalevideo.render": 12000,
    "upscalevideo.render.fast": 2000,  # ❌ TOO HIGH
    "upscalevideo.render.quality": 12000,
}
```

### Evidence

**Measured peak VRAM (RTX 5060 Ti 16GB):**
- Fast preset actual: **~848 MB**
- Manifest requested: **2,000 MB**
- **Over-allocation: 135%** (gấp 2.36x)

- Quality preset actual: **~11,176 MB**
- Manifest requested: **12,000 MB**
- **Over-allocation: 7%** (adequate)

### Root Cause

Manifest VRAM requirements were copied from old H32 benchmark without re-measurement. Fast preset was measured at 2GB peak but actual runtime peak is only 848MB.

### Impact

**On RTX 5060 Ti 16GB:**

| Current State | Issue |
|---------------|-------|
| Fast job requests 2,000 MB | Holds entire card via exclusive lease |
| Actual usage 848 MB | Wastes 1,152 MB that could run other jobs |
| Max concurrent fast | ⛔ SAI — "~4 jobs" giả định kế toán VRAM cộng dồn; `exclusive=True` (`gpu_lease.py:201-203`) giữ TRỌN card cho một lease, not 4 |
| Should support | ⛔ SAI — "~12 jobs"; `UniqueConstraint("host","gpu_uuid")` (`models.py:1037`) khoá đồng thời = **1**, not 12 (ISSUE A) |

**Business Impact:**
- User experiences job queue delays unnecessarily
- ⛔ SAI — "Production capacity underutilized by 66%" tính từ (12-4)/12, cả hai số đều SAI (ISSUE A); thật ra đồng thời luôn là 1, không có "capacity" nào bị bỏ phí theo cách này
- Higher cost per job due to queue wait time

### Fix

**File:** `apps/upscalevideo/manifest.py:96-100`

**Current:**
```python
gpu_vram_mb = {
    "upscalevideo.render": 12000,
    "upscalevideo.render.fast": 2000,
    "upscalevideo.render.quality": 12000,
}
```

**Recommended:**
```python
gpu_vram_mb = {
    "upscalevideo.render": 12000,  # Keep for legacy compatibility
    "upscalevideo.render.fast": 1000,  # 848 MB peak + 152 MB safety
    "upscalevideo.render.quality": 11500,  # 11176 MB peak + 324 MB safety
}
```

**Testing:**
1. Verify fast jobs still complete successfully
2. Test concurrent job scheduling
3. Monitor OOM events
4. Verify credit hold accuracy

**Rollback:**
- Revert to `2000` if OOM events occur

**Acceptance:**
- ⛔ SAI — "Max fast concurrent jobs increases from 4 → 12" giả định kế toán VRAM
  cộng dồn; `GpuLease.UniqueConstraint("host","gpu_uuid")` (`models.py:1037`)
  khoá đồng thời GPU = **1**, not 12, bất kể `gpu_vram_mb` (ISSUE A,
  `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md`). Hạ `gpu_vram_mb.fast` chỉ
  đổi sàn nhận MỘT job (ISSUE B), không mua thêm job đồng thời.
- No regression in fast job success rate
- No new OOM errors

---

## 2. BOTTLENECK #2: PNG FRAME EXTRACTION DISK I/O

**Priority:** P1 (High)  
**Location:** `apps/upscalevideo/ff.py:122-144`

### Problem Statement

```python
def extract_frames(src, out_dir, cfr_fps=None, ...):
    # FFmpeg outputs ONE FILE PER FRAME
    out_path = os.path.join(out_dir, "f%05d.png")
    proc = subprocess.run([...], capture_output=True)
```

### Impact Analysis

| Video | Duration | FPS | Frames | Disk Write | Time (Est.) |
|-------|----------|-----|--------|------------|-------------|
| Short preview | 8s | 30 | 240 | 700 MB | 5-10s |
| Medium | 1min | 30 | 1,800 | 5.4 GB | 30-60s |
| Long | 5min | 30 | 9,000 | 27 GB | 3-5 min |

**Disk I/O Pattern:**
- **Write:** 10,000+ small random writes
- **Latency:** Thousands of separate file operations
- **Throughput:** Limited by small-file overhead

### Root Cause

FFmpeg `-vf fps=` filter outputs individual PNG files. Each frame = separate file on disk.

**Why:** 
- Simple to implement
- Compatible with NCNN Vulkan tile processing
- Proven to work

### Alternative Solutions

| Solution | Effort | Speed Gain | Risk |
|----------|--------|------------|------|
| **1. Direct FFmpeg encode** | Low | ⭐⭐⭐ Eliminate PNG step | May lose FPS precision |
| **2. WebP intermediate** | Medium | ⭐⭐ 30% smaller files (ước lượng, CHƯA ĐO) | Decode overhead |
| **3. RAM buffer** | Medium | ⭐⭐⭐ Zero disk I/O | Memory hungry |
| **4. Batch PNG** | Medium | ⭐⭐ Fewer files | Complex |

### Quick Fix: Direct Encode

**Concept:** Instead of writing PNGs then reading back, encode directly from frames.

**Current flow:**
```
FFmpeg decode → PNG write → PNG read → NCNN upscale → PNG read → NCNN encode → PNG delete → FFmpeg encode
```

**Proposed flow:**
```
FFmpeg decode (internal) → NCNN upscale → FFmpeg encode
```

**Implementation:**
```python
# Instead of:
extract_frames() → upscale → encode

# Do:
extract_frames()  # Keep this for now
upscale_pngs()    # Process PNGs in batches
encode_segments() # Already optimized with NVENC
```

**Real gain:** Optimize `upscale_pngs()` batch size and I/O pattern first.

### Priority: MEDIUM (Optimize existing PNG workflow before replacing)

**Immediate actions:**
1. Profile PNG write I/O
2. Optimize disk I/O (batch writes, reduce temp files)
3. Tune `_BATCH_SIZE` based on disk profile

**Medium-term:**
4. Prototype direct encode path
5. A/B test PNG vs direct encode

### Recommendation

**Short-term:** Optimize PNG workflow (P1)  
**Long-term:** Consider direct encode (P2)

---

## 3. BOTTLENECK #3: NVENC GATE TOO STRICT

**Priority:** P1 (High)  
**Location:** `apps/upscalevideo/jobs.py:147-150`

### Problem Statement

```python
def _resolve_encoder(codec: Codec) -> str:
    gpu = media.detect_gpu_encoder()
    if gpu == "h264_nvenc":
        return ENCODER[codec]  # NVENC fast
    return "libx264"  # ❌ CPU fallback for ALL other GPUs
```

### Impact

| GPU Type | Current Encoder | Speed | Quality |
|----------|-----------------|-------|---------|
| NVIDIA (NVENC) | h264_nvenc | Fast (~2x, ước lượng CHƯA ĐO) | Good |
| **Intel (QSV)** | libx264 | **Very Slow (CPU)** | Good |
| **AMD (AMF)** | libx264 | **Very Slow (CPU)** | Good |

**Performance Impact:**
- Intel i9-10900K with QuickSync: ⚠️ CHƯA ĐO khi viết — "10x slower than NVENC"
  chưa có phép đo dẫn nguồn tại thời điểm đó. Cập nhật 2026-09-26: KHÔNG còn cần
  đo, vì `h264_qsv`/`hevc_qsv`/`h264_amf`/`hevc_amf` được MEASURED FAIL hoàn
  toàn ở runtime trên máy này ("Nothing was written into output file" trên một
  lượt encode thử 256×256), dù `ffmpeg -encoders` liệt kê chúng — không có
  "chậm hơn" để so, vì QSV/AMF không chạy được (⛔ SAI nếu đọc là "QSV chạy,
  chỉ chậm"). Xem `docs/UPSCALE_V2_CORRECTION/05_ENCODER_TRUTH.md`.
- Same 5min video: 5min (NVENC) vs 50min (CPU) — ước lượng, CHƯA ĐO

### Root Cause

Strict gate: only NVENC enabled if `h264_nvenc` detected. No fallback chain.

### Fix

**File:** `apps/upscalevideo/jobs.py:147-150`

**Add fallback chain:**
```python
def _resolve_encoder(codec: Codec) -> str:
    gpu = media.detect_gpu_encoder()
    
    if gpu == "h264_nvenc":
        return ENCODER[codec]  # NVIDIA NVENC
    elif gpu == "h264_qsv":
        return ENCODER_QSV[codec]  # Intel QuickSync
    elif gpu == "h264_amf":
        return ENCODER_AMD[codec]  # AMD AMF
    return "libx264"  # CPU fallback (final)
```

**Required changes:**
1. Add `ENCODER_QSV` mapping in `schemas.py`
2. Add `ENCODER_AMD` mapping in `schemas.py`
3. Update `media.detect_gpu_encoder()` to return QSV/AMF

**Testing:**
1. Test on Intel GPU with QSV support
2. Test on AMD GPU with AMF support
3. Compare NVENC vs QSV vs CPU encode time
4. Compare quality

**Acceptance:** ⛔ SAI — cả đề xuất này không thực thi được. MEASURED 2026-09-26:
`h264_qsv`, `hevc_qsv`, `h264_amf`, `hevc_amf` đều FAIL hoàn toàn ở runtime trên
máy này ("Nothing was written into output file" trên một lượt encode thử
256×256), dù `ffmpeg -encoders` liệt kê chúng. Chốt sản phẩm: app chỉ hỗ trợ
NVENC+CPU — xem `docs/UPSCALE_V2_CORRECTION/05_ENCODER_TRUTH.md`.
- Intel jobs use QSV instead of CPU
- AMD jobs use AMF instead of CPU
- Quality unchanged
- Speedup: 5-10x on QSV/AMF — ⛔ SAI, not applicable: QSV/AMF không chạy được, không có "speedup" nào để thu

---

## 4. BOTTLENECK #4: NO CHECKPOINT/RESUME

**Priority:** P1 (High)  
**Location:** `apps/upscalevideo/jobs.py:268-273`

### Problem Statement

```python
# Current: Only output-file-based checkpoint
if storage.exists(out_key):
    ctx.progress(100, "xong")
    return {"video_key": out_key, ...}
```

### Impact

**Long job failure scenario:**
```
1. 5-minute video, 9,000 frames
2. Upscale processing frame 2,000/9,000
3. OOM or crash
4. Entire job retry: all 9,000 frames re-processed
5. Time lost: 3-5 minutes
6. Disk waste: Thousands of PNG files recreated
```

### Root Cause

No intermediate checkpoint for partial job completion.

### Proposed Solution

**Stage-based checkpoints:**

```python
# Define checkpoint stages
CHECKPOINT_STAGES = [
    "probe_completed",
    "stabilize_completed",
    "frame_extraction_completed",
    "upscale_batch_001",
    "upscale_batch_002",
    ...
    "encode_batch_001",
    "concat_completed",
    "output_uploaded",
]

# Checkpoint on each stage
def save_checkpoint(job_id: str, stage: str, details: dict):
    from platform_core.job_content import save_checkpoint
    save_checkpoint(job_id, stage, details)

# In upscale loop:
for bi in range(n_batches):
    save_checkpoint(job_id, f"upscale_batch_{bi:03d}", {
        "batch": bi,
        "total": n_batches,
        "frames_processed": bi * _BATCH_SIZE,
    })
    
    # Process batch...
```

**Resume logic:**
```python
def resume_if_partial(job_id):
    checkpoints = get_job_checkpoints(job_id)
    
    if "upscale_batch_050" in checkpoints:
        # Resume from batch 051
        batch_start = 51
    elif "concat_completed" in checkpoints:
        # Job complete, just return
        return get_completed_output(job_id)
```

### Implementation Effort

| Component | Effort | Complexity |
|-----------|--------|------------|
| Checkpoint storage | 1 hour | Low (DB write) |
| Resume logic | 1 hour | Medium |
| Error recovery | 1 hour | Medium |
| Testing | 1 hour | Medium |

**Total:** ~4 hours

### Recommendation

**Status:** P1 — Should implement for long jobs >2min

---

## 5. BOTTLENECK #5: SMOOTH MOTION CPU COST

**Priority:** P1 (High)  
**Location:** `apps/upscalevideo/ff.py:134-136`

### Problem Statement

```python
"minterpolate=fps=48:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
```

**Current:** FFmpeg minterpolate filter (CPU-only)

### Impact

⚠️ Bảng dưới là ước lượng, CHƯA ĐO trên bộ video test thật.

| Resolution | Source FPS | Output FPS | CPU Cost | 5min Runtime |
|------------|------------|------------|----------|--------------|
| 720p | 30 → 60 | 60 | ~100ms/frame | 300-500s |
| 1080p | 30 → 60 | 60 | ~200ms/frame | 600-1000s |
| 1440p | 30 → 60 | 60 | ~400ms/frame | 1200-2000s |

**CPU Utilization:** 80-100% while GPU idle

### Root Cause

minterpolate is a CPU-only filter. No GPU acceleration.

### Alternative: RIFE-NCNN-Vulkan

**RIFE (Real-Time Intermediate Flow Estimation)** with NCNN-Vulkan is significantly faster and better quality:

⛔ SAI toàn hàng "RIFE-NCNN-Vulkan" — RIFE KHÔNG BAO GIỜ được cài đặt: chỉ còn
lại `# TODO` chết ở `ff.py:138-140` (`# filters.append("rife=0")  # Uncomment
when RIFE binary available`). Đường chạy thật vẫn luôn là `minterpolate` CPU.
"~10ms/frame", "Better", "30 min effort" là ƯỚC LƯỢNG cho một thứ chưa từng
được xây, not a result.

| Feature | minterpolate | RIFE-NCNN-Vulkan (⛔ SAI — chưa cài đặt, chỉ là đề xuất) |
|---------|--------------|------------------|
| Engine | minterpolate filter | RIFE + NCNN |
| GPU Support | ❌ CPU only | ✅ Vulkan/CUDA |
| Speed | 100ms-400ms/frame | ~10ms/frame (ước lượng, chưa cài đặt) |
| Quality | Good | Better (ước lượng, chưa cài đặt) |
| Integration | Already there | 30 min effort (ước lượng) |

### Fix

**Vendor rife-ncnn-vulkan:**
1. Download `rife-ncnn-vulkan.exe` from reliable source
2. Bundle in `apps/upscalevideo/vendor/engine/`
3. Add `.pb` model files
4. Update `ff.py` to use RIFE filter

**FFmpeg filter:**
```bash
# With RIFE
ffmpeg -y -i input.mp4 -vf "rife=0" output.mp4
```

**Estimated effort:** 30 minutes

**Acceptance:** RIFE chưa từng được cài đặt (`ff.py:138-140`, chỉ `# TODO` chết);
đường chạy thật vẫn là `minterpolate` CPU.
- Smooth motion 2x speedup — ⛔ SAI, not applicable: RIFE chưa cài đặt, không có "speedup" nào để thu
- Lower CPU utilization
- Better temporal quality

### Recommendation

**Status:** P1 — Should vendor RIFE for GPU acceleration

---

## 6. BOTTLENECK #6: SINGLE GPU EXCLUSIVE RESERVATION

**Priority:** P1 (High)  
**Location:** `platform_core/gpu_claims.py`

### Problem Statement

```python
cm.publish(..., exclusive=True)
```

Each job reserves entire GPU via exclusive claim.

### Impact

**RTX 5060 Ti 16GB single GPU:**

| Job Mix | Max Jobs | Issue |
|---------|----------|-------|
| Quality only | 1 | Quality uses 11GB, leaves only 5GB for system |
| Fast only | 4 (2GB each) | Should support 12 (848MB each) |
| Mixed (Fast×2 + Quality×1) | 3 | Quality blocks all other jobs |

### Root Cause

Exclusive VRAM reservation for safety and simplicity.

### Proposed Solutions

| Solution | Complexity | Benefit | Risk |
|----------|------------|---------|------|
| **Shared VRAM** | Medium | More concurrent jobs | OOM risk |
| **Dynamic allocation** | High | Optimized VRAM usage | Complex |
| **Chunked release** | Medium | Release GPU between batches | Code change |

### Quick Fix: Chunked Processing

```python
# Instead of holding GPU for entire job:
for bi in range(n_batches):
    # Acquire GPU for this batch only
    lease = gl.acquire(db, worker_id, job_id, need_mb)
    
    # Process batch
    upscale_batch(bi)
    
    # Release GPU
    gl.release(db, lease)
    
    # Next batch...
```

**Benefit:** GPU can be shared between jobs in idle periods.

### Recommendation

**Status:** P1 — Should implement chunked processing

---

## 7. BOTTLENECK #7: NO MODEL WARMUP

**Priority:** P2 (Medium)  
**Location:** `apps/upscalevideo/engine.py:69-71`

### Problem Statement

```python
proc = subprocess.Popen([_engine(), ...])
```

Each job spawns NCNN subprocess, model loads from disk.

### Impact

**Cold start latency:** ~1-3 seconds per job (ước lượng, CHƯA ĐO)

⚠️ Bảng dưới là ước lượng, CHƯA ĐO. Cập nhật 2026-09-26: warmup được vá để ghim
đúng GPU (`gpu_index`+`env`), nhưng bản thân warmup KHÔNG giữ model trong VRAM
(tiến trình con thoát hẳn trước job thật) — lợi ích thật giới hạn ở cache tệp
OS/shader driver, không phải "cold start" biến mất như ngụ ý ở đây. Xem
`docs/UPSCALE_V2_CORRECTION/07_CORRECTION_PLAN.md` mục D/E/F.

| Job Queue Depth | Cold Start Overhead |
|-----------------|---------------------|
| 1 job | 1-3s |
| 10 jobs | 10-30s total |
| Queue wait 1min | 6-18s wasted |

### Root Cause

No model caching or warmup mechanism.

### Fix

```python
# Warmup models on worker startup
def warmup_models():
    for model in PRESET_MODEL.values():
        if model_available(model):
            test_inference(model)

# Or cache model in memory
_model_cache = {}

def run_upscale(model):
    if model not in _model_cache:
        _model_cache[model] = load_model(model)
    return _model_cache[model]
```

### Effort

- Model warmup: 30 min
- Caching logic: 1 hour

**Recommendation:** P2 — Nice to have but not critical

---

## 8. BOTTLENECK SUMMARY TABLE

| # | Bottleneck | Priority | Effort | Impact | ROI |
|---|------------|----------|--------|--------|-----|
| 1 | VRAM Over-allocation | P0 | 15 min | ⛔ SAI — "3x more concurrent jobs": `UniqueConstraint("host","gpu_uuid")` (`models.py:1037`) khoá đồng thời = 1, not 12 (ISSUE A) | ⭐⭐⭐⭐⭐ |
| 2 | PNG Disk I/O | P1 | 1-2 hours | 2-3x faster extraction (ước lượng, CHƯA ĐO — chưa triển khai) | ⭐⭐⭐⭐ |
| 3 | NVENC Gate | P1 | 15 min | ⛔ SAI — "10x faster encode on QSV/AMD": MEASURED 2026-09-26, QSV/AMF FAIL hoàn toàn ở runtime trên máy này; không có "faster" nào vì không chạy được (`docs/UPSCALE_V2_CORRECTION/05_ENCODER_TRUTH.md`) | ⭐⭐⭐⭐ |
| 4 | No Checkpoint | P1 | 4 hours | Zero waste on job crashes (ước lượng — checkpoint thật vẫn chỉ ghi sổ, không resume; xem ISSUE G) | ⭐⭐⭐⭐ |
| 5 | Smooth Motion CPU | P1 | 30 min | ⛔ SAI — "5-10x faster motion interp": RIFE chưa từng cài đặt (`ff.py:138-140`), đường chạy thật vẫn `minterpolate` CPU (ISSUE K) | ⭐⭐⭐ |
| 6 | Single GPU Exclusive | P1 | 2-3 hours | Better job parallelization (nghĩa là xen kẽ job kế tiếp giữa các đợt release/acquire theo batch — KHÔNG phải chạy đồng thời; đồng thời GPU vẫn luôn là 1) | ⭐⭐⭐ |
| 7 | No Model Warmup | P2 | 1.5 hours | Reduce cold start (ước lượng — warmup không giữ model trong VRAM, lợi ích thật giới hạn; ISSUE D/E) | ⭐⭐ |

**Total Implementation Effort:** ~10 hours  
**Expected Throughput Gain:** ⛔ SAI — "2-5x" phần lớn dựa trên giả định tăng
đồng thời GPU (hàng 1, 3, 5 ở trên đều SAI); phần còn lại (PNG I/O, checkpoint,
warmup) là CHƯA ĐO, không phải đã chứng minh.

---

## 9. PRIORITY IMPLEMENTATION ORDER

### Phase 1: Quick Wins (1 day)

1. **VRAM Over-allocation** (15 min)
2. **NVENC Gate** (15 min)
3. **Smooth Motion RIFE** (30 min)

**Phase 1 Impact:** ⛔ SAI — "5x speedup" cộng dồn từ VRAM Over-allocation
(SAI, ISSUE A) + NVENC Gate (SAI — QSV/AMF fail hoàn toàn, MEASURED 2026-09-26)
+ Smooth Motion RIFE (SAI — chưa cài đặt, ISSUE K). Cả ba nguồn của con số này
đều SAI hoặc không thực thi được.

### Phase 2: Infrastructure (2 days)

4. **No Checkpoint** (4 hours)
5. **Single GPU Chunked** (2-3 hours)

**Phase 2 Impact:** Reliability, throughput

### Phase 3: Optimization (3 days)

6. **PNG Disk I/O** (1-2 hours)
7. **Model Warmup** (1.5 hours)
8. **Profile & tune** (remaining time)

**Phase 3 Impact:** Long-term performance

---

## 10. RECOMMENDATIONS

### Immediate Actions

1. **Fix VRAM over-allocation** — 15 minutes
2. **Add NVENC fallback chain** — 15 minutes
3. **Vendor RIFE for smooth motion** — 30 minutes

### Medium-term (This sprint)

4. **Implement checkpoints** — 4 hours
5. **Tune PNG workflow** — 1-2 hours
6. **Model warmup** — 1.5 hours

### Long-term (Next sprint)

7. **Chunked GPU processing** — 2-3 hours
8. **Profile all stages** — 1 hour
9. **Add observability** — ongoing

---

**END OF BOTTLENECKS REPORT**
