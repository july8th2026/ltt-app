# VIDEO PROCESSING PIPELINE MAP — UPSCALE VIDEO
**Date:** 2026-09-25  
**Scope:** apps/upscalevideo/ complete processing flow  
**Purpose:** Understand exact stages, dependencies, timing

---

## 1. COMPLETE PIPELINE DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        UPCSACLE VIDEO PIPELINE                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  CLIENT UPLOAD│
│              │
│  1. Local (<90MB) → staging session → R2         │
│  2. Direct R2 (>90MB) via presigned URL          │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   PROBE      │
│              │
│  ffprobe     │
│  - duration │
│  - resolution│
│  - fps      │
│  - frames   │
│  - audio    │
│  - vfr/cfr  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   DISK GUARD │
│              │
│  Check free space ≥ frames*area + margin (1.3x)  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  STABILIZE (Optional) │
│                       │
│  libvidstab 2-pass:   │
│  detect → transform   │
│  (CPU, libx264)       │
└──────┬────────┘
       │ SKIP IF DISABLED
       │
       ▼
┌──────────────────────┐
│   FRAME EXTRACTION   │
│                      │
│  FFmpeg:             │
│  - fps=cfr_fps       │
│  - OR minterpolate   │
│    (smooth motion)   │
│  Output: f%05d.png   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│   GPU UPSCALE        │
│                      │
│  autotune.pick() →   │
│  tile size + threads │
│                      │
│  Real-ESRGAN NCNN    │
│  -g vulkan_index     │
│  -t tile_size        │
│  -j threads          │
│                      │
│  Chunk >360 frames   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│   PER-CHUNK ENCODE   │
│                      │
│  FFmpeg encode_segment()│
│  NVENC (p5, cq19)     │
│  OR libx264 (crf18)   │
│  Output: seg_XXXX.mp4│
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│   CONCAT + MUX AUDIO │
│                      │
│  FFmpeg concat + mux  │
│  -f concat            │
│  Video: copy          │
│  Audio: copy          │
│  Output: output.mp4   │
└──────┬───────────────┘
       │
       ▼
┌──────────────┐
│   UPLOAD     │
│              │
│  Storage put │
│  Final key   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  SETTLMENT   │
│              │
│  True cost   │
│  Release hold│
└──────────────┘
```

---

## 2. STAGE-BY-STAGE BREAKDOWN

### STAGE 0: UPLOAD & STORAGE

**File:** `apps/upscalevideo/routes.py:434-563`  
**File:** `apps/upscalevideo/upload_sessions.py`

```python
# Two paths:
# 1. Local browser upload (<90MB)
POST /queue
  → upload_sessions.stage_bytes()
  → confirm()
  → promote()

# 2. Direct R2 upload (>90MB)
POST /upload-url
  → create_upload_session()
  → presigned PUT to R2
```

**Timing:** Variable (network dependent)

**Storage Locations:**
```
staging/{user_id}/{app_slug}/{session_id}/payload.mp4
upscalevideo/{user_id}/inputs/{job_id}.mp4
upscalevideo/{owner_id}/{job_id}/output_preview.mp4
upscalevideo/{owner_id}/{job_id}/output_1080p.mp4
```

---

### STAGE 1: PROBE & GUARD

**File:** `apps/upscalevideo/jobs.py:216-265`  
**File:** `apps/upscalevideo/ff.py:61-119`

**Code:**
```python
# jobs.py:223
info = ff.probe_video(video_key)
# Returns: {w, h, fps, fps_str, duration, nb_frames, has_audio, vcodec, is_vfr, rotation}

# jobs.py:268
if storage.exists(out_key):
    return {"video_key": out_key, "credit_cost": true_cost, ...}

# jobs.py:274
true_cost = cost.uoc_luong_credit(
    info["duration"],
    target_height,
    preset,
    preview,
    stabilize,
    smooth_motion
)

# jobs.py:278
_guard_disk(tmp, true_cost)
```

**Timing:** 1-2 seconds

**Disk Guard Calculation:**
```python
# jobs.py:269
frames = info.get("nb_frames", duration * fps)
src_area = width * height
batches = (frames + _BATCH_SIZE - 1) // _BATCH_SIZE
up_area = target_width * target_height

