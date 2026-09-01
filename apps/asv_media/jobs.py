"""Handler cho lan ffmpeg. Pha 05 — cong viec ben trong con la GIA.

## Vi sao tep nay mong den vay

Vong doi mot giai doan (doc co pham vi chu so huu, van tay + lineage, chot tran
chi, ghi checkpoint) nam o app cha: `apps/auto_scan_video/thi_hanh.py`. Executor
chi la mot lop DINH TUYEN — no ton tai de mang mot `manifest.requires` hep, chu
khong de mang logic.

Ban dau than thi hanh nam o day va `asv_gpu` import `_chay_giai_doan` sang.
`tools/lint_app_contract.py` chan lai va no dung: mot ten mo dau bang gach duoi
la mot loi hua rieng tu. Xem ghi chu dau `thi_hanh.py`.

⛔ Pha 05 cam Whisper / Demucs / LLM that / TTS that / render that.
"""
from __future__ import annotations

from apps.auto_scan_video.thi_hanh import chay_theo_job_type


def handle(params: dict, ctx=None) -> dict:
    """Cua DUY NHAT nen tang goi.

    ⭐ Doc `ctx.job_type` truoc, `params` sau: `ctx` la thu **nen tang** cap nen
       no khong the bi mot params dung san lam sai lech. Cung loi
       `apps/ltt_voice/jobs.py:78`.
    """
    loai = str(getattr(ctx, "job_type", "") or params.get("_job_type") or "")
    return chay_theo_job_type(loai, params, ctx)
