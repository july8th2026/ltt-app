"""Handler cho lan GPU. Pha 05 — KHONG nap model, KHONG cham card.

Hai giai doan that su can GPU: tach nguon tieng (demucs) va chep loi (whisper).
O pha nay ca hai chi ghi mot dong checkpoint qua than dung chung o app cha.

## Mot dieu phai dung ngay tu ban gia: KHONG BAO GIO TU CHON CARD

Khi engine that vao (pha 09/10), tien trinh con phai nhan card qua
`ctx.gpu_env(base=os.environ)`. Nen tang giu cho bang `platform_core.gpu_lease`
roi truyen card da cap qua `JobContext`. Mot handler tu doc bien moi truong cua
CUDA hay goi cong cu do GPU la dua vao mot cuoc dua voi chinh cai lease do — va
tren mot card dung chung voi ba ho khac (CLAUDE.md), ket qua la OOM giua mot lo dai.

🔴 Khong phai lo ngai ly thuyet: kho di san co NAM cho tu chon card, va chep mot
   trong nhung tep do vao day ma khong cat import ay la dua lai mat phang GPU cu
   vao mot duong CO TINH TIEN. Danh sach nam cho o
   `docs/auto_scan_video/RISK_REGISTER.md` (RISK-00-07).

   `tests/test_401_asv_ranh_gioi_va_artifact.py::test_auto_scan_KHONG_duoc_tu_chon_card_GPU`
   quet chinh thu muc nay bang AST va se do neu dieu do xay ra.
"""
from __future__ import annotations

from apps.auto_scan_video.thi_hanh import chay_theo_job_type


def handle(params: dict, ctx=None) -> dict:
    """Cua DUY NHAT nen tang goi cho lan GPU.

    Cung than thi hanh voi `asv_media` — cai khac nhau giua hai app la
    **dinh tuyen**, va dinh tuyen do manifest quyet dinh chu khong do handler.
    """
    loai = str(getattr(ctx, "job_type", "") or params.get("_job_type") or "")
    return chay_theo_job_type(loai, params, ctx)