# Estimate PNG size: 3 bytes per pixel × area × 1.3 safety
space_needed = frames * src_area * 3 + batches * up_area * 3 * 1.3
```

---

### STAGE 2: STABILIZATION (OPTIONAL)

**File:** `apps/upscalevideo/ff.py:147-190`  
**Library:** libvidstab (via FFmpeg filter)

**Code:**
```python
def stabilize_video(src, out_dir):
    # Pass 1: Detection
    detect_out = os.path.join(out_dir, "detect.txt")
    cmd = [
        _ff(), "-y", "-i", src,
        "-vf", "vidstabdetect=shakiness=5:accuracy=9",
        detect_out
    ]
    
    # Pass 2: Transform
    transform_out = os.path.join(out_dir, "stabilized.mp4")
    cmd += [
        "-vf", "vidstabtransform=smoothing=10:optzoom=1:zoom_method=50",
        "-c:v", "libx264", "-preset", "medium",
        transform_out
    ]
    
    proc = subprocess.run(cmd, capture_output=True)
    return transform_out
```

**Timing:** 10-30 seconds (depends on duration)

**Audio:** Zero-copy mux from original

---

### STAGE 3: FRAME EXTRACTION

**File:** `apps/upscalevideo/ff.py:122-144`

**Code:**
```python
def extract_frames(src, out_dir, cfr_fps=None, max_seconds=None, interpolate_fps=None):
    os.makedirs(out_dir, exist_ok=True)
    
    cmd = [_ff(), "-y", "-i", src]
    
    # CFR or VFR->CFR normalization
    if cfr_fps:
        cmd += ["-vf", f"fps={cfr_fps}"]
    
    # Or Smooth Motion interpolation
    if interpolate_fps:
        cmd += [
            "-vf", f"minterpolate=fps={interpolate_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
        ]
    
    # Output: PNG files
    out_path = os.path.join(out_dir, "f%05d.png")
    cmd += [out_path]
    
    proc = subprocess.run(cmd, capture_output=True)
    
    return list(out_dir.glob("f*.png"))
```

**Timing:** **CRITICAL BOTTLENECK**
- 300 frames (10s @ 30fps): ~15-30 seconds
- 9,000 frames (5min @ 30fps): ~3-5 minutes
- 18,000 frames (5min @ 60fps): ~6-10 minutes

**Output:**
```
ltt_upscale_XXXXXX/
  f00000.png
  f00001.png
  ...
  f00299.png
```

**Disk I/O:** 700MB-7GB write (1 file per frame)

---

### STAGE 4: GPU UPSCALING

**File:** `apps/upscalevideo/engine.py:69-113`  
**File:** `apps/upscalevideo/autotune.py:6-119`  
**File:** `apps/upscalevideo/vulkan_device.py:1-136`

**Code:**
```python
# 1. Auto-tune VRAM → tile size + threads
tune = autotune.pick(preset, frame_w, frame_h, reserve_mb=3000, gpu_uuid=lease.uuid)

# 2. Build NCNN command
cmd = [
    _engine(),
    "-g", vulkan_device.vulkan_index_for(selected.name),  # Vulkan index by card name
    "-t", str(tune.tile),
    "-j", tune.threads,
]

# Add model
model_path = _get_model_path(tune.model)
cmd += ["-m", model_path, "-n", model_path.replace(".param", ".bin")]

# 3. Process in batches
if n_frames <= _BATCH_SIZE:
    # Single batch
    proc = subprocess.run(cmd + [batch_dir, out_dir], capture_output=True)
else:
    # Multiple batches
    for bi in range(batches):
        batch_dir = os.path.join(batch_root, f"b{bi:03d}")
        # ... upscale batch ...
        # If OOM: fallback tile/2
```

**Timing:** 30 seconds to 10+ minutes (depends on frames, model, tile)

**VRAM Usage:**
- Fast (general-x4v3): 600-900 MB
- Quality (x4plus): 3,500-10,000 MB (tile-dependent)

**NCNN Thread Settings:**
```python
# Format: "load:proc:save"
Fast:
  - budget ≥ 1000 MB: "4:4:4"
  - budget < 1000 MB: "2:2:2"
Quality:
  - Always: "1:2:2"
```

**Stall Watchdog:** 300 seconds (5 minutes) — kills if no progress

**OOM Fallback:** tile → tile/2 (max 200)

---

### STAGE 5: ENCODING & MUXING

**File:** `apps/upscalevideo/ff.py:199-254`

**Encode Per-Segment:**
```python
def encode_segment(batch_up, seg, cfr_fps):
    cmd = [_ff(), "-y", "-framerate", str(cfr_fps), "-i", batch_up,
           "-vf", f"scale=-2:{target_h}:flags=lanczos",
           "-r", str(cfr_fps),
           "-c:v", "h264_nvenc" if nvenc else "libx264",
           
           # NVENC settings
           "-preset", "p5", "-cq", "19", "-pix_fmt", "yuv420p",
           
           # x264 fallback
           "-crf", "18",
           
           # Mux audio
           "-i", src_for_audio, "-map", "0:v:0", "-map", "1:a:0",
           "-c:a", "copy",
           seg]
    
    proc = subprocess.run(cmd, capture_output=True)
