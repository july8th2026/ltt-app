# GPU OPTIMIZATION STRATEGY — RTX 5060 Ti 16GB
**Date:** 2026-09-25  
**Target:** Production-ready configuration for Upscale Video

---

## 1. GPU CONFIGURATION SUMMARY

### Hardware Truth

| Property | Value |
|----------|-------|
| **GPU Model** | NVIDIA GeForce RTX 5060 Ti |
| **VRAM Total** | 16,311 MB (~16 GB) |
| **Driver** | 616.92 (WDDM) |
| **CUDA** | 13.4 |
| **Core Count** | 1 single GPU |
| **CPU Partner** | Intel Core i9-10900K (10C/20T) |

### Current Configuration

| Parameter | Current Value | Actual Peak | Overhead |
|-----------|---------------|-------------|----------|
| **Fast VRAM request** | 2,000 MB | 848 MB | 135% |
| **Quality VRAM request** | 12,000 MB | 11,176 MB | 7% |
| **Fast tile sizes** | [200, 384] | [200, 384] | - |
| **Quality tile sizes** | [256, 320, 384, 448, 512] | - | - |
| **Fast threads** | `4:4:4` if budget≥1000 | - | - |
| **Quality threads** | `1:2:2` | - | - |

---

## 2. OPTIMIZED CONFIGURATION

### 2.1 VRAM Configuration

**Recommendation:**

```python
# apps/upscalevideo/manifest.py
gpu_vram_mb = {
    "upscalevideo.render": 12000,
    "upscalevideo.render.fast": 1000,   # 848 MB + 152 MB safety
    "upscalevideo.render.quality": 11500,  # 11,176 MB + 324 MB safety
}
```

**Rationale:**
- Fast: Reduce from 2,000 → 1,000 MB (50% reduction)
- Quality: Reduce from 12,000 → 11,500 MB (4% reduction)

**Impact:**
- ⛔ SAI — "Max concurrent fast jobs: 4 → 12 (tripling)" giả định kế toán VRAM cộng
  dồn nhiều job trên một GPU; `GpuLease.UniqueConstraint("host","gpu_uuid")`
  (`platform_core/models.py:1037`) khoá đồng thời GPU = **1**, not 12
  (ISSUE A, `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md`). Con số
  `gpu_vram_mb` chỉ đổi sàn nhận MỘT job đang xin (ISSUE B), không mua thêm job.
- Quality margin: 824 MB → 525 MB — đúng số học, nhưng không có "throughput" nào
  để thu vì Quality vẫn chỉ chạy 1 job tại một thời điểm.

### 2.2 Tile Configuration

**Fast Preset:**
- Current: `[200, 384]`
- Recommended: `[200, 256, 384]`
- Rationale: 256 for large frames with VRAM margin

**Quality Preset:**
- Current: `[256, 320, 384, 448, 512]`
- Recommended: Keep as-is
- Rationale: Full range needed for quality

**Tile VRAM Estimation (Fast):**

⛔ SAI — bộ số dưới đây không khớp cái nào với `autotune.py` đang chạy (bản cũ
đưa một bộ số THỨ BA, khác cả hai bộ đã có). Mã thật (`autotune.py:96-98,120-127`)
dùng `est_alloc` **cố định** theo dải: Fast 1000/500 MB; Quality 10024/9314/
7025/5095/3513 MB. Xem `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md` ISSUE C.

| Tile Size | VRAM Allocation (bản cũ, không khớp mã) | Use Case |
|-----------|-----------------|----------|
| 200 | ~600 MB | Small frames, VRAM constrained |
| 256 | ~750 MB | Medium frames, balanced |
| 384 | ~950 MB | Large frames, max quality |

**Tile VRAM Estimation (Quality):**

