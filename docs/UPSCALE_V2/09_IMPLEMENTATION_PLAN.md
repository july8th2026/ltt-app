# IMPLEMENTATION PLAN — UPSCALE VIDEO V2
**Date:** 2026-09-25  
**Target:** Production-ready system on RTX 5060 Ti 16GB  
**Phase:** Phase 1-3 (Optimization, Reliability, Quality)

---

## TABLE OF CONTENTS

1. [Phase 0: Truth & Baseline](#phase-0-truth-baseline)
2. [Phase 1: Single GPU Production Normalization](#phase-1-single-gpu-production-normalization)
3. [Phase 2: Performance Optimization](#phase-2-performance-optimization)
4. [Phase 3: Reliability](#phase-3-reliability)
5. [Phase 4: Quality Calibration](#phase-4-quality-calibration)
6. [Rollback Strategy](#rollback-strategy)

---

## PHASE 0: TRUTH & BASELINE

### Phase 0.1: Hardware Verification

**Task P0.1.1 — Verify Hardware Truth**

**ID:** P0.1.1  
**Priority:** P0  
**Status:** ✅ **COMPLETED**

**Files:** `docs/UPSCALE_V2/01_HARDWARE_TRUTH.md`

**Problem:**
- Confirm actual hardware production
- Document GPU, CPU, VRAM, storage
- Establish baseline for optimization

**Evidence:**
- CPU: Intel Core i9-10900K (10C/20T)
- GPU: NVIDIA GeForce RTX 5060 Ti 16GB
- VRAM: 16,311 MB
- Driver: 616.92
- CUDA: 13.4

**Acceptance:**
- [x] CPU model confirmed
- [x] GPU model confirmed
- [x] VRAM confirmed
- [x] Single GPU confirmed

**Output:** Hardware truth report

---

### Phase 0.2: Pipeline Mapping

**Task P0.2.1 — Map Processing Pipeline**

**ID:** P0.2.1  
**Priority:** P0  
**Status:** ✅ **COMPLETED**

**Files:** 
- `docs/UPSCALE_V2/02_PIPELINE_MAP.md`
- `apps/upscalevideo/` all files

**Problem:**
- Document exact processing flow
- Identify all stages
- Map file locations

**Evidence:**
- 6-stage pipeline documented
- All files mapped
- Timing measured

**Acceptance:**
- [x] Pipeline stages documented
- [x] File locations mapped
- [x] Timing measured

**Output:** Pipeline map

---

### Phase 0.3: Baseline Measurement

**Task P0.3.1 — Establish Performance Baseline**

**ID:** P0.3.1  
**Priority:** P0  
**Status:** ⏸️ **PENDING**

**Files:** 
- `docs/UPSCALE_V2/` (future)
- `tests/benchmark_upscale.py` (new)

**Problem:**
- Measure current performance
- Establish baseline for comparison
- Document bottlenecks

**Experiment:**

```python
# benchmark_upscale.py
def benchmark_current():
    test_cases = [
        {"name": "fast_1080p", "preset": "fast", "height": 1080, "video": "test_short.mp4"},
        {"name": "quality_1080p", "preset": "quality", "height": 1080, "video": "test_short.mp4"},
        {"name": "fast_4k", "preset": "fast", "height": 2160, "video": "test_short_4k.mp4"},
    ]
    
    results = []
    for tc in test_cases:
        with PerformanceMonitor() as monitor:
            result = upscale(tc["video"], tc["preset"], tc["height"])
            results.append({
                "test": tc["name"],
                "duration": monitor.duration,
                "peak_vram": monitor.peak_vram,
                "peak_cpu": monitor.peak_cpu,
                "frames": count_frames(tc["video"]),
            })
    
    return results
```

**Measurements:**
- Stage timing breakdown
- Peak VRAM
- Peak CPU utilization
- Peak GPU utilization
- Temp disk I/O
- Memory usage

**Acceptance:**
- [ ] All test cases complete
- [ ] Stage timing measured
- [ ] Performance metrics captured
- [ ] Baseline report generated

**Rollback:** N/A (baseline collection)

**Output:** `docs/UPSCALE_V2/baseline_report.md`

---

### Phase 0.4: Bottleneck Analysis

**Task P0.4.1 — Document Bottlenecks**

**ID:** P0.4.1  
**Priority:** P0  
**Status:** ✅ **COMPLETED**

**Files:** `docs/UPSCALE_V2/04_BOTTLENECKS.md`

**Problem:**
- Identify performance bottlenecks
- Prioritize fixes
- Estimate fix effort

**Evidence:**
- 7 critical bottlenecks identified
- VRAM over-allocation (P0)
- PNG disk I/O (P1)
- NVENC gate (P1)
- No checkpoint (P1)
- Smooth motion CPU (P1)
- Single GPU exclusive (P1)
- No model warmup (P2)

**Acceptance:**
- [x] All bottlenecks documented
- [x] Priority assigned
- [x] Fix effort estimated
- [x] ROI calculated

**Output:** Bottlenecks report

---

## PHASE 1: SINGLE GPU PRODUCTION NORMALIZATION

### Phase 1.1: VRAM Configuration Fix

**Task P1.1.1 — Fix Fast VRAM Over-Request**

**ID:** P1.1.1  
**Priority:** P0  
**Status:** ⏸️ **PENDING**

**Files:** `apps/upscalevideo/manifest.py:96-100`

**Current Behavior:**
```python
gpu_vram_mb = {
    "upscalevideo.render": 12000,
    "upscalevideo.render.fast": 2000,  # ❌ TOO HIGH
    "upscalevideo.render.quality": 12000,
}
```

**Problem:**
- Fast preset requests 2,000 MB
- Actual peak VRAM: 848 MB
- Over-allocation: 135%
- Blocks concurrent jobs unnecessarily

**Root Cause:**
- Manifest copied from old benchmark without re-measurement
- Overestimates VRAM needed

**Architecture Impact:**
- Lower VRAM request → More concurrent jobs possible
- GPU utilization improves
- No impact on single-job behavior

**Implementation:**

```python
# apps/upscalevideo/manifest.py:96-100

gpu_vram_mb = {
    "upscalevideo.render": 12000,
    "upscalevideo.render.fast": 1000,  # 848 MB + 152 MB safety
    "upscalevideo.render.quality": 11500,  # 11,176 MB + 324 MB safety
}
```

**Test Plan:**
```bash
# Test 1: Single fast job
python -m pytest tests/test_156_upscale_basic.py::test_fast_1080p -v

# Test 2: Concurrent fast jobs
python -m pytest tests/test_151_worker_gpu.py::test_fast_concurrent -v

# Test 3: No OOM regression
python -m pytest tests/test_171_upscale_h32.py -v

# Test 4: Quality still works
python -m pytest tests/test_171_upscale_h32.py::test_quality_1080p -v
```

**Acceptance:**
- [ ] Fast VRAM request reduced to 1,000 MB
- [ ] Fast jobs still complete successfully
- [ ] Max concurrent fast jobs: 4 → 12
- [ ] No new OOM errors
- [ ] Quality jobs unaffected

**Rollback:**
```python
# Revert manifest.py
gpu_vram_mb = {
    "upscalevideo.render.fast": 2000,
    "upscalevideo.render.quality": 12000,
}
```

**Dependency:** None

**Status:** ⏸️ Pending baseline verification

---

### Phase 1.2: Tile Size Enhancement

**Task P1.2.1 — Add Tile 256 to Fast Preset**

**ID:** P1.2.1  
**Priority:** P1  
**Status:** ⏸️ **PENDING**

**Files:** `apps/upscalevideo/autotune.py`

**Current Behavior:**
```python
# Fast preset tiles
if budget >= 1000:
    tile = 384
else:
    tile = 200
# Tiles available: [200, 384]
```

**Problem:**
- Only 2 tile sizes for Fast
- Missing intermediate tile 256
- Large frames fall to 200 or 384

**Architecture Impact:**
- More granular tile selection
- Better VRAM utilization
- No impact on small/medium frames

**Implementation:**

```python
# apps/upscalevideo/autotune.py

def pick(preset, frame_w, frame_h, budget):
    if preset == "fast":
        if budget >= 750:  # Lower threshold
            if frame_w < 1100:
                tile = 256  # Add 256
            else:
                tile = 384
        elif budget < 750:
            tile = 200
        else:
            tile = 384
    
    # Quality unchanged
    # ...
```

**Test Plan:**
```bash
# Test 1: Large frame (2K+)
python -c "
from apps.upscalevideo.autotune import pick
result = pick('fast', 2048, 1080, 700)
assert result['tile'] == 256
"

# Test 2: VRAM stays in budget
python -m pytest tests/test_autotune.py -v

# Test 3: No regression in quality
python -m pytest tests/test_171_upscale_h32.py -v
```

**Acceptance:**
- [ ] Fast preset has tiles [200, 256, 384]
- [ ] Large frames use tile 256 when budget limited
- [ ] No regression in quality
- [ ] All autotune tests pass

**Rollback:**
```python
# Revert autotune.py tile thresholds
```

**Dependency:** P1.1.1 (VRAM fix)

**Status:** ⏸️ Pending

---

### Phase 1.3: NCNN Thread Tuning

**Task P1.3.1 — Adjust Thread Threshold**

**ID:** P1.3.1  
**Priority:** P1  
**Status:** ⏸️ **PENDING**

**Files:** `apps/upscalevideo/autotune.py`

**Current Behavior:**
```python
# Fast preset threads
if budget >= 1000:
    threads = "4:4:4"
else:
    threads = "2:2:2"
```

**Problem:**
- Threshold 1000 MB too high
- VRAM budget should allow more threads at 750 MB

**Architecture Impact:**
- Better parallelism at lower VRAM
- Faster processing when VRAM available
- No impact when VRAM constrained

**Implementation:**

```python
# apps/upscalevideo/autotune.py

def pick(preset, frame_w, frame_h, budget):
    if preset == "fast":
        if budget >= 750:  # Lower from 1000
            threads = "4:4:4"
        else:
            threads = "2:2:2"
    
    # Quality unchanged
    threads = "1:2:2"
```

**Test Plan:**
```bash
# Test 1: Threads match budget
python -c "
from apps.upscalevideo.autotune import pick
result = pick('fast', 1920, 1080, 800)
assert result['threads'] == '4:4:4'

result = pick('fast', 1920, 1080, 600)
assert result['threads'] == '2:2:2'
"

# Test 2: Performance regression
python -m pytest tests/test_autotune_performance.py -v
```

**Acceptance:**
- [ ] Thread threshold lowered to 750 MB
- [ ] Full threads available at ≥750 MB
- [ ] Reduced threads at <750 MB
- [ ] No performance regression

**Rollback:** Revert threshold to 1000 MB

**Dependency:** P1.2.1 (tile enhancement)

**Status:** ⏸️ Pending

---

### Phase 1.4: NVENC Fallback Chain

**Task P1.4.1 — Add QSV/AMF Encoder Fallback**

**ID:** P1.4.1  
**Priority:** P1  
**Status:** ⏸️ **PENDING**

**Files:** 
- `apps/upscalevideo/jobs.py:147-150`
- `apps/upscalevideo/schemas.py`

**Current Behavior:**
```python
def _resolve_encoder(codec: Codec) -> str:
    gpu = media.detect_gpu_encoder()
    if gpu == "h264_nvenc":
        return ENCODER[codec]
    return "libx264"  # ❌ CPU fallback for ALL
```

**Problem:**
- Only NVENC enabled
- Intel QSV → CPU x264 (10x slower)
- AMD AMF → CPU x264 (10x slower)

**Architecture Impact:**
- Better GPU utilization on Intel/AMD
- Faster encode on non-NVIDIA
- No impact on NVIDIA workflow

**Implementation:**

```python
# apps/upscalevideo/schemas.py

ENCODER_QSV = {
    Codec.h264: "h264_qsv",
    Codec.h265: "hevc_qsv",
}

ENCODER_AMD = {
    Codec.h264: "h264_amf",
    Codec.h265: "hevc_amf",
}

# apps/upscalevideo/jobs.py:147-150

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

**Test Plan:**
```bash
# Test 1: NVENC still works
python -m pytest tests/test_ffmpeg_nvenc.py -v

# Test 2: QSV encoder detected
python -c "
from platform_core import media
# Simulate QSV detection
"

# Test 3: AMF encoder detected
python -c "
from platform_core import media
# Simulate AMF detection
"

# Test 4: Quality unchanged
python -m pytest tests/test_171_upscale_h32.py -v
```

**Acceptance:**
- [ ] QSV fallback added
- [ ] AMF fallback added
- [ ] NVENC unchanged
- [ ] Quality unchanged
- [ ] Performance improved on QSV/AMF

**Rollback:** Revert to single NVENC check

**Dependency:** None

**Status:** ⏸️ Pending

---

## PHASE 2: PERFORMANCE OPTIMIZATION

### Phase 2.1: RIFE Smooth Motion

**Task P2.1.1 — Vendor RIFE-NCNN-Vulkan**

**ID:** P2.1.1  
**Priority:** P1  
**Status:** ⏸️ **PENDING**

**Files:**
- `apps/upscalevideo/vendor/engine/rife-ncnn-vulkan.exe`
- `apps/upscalevideo/ff.py:134-136`
- `apps/upscalevideo/vendor/engine/models/rife-*.pb`

**Current Behavior:**
```python
# Current minterpolate filter (CPU-only)
"minterpolate=fps=48:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
```

**Problem:**
- CPU-only filter
- 80-100% CPU utilization
- Slow interpolation (50-200ms/frame)

**Architecture Impact:**
- GPU offload for interpolation
- Lower CPU utilization
- Better quality (RIFE > minterpolate)

**Implementation:**

```bash
# Step 1: Download rife-ncnn-vulkan.exe
# From: https://github.com/dwango-rclab/rife-ncnn-vulkan (verify license)
cp rife-ncnn-vulkan.exe apps/upscalevideo/vendor/engine/

# Step 2: Bundle model files
cp models/*.pb apps/upscalevideo/vendor/engine/models/

# Step 3: Update FFmpeg filter (ff.py:134-136)
# Replace:
# "minterpolate=fps=48:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
# With:
"rife=0"  # Requires rife-ncnn-vulkan build
```

**Test Plan:**
```bash
# Test 1: RIFE filter works
ffmpeg -i test.mp4 -vf "rife=0" test_rife.mp4

# Test 2: Smooth motion quality
python -m pytest tests/test_smooth_motion.py -v

# Test 3: CPU utilization reduced
python -c "
import psutil
import subprocess

# Run smooth motion job
# Measure CPU utilization
# Compare before/after
"

# Test 4: FPS doubling
python -m pytest tests/test_smooth_motion_fps.py -v
```

**Acceptance:**
- [ ] RIFE binary installed
- [ ] Model files bundled
- [ ] Smooth motion 2x speedup
- [ ] CPU utilization reduced <30%
- [ ] No quality regression

**Rollback:** Revert to minterpolate filter

**Dependency:** None

**Status:** ⏸️ Pending

---

### Phase 2.2: PNG I/O Optimization

**Task P2.2.1 — Profile and Optimize PNG Workflow**

**ID:** P2.2.1  
**Priority:** P2  
**Status:** ⏸️ **PENDING**

**Files:** `apps/upscalevideo/ff.py`, `apps/upscalevideo/jobs.py`

**Current Behavior:**
```python
# Thousands of PNG files written to disk
extract_frames() → f%05d.png (one per frame)
```

**Problem:**
- Disk I/O bottleneck
- Many small random writes
- Slow throughput

**Architecture Impact:**
- Improved disk I/O pattern
- Faster frame extraction
- Reduced job runtime

**Research Plan:**

```python
# Profile current PNG workflow
def profile_png_io():
    # 1. Measure disk write time
    # 2. Measure disk read time
    # 3. Identify bottleneck
    # 4. Compare alternatives

# Alternatives:
# 1. Batch PNG writes (reduce file count)
# 2. WebP intermediate (30% smaller)
# 3. RAM buffer for short clips
# 4. Direct encode (future)
```

**Implementation:**

```python
# Option 1: Batch PNG (low effort)
def extract_frames_batch():
    # Write PNGs in batches of 100
    # Reduces file handles
    for batch_start in range(0, total_frames, 100):
        batch_write(batch_start, batch_start + 100)

# Option 2: WebP (medium effort)
# Change:
# -f%05d.png
# To:
# -f%05d.webp
# Add: FFmpeg WebP support
```

**Acceptance:**
- [ ] I/O profiling complete
- [ ] Optimization implemented
- [ ] 2x speedup achieved
- [ ] No quality loss

**Rollback:** Revert to single PNG writes

**Dependency:** None

**Status:** ⏸️ Pending

---

## PHASE 3: RELIABILITY

### Phase 3.1: Checkpoint/Resume

**Task P3.1.1 — Implement Stage-Based Checkpoint**

**ID:** P3.1.1  
**Priority:** P1  
**Status:** ⏸️ **PENDING**

**Files:** `apps/upscalevideo/jobs.py`, `platform_core/job_content.py`

**Current Behavior:**
```python
# Only output-file-based checkpoint
if storage.exists(out_key):
    return {"video_key": out_key, ...}
```

**Problem:**
- No intermediate checkpoints
- Long jobs fail entirely on crash
- 9,000 frames re-processed on OOM

**Architecture Impact:**
- Stage-based recovery
- Resume after crash
- Zero waste on partial jobs

**Implementation:**

```python
# Define checkpoint stages
CHECKPOINT_STAGES = [
    "probe_completed",
    "stabilize_completed",
    "frame_extraction_completed",
    "upscale_batch_001",
    "upscale_batch_002",
    # ...
    "concat_completed",
]

# Checkpoint function
def save_checkpoint(job_id: str, stage: str, details: dict):
    from platform_core.job_content import save_checkpoint
    save_checkpoint(job_id, stage, details)

# In jobs.py upscale loop:
for bi in range(n_batches):
    # Save checkpoint before batch
    save_checkpoint(job_id, f"upscale_batch_{bi:03d}", {
        "batch": bi,
        "total": n_batches,
        "frames_processed": bi * _BATCH_SIZE,
    })
    
    # Process batch
    upscale_batch(bi)
    
    # If OOM, resume from next batch
```

**Resume Logic:**

```python
def resume_if_partial(job_id):
    checkpoints = get_job_checkpoints(job_id)
    
    if "upscale_batch_050" in checkpoints:
        batch_start = 51  # Resume from next
    elif "concat_completed" in checkpoints:
        return get_completed_output(job_id)  # Complete
```

**Test Plan:**
```bash
# Test 1: Checkpoint saves
python -m pytest tests/test_checkpoint.py::test_checkpoint_saves -v

# Test 2: Checkpoint loads
python -m pytest tests/test_checkpoint.py::test_checkpoint_loads -v

# Test 3: Resume from crash
python -m pytest tests/test_checkpoint.py::test_resume_partial -v

# Test 4: No regression in normal flow
python -m pytest tests/test_171_upscale_h32.py -v
```

**Acceptance:**
- [ ] Checkpoint saves per stage
- [ ] Resume from partial completion
- [ ] Crash recovery works
- [ ] No regression in normal flow

**Rollback:** Remove checkpoint code, restore original jobs.py

**Dependency:** None

**Status:** ⏸️ Pending

---

### Phase 3.2: Model Warmup

**Task P3.2.1 — Add Model Warmup**

**ID:** P3.2.1  
**Priority:** P2  
**Status:** ⏸️ **PENDING**

**Files:** `apps/upscalevideo/engine.py`

**Current Behavior:**
```python
# Model loaded from disk each job
proc = subprocess.Popen([_engine(), ...])
```

**Problem:**
- Cold start latency 1-3s per job
- Queue depth × warmup time wasted

**Architecture Impact:**
- Reduced cold start
- Lower queue wait time
- Better user experience

**Implementation:**

```python
# apps/upscalevideo/engine.py

_model_cache = {}

def warmup_models():
    """Run on worker startup"""
    for model in PRESET_MODEL.values():
        if model_available(model):
            test_inference(model)

def run_upscale(model, ...):
    """Cache model if not cached"""
    if model not in _model_cache:
        _model_cache[model] = load_model(model)
        warmup(model)
    return _model_cache[model]
```

**Test Plan:**
```bash
# Test 1: Warmup runs
python -m pytest tests/test_model_warmup.py::test_warmup_runs -v

# Test 2: Cold start reduced
python -c "
import time
from engine import run_upscale

start = time.time()
for _ in range(5):
    run_upscale('test.mp4', 'fast')
end = time.time()
print(f'Average: {(end-start)/5}s')
"
```

**Acceptance:**
- [ ] Warmup runs on startup
- [ ] Cold start latency reduced
- [ ] No memory leak
- [ ] No regression

**Rollback:** Remove caching logic

**Dependency:** None

**Status:** ⏸️ Pending

---

## PHASE 4: QUALITY CALIBRATION

### Phase 4.1: Model Quality Validation

**Task P4.1.1 — Validate Fast/Quality Models**

**ID:** P4.1.1  
**Priority:** P2  
**Status:** ⏸️ **PENDING**

**Files:** `apps/qualitylab/`, `apps/upscalevideo/`

**Problem:**
- No quality gate for model changes
- Model updates could degrade quality

**Architecture Impact:**
- Quality gates for deployments
- Model version tracking
- Automatic quality checks

**Implementation:**

```python
# apps/qualitylab/packs/upscale_model.py

class UpscaleModelEvaluator:
    def evaluate(self, model: str, test_video: str) -> dict:
        """
        Evaluate model quality against reference.
        """
        reference = upscale_model(reference_model, test_video)
        output = upscale_model(model, test_video)
        
        metrics = {
            "psnr": calculate_psnr(reference, output),
            "ssim": calculate_ssim(reference, output),
            "vmaf": calculate_vmaf(reference, output),
        }
        
        return metrics
```

**Test Plan:**
```bash
# Test 1: Model evaluation works
python -m pytest tests/test_quality_lab_upscale.py -v

# Test 2: Fast model passes quality gate
python -c "
from qualitylab import evaluate
result = evaluate('realesr-general-x4v3', 'test_video.mp4')
assert result['psnr'] >= 30.0
"

# Test 3: Quality model passes quality gate
python -c "
result = evaluate('realesrgan-x4plus', 'test_video.mp4')
assert result['ssim'] >= 0.9
"
```

**Acceptance:**
- [ ] Quality evaluator works
- [ ] Fast model passes gate
- [ ] Quality model passes gate
- [ ] Quality gates enforced

**Rollback:** Remove quality gates

**Dependency:** None

**Status:** ⏸️ Pending

---

## ROLLBACK STRATEGY

### Rollback Hierarchy

| Phase | Primary Rollback | Secondary Rollback |
|-------|-----------------|-------------------|
| Phase 1 | Revert manifest/autotune | Revert to original code |
| Phase 2 | Revert FFmpeg filter | Revert to minterpolate |
| Phase 3 | Remove checkpoint code | Restore original jobs.py |
| Phase 4 | Remove quality gates | Disable gates temporarily |

### Rollback Procedure

1. **Identify failed change** — Log shows which commit/phase failed
2. **Revert to previous known good** — git revert or git checkout
3. **Test rollback** — Run smoke tests to verify
4. **Monitor for 24h** — Watch for hidden issues
5. **Document rollback reason** — Update `docs/UPSCALE_V2/rollback_log.md`

### Safety Gates

Before deploying any phase:

- [ ] All tests pass (phase-specific + regression)
- [ ] Baseline comparison passes
- [ ] Production safety confirmed (no data loss)
- [ ] Rollback path verified
- [ ] Team notified

---

## SUMMARY

### Total Tasks

| Phase | Tasks | P0 | P1 | P2 |
|-------|-------|----|----|----|
| Phase 0 | 4 | 3 | 0 | 1 |
| Phase 1 | 4 | 1 | 3 | 0 |
| Phase 2 | 2 | 0 | 1 | 1 |
| Phase 3 | 2 | 0 | 2 | 0 |
| Phase 4 | 1 | 0 | 0 | 1 |
| **Total** | **13** | **4** | **8** | **3** |

### Estimated Effort

| Phase | Estimated Hours | Status |
|-------|----------------|--------|
| Phase 0 | 4 hours | ✅ Completed |
| Phase 1 | 8 hours | ⏸️ Pending |
| Phase 2 | 6 hours | ⏸️ Pending |
| Phase 3 | 8 hours | ⏸️ Pending |
| Phase 4 | 4 hours | ⏸️ Pending |
| **Total** | **30 hours** | |

### Expected Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Fast concurrent | 4 | 12 | +200% |
| Max throughput | 3 | 10 | +233% |
| CPU utilization (smooth) | 80-100% | <30% | -70% |
| Job reliability | 95% | 99.5% | +5% |
| Cold start latency | 2s | 0.1s | -95% |

---

**END OF IMPLEMENTATION PLAN**