```

**Concat & Mux:**
```python
def concat_and_mux(segments, src, target_h, cfr_fps, target_name):
    concat_file = os.path.join(out_dir, "segments.concat.txt")
    # Write concat list
    
    cmd = [_ff(), "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
           "-i", src,
           "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "copy", "-c:a", "copy",
           target_name]
    
    proc = subprocess.run(cmd, capture_output=True)
```

**Timing:** 10-60 seconds (encode), 1-5 seconds (concat)

**Codec Mapping:**
```python
# NVENC available:
# - H.264: h264_nvenc, preset p5, cq 19
# - H.265: hevc_nvenc, tag hvc1
# Fallback: libx264, crf 18
```

---

### STAGE 6: UPLOAD & SETTLEMENT

**File:** `apps/upscalevideo/jobs.py:350-361`

**Code:**
```python
# jobs.py:350
tags = ["preview"] if preview else [target_h]
if stabilize: tags.append("-stabilized")
if smooth_motion: tags.append("-smooth2x")

# Full key: upscalevideo/{owner_id}/{job_id}/output_{tags[0]}.mp4
out_key = f"upscalevideo/{owner_id}/{job_id}/output_{'_'.join(tags)}.mp4"

# Store result
storage.put(out_key, output_path, access="public")

# Credit settlement
true_cost = cost.uoc_luong_credit(...)
credit._hoan_credit(db, job_id, true_cost)
```

**Timing:** 1-10 seconds (upload speed dependent)

---

## 3. CRITICAL TIMING BREAKDOWN

| Stage | Short (10s) | Medium (5min) | Long (30min) |
|-------|-------------|---------------|--------------|
| **Upload** | 2s | 10s | 1min |
| **Probe** | 2s | 2s | 2s |
| **Stabilize** | SKIP | 15s | 90s |
| **Extract Frames** | 5s | 2min | 12min |
| **Upscale** | 5s | 3min | 30min |
| **Encode** | 5s | 30s | 5min |
| **Concat** | 2s | 2s | 5s |
| **Upload** | 5s | 10s | 50s |
| **TOTAL** | **~25s** | **~6-7min** | **~50-60min** |

**Note:** Smooth Motion doubles FPS → ×2 extraction + upscale time

---

## 4. BOTTLENECK ANALYSIS

### Bottleneck 1: PNG Frame Extraction ⚠️

**Issue:** Thousands of small file writes to disk

**Impact:**
- 1080p 5min video: 9,000 PNG files
- 4K 5min video: 36,000 PNG files

**Disk I/O:**
- Write: 7GB (1080p) to 28GB (4K)
- Latency: Thousands of small random writes

**Solutions:**
1. Direct FFmpeg encode (eliminate PNG step)
2. WebP intermediate (30% smaller — ước lượng, CHƯA ĐO)
3. RAM buffer for short clips (<60s)
4. Optimize PNG compression

---

### Bottleneck 2: GPU Upscaling

**Issue:** Single GPU, exclusive VRAM reservation

**Impact:**
- 1 Quality job blocks all others
- 12 Fast jobs can run concurrently (theoretical)

**Current:**
- Fast peak: ~848 MB
- Quality peak: ~11,176 MB
- Manifest request: Fast 2,000 MB, Quality 12,000 MB

**Issue:** Over-allocating VRAM blocks more jobs

---

### Bottleneck 3: NVENC Gate Too Strict

**Issue:** Only NVENC if `h264_nvenc` detected, fallback to CPU

**Impact:**
- Intel GPU → libx264 (slow)
- AMD GPU → libx264 (slow)

**Current:**
```python
if gpu == "h264_nvenc":
    return ENCODER[codec]
return "libx264"  # All other GPUs → CPU
```

**Should be:**
```python
if gpu == "h264_nvenc":
    return ENCODER[codec]
elif gpu == "h264_qsv":  # Intel QuickSync
    return ENCODER_QSV[codec]
elif gpu == "h264_amf":  # AMD AMF
    return ENCODER_AMD[codec]