| Tile Size | VRAM Allocation (bản cũ, không khớp mã — xem ISSUE C) | Use Case |
|-----------|-----------------|----------|
| 256 | ~3,500 MB | Low VRAM budget |
| 320 | ~4,200 MB | Moderate budget |
| 384 | ~5,500 MB | Balanced budget |
| 448 | ~7,000 MB | High budget |
| 512 | ~9,000 MB | Max budget |

### 2.3 NCNN Thread Configuration

**Format:** `load:proc:save`

**Recommendation per preset:**

**Fast Preset:**
```python
# VRAM budget ≥ 800 MB: Full threading
# VRAM budget < 800 MB: Reduced threading
```

⛔ SAI — "Lower to 800 MB" (và một chú thích khác trong `autotune.py` từng nói
"750 MB") KHÔNG PHẢI ngưỡng đang chạy. Ngưỡng thật là `est_alloc = 1000`
(`autotune.py:99,103`), khớp `manifest.py`'s `gpu_vram_mb.fast = 1000` (848 MB
đỉnh đo được + 152 MB an toàn). Đề xuất 750/800 MB ở đây **chưa bao giờ được
triển khai** — xem `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md` ISSUE C.

**Code change in `autotune.py`:** ⛔ SAI — mã thật không có nhánh `budget >= 800`;
xem `autotune.py:103` (`if budget < est_alloc` với `est_alloc = 1000`).

```python
if budget >= 800:
    threads = "4:4:4"  # Full parallelism
else:
    threads = "2:2:2"  # Reduced for VRAM
```

**Quality Preset:**
```python
# Always conservative for large VRAM allocations
threads = "1:2:2"
```

**Rationale:**
- Quality uses 11GB+ VRAM → Conservative threading
- Fast can afford full threading with lower VRAM

### 2.4 Concurrency Limits

**RTX 5060 Ti 16GB Single GPU:**

⛔ SAI — bảng dưới đây giả định nhiều job chia sẻ VRAM trên một GPU. Thật ra
`GpuLease.UniqueConstraint("host","gpu_uuid")` (`models.py:1037`) khoá đồng
thời GPU = 1 bất kể preset (ISSUE A). "Max Jobs" > 1 ở mọi hàng dưới đây SAI.

| Preset Mix | Max Jobs (bản cũ, SAI) | GPU Util | VRAM Used | Safety Margin |
|------------|----------|----------|-----------|---------------|
| Fast only | 12 | 75% | 10 GB | 6 GB |
| Quality only | 1 | 90% | 11 GB | 5 GB |
| Mixed (Fast×8 + Quality×1) | 9 | 80% | 14 GB | 2 GB |

**Recommended Production Limits:**
- Fast: ⛔ SAI — "Max 8 concurrent (leaves safety margin)"; thật là **1**, not 12 (ISSUE A).
- Quality: Max 1 concurrent (single GPU) — đúng, và đây là trần cho MỌI preset.
- Mixed: ⛔ SAI — không có "limit total to 8"; đồng thời GPU luôn là 1.

**Why not max theoretical?**
- Safety margin for system operations
- Buffer for peak moments
- Prevent OOM spikes

### 2.5 NVENC Configuration

**Current:**
```bash
-c:v h264_nvenc -preset p5 -cq 19 -pix_fmt yuv420p
```

**Recommendation:**

| Preset | Encoder | Preset | CQ | Rationale |
|--------|---------|--------|-----|-----------|
| **Fast** | h264_nvenc | p5 | 23 | Faster, slightly more compression |
| **Quality** | h264_nvenc | p2 | 19 | Better quality, slower |

**Preset mapping:**
- p0 = fastest (lowest quality)
- p1 = faster
- p2 = very fast
- p3 = fast
- p4 = medium
- p5 = slow (current)
- p6 = slowness

**Quality vs Speed Tradeoff:**
- Fast preset: Accept more compression for speed → CQ 23
- Quality preset: Prioritize quality → CQ 19, p2 preset

### 2.6 Tile Tuning Strategy

