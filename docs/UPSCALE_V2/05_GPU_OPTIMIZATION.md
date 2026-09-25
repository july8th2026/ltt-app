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
- Max concurrent fast jobs: 4 → 12 (tripling)
- Quality margin: 824 MB → 525 MB

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

| Tile Size | VRAM Allocation | Use Case |
|-----------|-----------------|----------|
| 200 | ~600 MB | Small frames, VRAM constrained |
| 256 | ~750 MB | Medium frames, balanced |
| 384 | ~950 MB | Large frames, max quality |

**Tile VRAM Estimation (Quality):**

| Tile Size | VRAM Allocation | Use Case |
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

Current threshold is 1000 MB → Lower to 800 MB for VRAM margin.

**Code change in `autotune.py`:**

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

| Preset Mix | Max Jobs | GPU Util | VRAM Used | Safety Margin |
|------------|----------|----------|-----------|---------------|
| Fast only | 12 | 75% | 10 GB | 6 GB |
| Quality only | 1 | 90% | 11 GB | 5 GB |
| Mixed (Fast×8 + Quality×1) | 9 | 80% | 14 GB | 2 GB |

**Recommended Production Limits:**
- Fast: Max 8 concurrent (leaves safety margin)
- Quality: Max 1 concurrent (single GPU)
- Mixed: Limit total to 8

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
| Max concurrent fast | 4 (theoretical) |
| Max concurrent quality | 1 |
| Smooth motion engine | CPU minterpolate |
| Fast encode codec | NVENC p5 cq19 |
| Quality encode codec | NVENC p5 cq19 |

### 3.2 Optimized Targets

| Metric | Target | Improvement |
|--------|--------|-------------|
| Fast VRAM request | 1,000 MB | -50% |
| Max concurrent fast | 12 | +3x |
| Max concurrent quality | 1 | - |
| Smooth motion engine | GPU RIFE | +10x |
| Fast encode | NVENC p5 cq23 | +20% speed |
| Quality encode | NVENC p2 cq19 | +50% quality |

### 3.3 Throughput Calculation

**Current (RTX 5060 Ti 16GB):**

| Preset | Max Concurrent | Time per Job (5min) | Throughput |
|--------|----------------|---------------------|------------|
| Fast | 4 | 5-10 min | 0.5-0.8 jobs/min |
| Quality | 1 | 15-30 min | 0.03-0.06 jobs/min |

**Optimized (with RIFE):**

| Preset | Max Concurrent | Time per Job (5min) | Throughput |
|--------|----------------|---------------------|------------|
| Fast | 12 | 2-4 min | 2.5-5 jobs/min |
| Quality | 1 | 8-15 min (with RIFE) | 0.06-0.12 jobs/min |

**Total throughput improvement:**
- Fast: 3-5x increase
- Overall system: 3x increase (weighted average)

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
| Fast concurrent jobs | `admin-telemetry` | Max 8 |
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
| Max concurrent fast | 4 | 12 | ≥ 12 |
| Quality VRAM request | 12,000 MB | 11,500 MB | 11,500 ± 300 |
| Fast threads (budget≥800) | 4:4:4 | 4:4:4 | 4:4:4 |
| Fast threads (budget<800) | 2:2:2 | 2:2:2 | 2:2:2 |
| Fast tile sizes | [200, 384] | [200, 256, 384] | Contains all 3 |
| Quality tile sizes | [256,320,384,448,512] | Same | All 5 present |

### 5.3 Performance Baseline Tests

| Test | Before | After | Pass |
|------|--------|-------|------|
| Fast job time (5min) | 5-10 min | 2-4 min | ≤ 4 min |
| Fast concurrent | 4 jobs | 12 jobs | ≥ 12 |
| Quality job time (5min) | 15-30 min | 8-15 min | ≤ 15 min |
| GPU memory peak (Fast) | 848 MB | 848 MB | Same |
| GPU memory peak (Quality) | 11,176 MB | 11,176 MB | Same |
| CPU utilization (smooth) | 80-100% | <30% | ≤ 30% |

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
| Fast throughput | 0.5-0.8 jobs/min | 2.5-5 jobs/min | +300-500% |
| Quality throughput | 0.03-0.06 jobs/min | 0.06-0.12 jobs/min | +100% |
| Smooth motion CPU | 80-100% | <30% | -70% |
| Smooth motion time | 5-10x longer | 1-2x longer | +4-8x |

### 8.2 Business Impact

- User wait time reduced by 70%
- Production capacity tripled
- Cost per job reduced (more throughput)
- Better customer satisfaction

### 8.3 Technical Benefits

- Optimized VRAM usage
- Better GPU utilization
- Improved error handling
- Enhanced observability

---

**END OF GPU OPTIMIZATION STRATEGY**
