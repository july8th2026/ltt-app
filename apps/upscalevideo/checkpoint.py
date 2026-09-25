"""
checkpoint.py — Job checkpoint system for stage-based resume.

Each job can checkpoint progress at defined stages. On crash/OOM,
the job can resume from the last completed stage.

Checkpoint storage uses JSON file with DB-backed job state.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from platform_core import db

CHECKPOINT_TABLE = "upscalevideo_checkpoint"


def get_checkpoint_path(job_id: str, stage: str) -> Path:
    """Get checkpoint file path for job+stage."""
    temp_dir = Path(os.environ.get("LTT_UPSCALE_TEMP", "tmp/upscale"))
    return temp_dir / job_id / f"{stage}.json"


def save_checkpoint(job_id: str, stage: str, details: dict | None = None):
    """Save checkpoint for job stage.

    Args:
        job_id: Unique job identifier
        stage: Stage name (e.g., "probe_completed", "upscale_batch_001")
        details: Optional stage details
    """
    from platform_core.storage import get_storage

    temp_dir = Path(os.environ.get("LTT_UPSCALE_TEMP", "tmp/upscale"))
    temp_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_file = temp_dir / job_id / f"{stage}.json"
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

    checkpoint_data = {
        "job_id": job_id,
        "stage": stage,
        "timestamp": time.time(),
        "details": details or {},
    }

    # Save to temp file (not R2, too expensive)
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint_data, f)


def load_checkpoint(job_id: str, stage: str) -> dict:
    """Load checkpoint for job stage.

    Returns empty dict if no checkpoint exists.
    """
    from platform_core.storage import get_storage

    temp_dir = Path(os.environ.get("LTT_UPSCALE_TEMP", "tmp/upscale"))
    checkpoint_file = temp_dir / job_id / f"{stage}.json"

    if not checkpoint_file.exists():
        return {}

    try:
        with open(checkpoint_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def get_job_checkpoints(job_id: str) -> dict[str, dict]:
    """Get all checkpoints for a job.

    Returns dict of stage_name -> checkpoint_data
    """
    temp_dir = Path(os.environ.get("LTT_UPSCALE_TEMP", "tmp/upscale"))
    job_dir = temp_dir / job_id

    if not job_dir.exists():
        return {}

    checkpoints = {}
    for stage_file in job_dir.glob("*.json"):
        stage = stage_file.stem
        checkpoints[stage] = load_checkpoint(job_id, stage)

    return checkpoints


def cleanup_job_checkpoints(job_id: str):
    """Remove all checkpoints for completed/failed job."""
    temp_dir = Path(os.environ.get("LTT_UPSCALE_TEMP", "tmp/upscale"))
    job_dir = temp_dir / job_id

    if job_dir.exists():
        import shutil
        shutil.rmtree(job_dir, ignore_errors=True)


# Define checkpoint stages in order
CHECKPOINT_STAGES = [
    "probe_completed",
    "stabilize_completed",
    "frame_extraction_completed",
    # Upscale batches (dynamically numbered)
    "upscale_batch_",  # Will be formatted as upscale_batch_001, upscale_batch_002, ...
    "encode_batch_",  # Will be formatted as encode_batch_001, encode_batch_002, ...
    "concat_completed",
    "output_uploaded",
]