**Auto-tuning algorithm (autotune.py):**

```python
def pick(preset, frame_w, frame_h, budget):
    if preset == "fast":
        if frame_w < 1100 and budget >= 750:
            return {"tile": 256, "threads": "4:4:4"}
        elif frame_w < 1100 and budget < 750:
            return {"tile": 200, "threads": "2:2:2"}
        else:
            return {"tile": 384, "threads": "4:4:4"}
    
    if preset == "quality":
        if budget >= 9000:
            return {"tile": 512, "threads": "1:2:2"}
        elif budget >= 7000:
            return {"tile": 448, "threads": "1:2:2"}
        elif budget >= 5500:
            return {"tile": 384, "threads": "1:2:2"}
        elif budget >= 4500:
            return {"tile": 320, "threads": "1:2:2"}
        else:
            return {"tile": 256, "threads": "1:2:2"}
```

**Changes from current:**
1. Add tile 256 to Fast preset
2. Adjust VRAM thresholds
3. Align threads with VRAM budget

---

## 3. PERFORMANCE TARGETS

### 3.1 Baseline (Current State)

| Metric | Value |
|--------|-------|
| Fast VRAM request | 2,000 MB |
| Fast peak VRAM | 848 MB |
| Quality VRAM request | 12,000 MB |
| Quality peak VRAM | 11,176 MB |
| Max concurrent fast | ⛔ SAI — "4 (theoretical)": `exclusive=True` (`gpu_lease.py:201-203`) đã giữ TRỌN card từ trước; đồng thời luôn là 1, not 4 |
| Max concurrent quality | 1 |
| Smooth motion engine | CPU minterpolate |
| Fast encode codec | NVENC p5 cq19 |
| Quality encode codec | NVENC p5 cq19 |

### 3.2 Optimized Targets

| Metric | Target | Improvement |
|--------|--------|-------------|
| Fast VRAM request | 1,000 MB | -50% |
| Max concurrent fast | 12 | ⛔ SAI — "+3x": `UniqueConstraint("host","gpu_uuid")` (`models.py:1037`) khoá đồng thời = 1, not 12 (ISSUE A) |
| Max concurrent quality | 1 | - |
| Smooth motion engine | GPU RIFE | ⛔ SAI — "+10x": RIFE chưa từng cài đặt (`ff.py:138-140`), vẫn `minterpolate` CPU (ISSUE K) |
| Fast encode | NVENC p5 cq23 | +20% speed (ước lượng, CHƯA ĐO) |
| Quality encode | NVENC p2 cq19 | +50% quality (ước lượng, CHƯA ĐO) |

### 3.3 Throughput Calculation

⛔ SAI toàn mục — cả hai bảng dưới đây và kết luận cộng dồn từ chúng đều dựa
trên giả định >1 job GPU đồng thời (4 rồi 12) VÀ trên RIFE (chưa cài đặt).
Đồng thời GPU thật là **1** (ISSUE A, `models.py:1037`); RIFE không tồn tại
(ISSUE K, `ff.py:138-140`). Không có "throughput" nào để tính theo cách này.

**Current (RTX 5060 Ti 16GB):** (bản cũ, SAI — xem trên)

| Preset | Max Concurrent (SAI) | Time per Job (5min) | Throughput (SAI, not 12) |
|--------|----------------|---------------------|------------|
| Fast | 4 | 5-10 min | 0.5-0.8 jobs/min |
| Quality | 1 | 15-30 min | 0.03-0.06 jobs/min |

**Optimized (with RIFE):** (bản cũ, SAI — xem trên, RIFE chưa cài đặt ISSUE K)

| Preset | Max Concurrent (⛔ SAI, not 12 — ISSUE A) | Time per Job (5min) | Throughput (⛔ SAI) |
|--------|----------------|---------------------|------------|
| Fast | 12 | 2-4 min | 2.5-5 jobs/min |
| Quality | 1 | 8-15 min (with RIFE) | 0.06-0.12 jobs/min |

