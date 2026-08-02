"""Redacted operational telemetry for the admin-only Upscale panel."""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone

from sqlalchemy import func, select

from platform_core.models import JOB_QUEUED, JOB_RUNNING, Job


def gpu_snapshot(run=subprocess.run) -> dict:
    command = ["nvidia-smi",
               "--query-gpu=name,utilization.gpu,temperature.gpu,memory.total,memory.used",
               "--format=csv,noheader,nounits"]
    try:
        result = run(command, capture_output=True, text=True, timeout=4, check=False)
        if result.returncode != 0 or not result.stdout.strip():
            return {"available": False}
        name, util, temp, total, used = [part.strip()
                                         for part in result.stdout.splitlines()[0].split(",")]
        return {"available": True, "model": name, "util_percent": int(float(util)),
                "temp_c": int(float(temp)), "vram_total_mb": int(float(total)),
                "vram_used_mb": int(float(used))}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {"available": False}


def storage_snapshot(storage) -> dict:
    root = getattr(storage, "root", None)
    if root is None:
        return {"available": False, "backend": storage.__class__.__name__}
    try:
        usage = shutil.disk_usage(root)
        return {"available": True, "backend": "local",
                "disk_total_bytes": usage.total, "disk_used_bytes": usage.used,
                "disk_free_bytes": usage.free}
    except OSError:
        return {"available": False, "backend": "local"}


def queue_snapshot(db) -> dict:
    counts = dict(db.execute(select(Job.status, func.count()).where(
        Job.app_slug == "upscalevideo").group_by(Job.status)).all())
    running = db.execute(select(Job).where(
        Job.app_slug == "upscalevideo", Job.status == JOB_RUNNING)).scalars().all()
    now = datetime.now(timezone.utc)
    workers = []
    for row in running:
        heartbeat = row.heartbeat_at or row.started_at
        if heartbeat and heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=timezone.utc)
        age = int(max(0, (now - heartbeat).total_seconds())) if heartbeat else None
        workers.append({"worker_id": row.worker_id or "unassigned",
                        "heartbeat_age_s": age, "stale": age is None or age > 300})
    return {"queued": int(counts.get(JOB_QUEUED, 0)),
            "running": int(counts.get(JOB_RUNNING, 0)),
            "workers": workers, "required_capabilities": ["gpu", "ffmpeg"]}
