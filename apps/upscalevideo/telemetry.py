"""Redacted operational telemetry for the admin-only Upscale panel."""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone

from sqlalchemy import func, select

from platform_core.models import JOB_QUEUED, JOB_RUNNING, Job


def gpu_snapshot(run=subprocess.run) -> dict:
    """Trạng thái MỌI GPU cho bảng quản trị.

    Bản trước đọc `stdout.splitlines()[0]` nên chỉ báo card đầu tiên. Từ
    2026-08-06 máy có hai card — bảng quản trị hiện một card là nói dối người
    vận hành đúng lúc họ cần biết card nào đang nóng/đầy.

    `gpus` là danh sách đầy đủ. Các khoá phẳng (`model`, `util_percent`, …) giữ
    lại và trỏ vào card ĐẦU TIÊN, chỉ để giao diện cũ không vỡ khi triển khai
    lệch nhịp; giao diện mới đọc `gpus`.
    """
    command = ["nvidia-smi",
               "--query-gpu=name,utilization.gpu,temperature.gpu,memory.total,memory.used",
               "--format=csv,noheader,nounits"]
    try:
        result = run(command, capture_output=True, text=True, timeout=4, check=False)
        if result.returncode != 0 or not result.stdout.strip():
            return {"available": False, "gpus": []}
        gpus = []
        for index, line in enumerate(result.stdout.strip().splitlines()):
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 5:
                continue
            name, util, temp, total, used = parts
            gpus.append({"index": index, "model": name,
                         "util_percent": int(float(util)), "temp_c": int(float(temp)),
                         "vram_total_mb": int(float(total)),
                         "vram_used_mb": int(float(used))})
        if not gpus:
            return {"available": False, "gpus": []}
        dau = gpus[0]
        return {"available": True, "gpus": gpus, "count": len(gpus),
                "model": dau["model"], "util_percent": dau["util_percent"],
                "temp_c": dau["temp_c"], "vram_total_mb": dau["vram_total_mb"],
                "vram_used_mb": dau["vram_used_mb"]}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {"available": False, "gpus": []}


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