**Total throughput improvement:** ⛔ SAI — "Fast 3-5x", "Overall 3x" tính từ
hai bảng SAI ở trên (đồng thời 4→12 không có thật, RIFE không tồn tại), not 12.

---

## 4. IMPLEMENTATION PLAN

### Phase 1: VRAM Configuration (15 minutes)

**File:** `apps/upscalevideo/manifest.py:96-100`

**Change:**
```diff
 gpu_vram_mb = {
-    "upscalevideo.render.fast": 2000,
+    "upscalevideo.render.fast": 1000,
-    "upscalevideo.render.quality": 12000,
+    "upscalevideo.render.quality": 11500,
 }
```

**Testing:**
1. Verify fast jobs still work
2. Test concurrent job scheduling
3. Monitor OOM events

**Rollback:** Revert to 2000 if needed

### Phase 2: Tile Sizes (30 minutes)

**File:** `apps/upscalevideo/autotune.py`

**Change:** Add tile 256 to Fast preset thresholds

**Testing:**
1. Test with various frame sizes
2. Verify VRAM stays within budget
3. No regression in quality

### Phase 3: NCNN Threads (30 minutes)

**File:** `apps/upscalevideo/autotune.py`

**Change:** Lower VRAM threshold from 1000 → 800 MB for Fast preset

**Testing:**
1. Test on small VRAM GPU
2. Test on large VRAM GPU
3. Verify threading matches budget

### Phase 4: NVENC Configuration (15 minutes)

**File:** `apps/upscalevideo/jobs.py:189-196`
**File:** `apps/upscalevideo/schemas.py`

**Change:** Adjust NVENC preset and CQ per preset

**Testing:**
1. Compare Fast quality vs speed
2. Compare Quality quality
3. Verify NVENC still works

### Phase 5: RIFE Integration (1 hour)

**Vendor:** Download and test rife-ncnn-vulkan

**File:** `apps/upscalevideo/ff.py:134-136`

**Change:** Replace minterpolate with RIFE filter

**Testing:**
1. Test smooth motion quality
2. Measure CPU reduction
3. Verify 2x FPS doubling

### Phase 6: Validation (2 hours)

**Test suite:**
1. Single job performance
2. Concurrent job stress test
3. Memory usage validation
4. Quality regression check
5. Error handling validation

---

## 5. MONITORING METRICS

### 5.1 Key Metrics to Track

| Metric | Tool | Threshold |
|--------|------|-----------|
| Fast concurrent jobs | `admin-telemetry` | ⛔ SAI — "Max 8"; đồng thời GPU thật là **1**, not 12 (ISSUE A, `models.py:1037`) |
| Quality concurrent jobs | `admin-telemetry` | Max 1 |
| Peak VRAM per job | `GpuEvidenceSampler` | Fast: <1.2GB, Quality: <11.5GB |
| GPU utilization | `nvidia-smi` | Target 70-85% |
| Job queue time | `admin-telemetry` | Alert >5min |
| OOM errors | Logs | Zero |
| STALL events | `engine.py` | Alert >0 |

### 5.2 Performance Gates

| Metric | Before | After | Gate |
|--------|--------|-------|------|
| Fast VRAM request | 2,000 MB | 1,000 MB | 1,000 ± 50 |
| Max concurrent fast | 4 | 12 | ⛔ SAI — "≥ 12" không đo được vì không tồn tại: đồng thời GPU = 1 (ISSUE A) |
| Quality VRAM request | 12,000 MB | 11,500 MB | 11,500 ± 300 |
| Fast threads (budget≥800) | 4:4:4 | 4:4:4 | 4:4:4 |
| Fast threads (budget<800) | 2:2:2 | 2:2:2 | 2:2:2 |
| Fast tile sizes | [200, 384] | [200, 256, 384] | Contains all 3 |
| Quality tile sizes | [256,320,384,448,512] | Same | All 5 present |

