"""Handler cho lan `voice`. Sinh tieng noi cho tung doan ban dich.

Cung khuon voi `asv_media`/`asv_gpu`: mot lop DINH TUYEN mong. Vong doi giai
doan nam o app cha (`apps/auto_scan_video/thi_hanh.py`); executor ton tai de
mang mot `manifest.requires` hep, chu khong de mang logic.

Xem `apps/asv_media/jobs.py` de biet vi sao phai la app rieng thay vi mot
`job_type` trong app khac.
"""
from __future__ import annotations

from apps.auto_scan_video.thi_hanh import chay_theo_job_type


def handle(params: dict, ctx=None) -> dict:
    """Cua DUY NHAT nen tang goi cho lan `voice`."""
    loai = str(getattr(ctx, "job_type", "") or params.get("_job_type") or "")
    return chay_theo_job_type(loai, params, ctx)
