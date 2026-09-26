# PHASE 3.1.1: CHECKPOINT/RESUME SYSTEM

## OVERVIEW

**Status:** IMPLEMENTING

**Goal:** Add stage-based checkpoint/resume for long jobs (5min+ videos).

**Benefits (mục tiêu ban đầu — ⛔ SAI, không đạt được):**
- Zero waste on job crashes (OOM, STALL)
- ⛔ SAI — "Resume from last completed stage" KHÔNG được xây: `load_checkpoint`/
  `get_job_checkpoints` không có caller nào trong cả kho; chỉ có `save_`
  (ISSUE G, `docs/UPSCALE_V2_CORRECTION/03_CHECKPOINT_TRUTH.md`)
- Better reliability (99%+ completion rate) — CHƯA ĐO, không đo được vì resume không tồn tại

## CURRENT STATE

**Jobs resume only if output already exists** (line 279-284):
```python
if storage.exists(out_key):
    return {"video_key": out_key, ...}
```

**Problem:** No intermediate checkpoint → entire job re-processed on crash.

## IMPLEMENTATION PLAN

### Step 1: Checkpoint Storage

Add checkpoint function that saves job state:

```python
def save_checkpoint(job_id: str, stage: str, details: dict):
    """Save checkpoint for job."""
    from platform_core.job_content import save_checkpoint
    save_checkpoint(job_id, stage, details)
```

### Step 2: Resume Logic

Check checkpoints before resuming:

```python
def resume_if_partial(job_id):
    """Check if job can resume from checkpoint."""
    checkpoints = get_job_checkpoints(job_id)
    
    if "probe_completed" in checkpoints:
        # Resume from stabilize stage
        ...
    if "frame_extraction_completed" in checkpoints:
        # Resume from upscale stage
        ...
    if "upscale_batch_050" in checkpoints:
        # Resume from batch 051
        ...
```

### Step 3: Checkpoint Stages

```python
CHECKPOINT_STAGES = [
    "probe_completed",
    "stabilize_completed",
    "frame_extraction_completed",
    "upscale_batch_001",
    "upscale_batch_002",
    # ... up to 100 batches
    "encode_batch_001",
    "concat_completed",
    "output_uploaded",
]
```

## FILES TO MODIFY

1. `apps/upscalevideo/jobs.py` — Add checkpoint calls
2. `platform_core/job_content.py` — Checkpoint storage (if needed)

## ESTIMATED EFFORT

- **Checkpoint logic:** 1 hour
- **Resume logic:** 1 hour
- **Testing:** 2 hours
- **Total:** 4 hours

## NEXT ACTION

**Should I implement checkpoint/resume now?**

Answer: YES — proceed with implementation.