### 5.3 Performance Baseline Tests

| Test | Before | After | Pass |
|------|--------|-------|------|
| Fast job time (5min) | 5-10 min | 2-4 min (ước lượng, CHƯA ĐO) | ≤ 4 min |
| Fast concurrent | 4 jobs | 12 jobs | ⛔ SAI — không đo được vì không tồn tại: đồng thời GPU = 1 (ISSUE A) |
| Quality job time (5min) | 15-30 min | 8-15 min | ⛔ SAI — số "8-15 min" giả định có RIFE; RIFE chưa cài đặt (ISSUE K) |
| GPU memory peak (Fast) | 848 MB | 848 MB | Same |
| GPU memory peak (Quality) | 11,176 MB | 11,176 MB | Same |
| CPU utilization (smooth) | 80-100% | <30% | ⛔ SAI — mức <30% giả định RIFE thay CPU minterpolate; RIFE chưa cài đặt (ISSUE K) |

---

## 6. SAFETY CHECKLIST

Before deploying optimized configuration:

- [ ] VRAM reduction doesn't cause OOM
- [ ] All concurrent jobs complete successfully
- [ ] No new STALL events
- [ ] No new OOM fallback events
- [ ] Quality scores unchanged
- [ ] Encoding successful with new settings
- [ ] Smooth motion works with RIFE
- [ ] Error handling still works
- [ ] Telemetry accurate
- [ ] Production safety: no rollback path broken

---

## 7. ROLLBACK PLAN

### VRAM Configuration Rollback

If OOM errors occur:
1. Revert `manifest.py` to original values
2. Monitor for 24 hours
3. Analyze OOM patterns
4. Adjust thresholds incrementally

### Tile Size Rollback

If quality issues occur:
1. Revert `autotune.py` tile thresholds
2. Test original configuration
3. Debug: log tile selection decisions
4. Adjust thresholds conservatively

### NCNN Threads Rollback

If performance degrades:
1. Revert thread thresholds
2. Test performance
3. Adjust threshold gradually

### RIFE Integration Rollback

If quality issues occur:
1. Revert `ff.py` to minterpolate
2. Test original configuration
3. Debug RIFE integration
4. Adjust RIFE parameters

---

## 8. EXPECTED OUTCOMES

### 8.1 Performance

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Fast throughput | 0.5-0.8 jobs/min | 2.5-5 jobs/min | ⛔ SAI — "+300-500%" dựa trên đồng thời 4→12, không tồn tại (ISSUE A) |
| Quality throughput | 0.03-0.06 jobs/min | 0.06-0.12 jobs/min | ⛔ SAI — "+100%" dựa trên thời gian job có RIFE, RIFE chưa cài đặt (ISSUE K) |
| Smooth motion CPU | 80-100% | <30% | ⛔ SAI — "-70%" dựa trên RIFE thay CPU minterpolate; chưa cài đặt (ISSUE K) |
| Smooth motion time | 5-10x longer | 1-2x longer | ⛔ SAI — "+4-8x" dựa trên RIFE; chưa cài đặt (ISSUE K) |

### 8.2 Business Impact

- User wait time reduced by 70% — ⛔ SAI, cộng dồn từ các con số SAI ở 8.1 (ISSUE A + K)
- Production capacity tripled — ⛔ SAI — đồng thời GPU = 1, not 12 (ISSUE A)
- Cost per job reduced (more throughput) — ⛔ SAI — không có "more throughput" từ đồng thời (ISSUE A)
- Better customer satisfaction — CHƯA ĐO (không có khảo sát/số liệu nào dẫn nguồn)

### 8.3 Technical Benefits

- Optimized VRAM usage
- Better GPU utilization
- Improved error handling
- Enhanced observability

---

**END OF GPU OPTIMIZATION STRATEGY**