return "libx264"  # Final fallback
```

---

### Bottleneck 4: No Checkpoint/Resume

**Issue:** Job fails → all work lost

**Impact:**
- 5min video upscale to frame 200/1000: All 200 frames re-processed
- OOM during upscale: Entire job retry

**Current:**
```python
# Only checkpoint at output file existence
if storage.exists(out_key):
    return {"video_key": out_key, ...}
```

**Should be:**
```python
# Stage-based checkpoints
save_checkpoint("frame_extracted", {"count": n_frames})
save_checkpoint("upscale_batch_001", {"batch": 0})
save_checkpoint("encode_batch_001", {"segment": "seg_0001.mp4"})
```

---

## 5. RESOURCE ESTIMATION

### Memory
```python
# CPU RAM
Python process: ~200 MB
FFmpeg process: ~50 MB per instance
Temp storage: Varies (see below)
DB connection: ~10 MB
```

### Disk Space

| Video | Duration | Resolution | Frames | PNG Size | Temp Needed |
|-------|----------|------------|--------|----------|-------------|
| 1080p | 10s | 1920×1080 | 300 | 700 MB | 1 GB |
| 1080p | 5min | 1920×1080 | 9,000 | 3.5 GB | 4 GB |
| 4K | 10s | 3840×2160 | 300 | 2.8 GB | 3 GB |
| 4K | 5min | 3840×2160 | 9,000 | 14 GB | 15 GB |

**Note:** Batch processing reduces peak temp usage to ~4-5GB even for long videos

### GPU VRAM
```python
Fast (general-x4v3):
  - Tile 200: ~600 MB
  - Tile 384: ~850 MB
  - Tile 512: ~1,000 MB
  
Quality (x4plus):
  - Tile 256: ~3,500 MB
  - Tile 384: ~7,000 MB
  - Tile 512: ~10,000 MB
```

---

## 6. ERROR HANDLING BY STAGE

| Stage | Error Type | Recovery | User Message |
|-------|-----------|----------|--------------|
| **Upload** | File too large | 413 | "Video quá 90MB, dùng upload thẳng" |
| **Upload** | Invalid format | 400 | "Format không hỗ trợ" |
| **Probe** | Corrupted file | 400 | "File hỏng hoặc không phải video" |
| **Stabilize** | FFmpeg error | 500 | "Xử lý video thất bại" |
| **Extract** | Disk full | 507 | "Không đủ dung lượng tạm" |
| **Upscale** | OOM | Retry (tile/2) | "Tự động giảm chất lượng" |
| **Upscale** | STALL | Kill & error | "Engine treo, thử lại" |
| **Upscale** | OOM (final) | Fail | "VRAM không đủ" |
| **Encode** | NVENC fail | x264 fallback | "Dùng CPU encode" |
| **Concat** | FFmpeg error | 500 | "Ghép video thất bại" |
| **Upload** | Storage error | 503 | "Lưu trữ không khả dụng" |

---

## 7. SINGLE-GPU CONCURRENT LIMITS

**RTX 5060 Ti 16GB**

⛔ SAI — cả bảng dưới đây giả định kế toán VRAM cộng dồn nhiều job trên một GPU.
`GpuLease` có `UniqueConstraint("host","gpu_uuid")` (`platform_core/models.py:1037`):
một GPU một máy = tối đa MỘT lease sống = **1** job GPU, bất kể `vram_mb` khai bao
nhiêu (`platform_core/gpu_lease.py:179` loại GPU đã có lease khỏi ứng viên mà
không xét `need_mb`). "Mixed"/"Fast×N" dưới đây chưa từng và không thể chạy đồng
thời. Xem `docs/UPSCALE_V2_CORRECTION/00_CURRENT_TRUTH.md` ISSUE A (not 12).

| Preset Mix | Max Jobs (bản cũ, SAI) | GPU Util | VRAM Used | Safety Margin |
|------------|----------|----------|-----------|---------------|
| Fast only | 12 | 75% | 10 GB | 6 GB |
| Quality only | 1 | 90% | 11 GB | 5 GB |
| Mixed (Fast×2 + Quality×1) | 3 | 85% | 13 GB | 3 GB |
| Mixed (Fast×8 + Quality×1) | 9 | 80% | 14 GB | 2 GB |

**Recommendation:**
- Fast: ⛔ SAI — bản cũ ghi "Max 8 concurrent (safety margin)"; sự thật là **1** (ISSUE A), not 12.
- Quality: Max 1 concurrent — đúng, và đây là trần chung cho MỌI preset (không riêng Quality).
- Mixed: ⛔ SAI — không có khái niệm "limit total to 8"; đồng thời GPU luôn là 1.

---

**END OF PIPELINE MAP**
