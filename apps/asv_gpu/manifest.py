"""Executor AN cua Auto Scan Video — lan `gpu`.

Hai giai doan, ca hai deu nap model len card: tach nguon tieng (demucs) va chep
loi (whisper). Xem `apps/asv_media/manifest.py` de biet vi sao phai la mot app
rieng thay vi mot `job_type` trong app kia.

## `gpu_vram_mb` — con so phai DO roi moi khai

Nen tang dung con so nay lam **san de xep cho**: no loai cac card khong con du
trong, roi giu cho nguyen tu qua `platform_core.gpu_lease`. Khai thieu thi job
bi xep vao card chat va OOM; khai thua thi job cho lau hon can thiet.

⚠️ Hai so duoi la **uoc luong tam cua pha 05**, va chung phai duoc do lai truoc
   khi engine that chay (pha 09/10). Kho nay co mot luat rieng cho viec do —
   *"CHUA DO THI KHONG CHAY"* — va `render_gateway/ngan_sach.py` tu choi moi cau
   hinh vuot muc da do **truoc khi cham GPU**. Dat mot con so cho co roi quen
   la dung cach de mot lo dai chet giua chung.

   Tham chieu de so sanh, deu do that va ghi trong CLAUDE.md:
     `upscalevideo` quality  12.000 MB
     `autosubvideo.transcribe` 6.000 MB
     LTT VOICE (VieNeu-TTS)      641 MB dinh
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest


def _gia(params: dict) -> int:
    """Luon 0 — chi `asv_run` giu tien (ADR-001 D4). Xem `asv_media/manifest.py`."""
    return 0


MANIFEST = AppManifest(
    slug="asv_gpu",
    display_name=N_('Auto Scan Video — xử lý GPU'),
    route_prefix="/asv-gpu",
    summary=N_('Executor nội bộ của Auto Scan Video. Không phải sản phẩm riêng.'),
    icon="🧠",

    catalog_parent="auto_scan_video",
    surface="runtime",
    public=False,
    enabled=False,
    lifecycle="internal",

    job_types=("asv_gpu.audio_prepare", "asv_gpu.transcribe"),
    requires=("gpu",),
    credit_cost=_gia,

    #: ⚠️ VAN LA UOC LUONG. Pha 09 da noi demucs that vao, nhung KHONG do duoc
    #:    VRAM: `torch` tren may nay la ban CPU-only (`2.11.0+cpu`,
    #:    `cuda False`), nen phep tach chay tren CPU va khong cham card nao.
    #:
    #: 🔴 Luat cua kho la "CHUA DO THI KHONG CHAY". Truoc khi cho `asv_gpu` chay
    #:    tren mot may co card, phai do that roi sua hai so nay.
    #:    `tests/test_406_asv_tach_tieng.py::TestChoBangChungNgoai` se DO ngay
    #:    khi may co CUDA — no la thu nhac, khong phai mot loi hua suong.
    #:
    #: Do duoc tren may nay (CPU, torch 2.11.0+cpu): 3 giay stereo 44,1 kHz ->
    #: 4,3 giay tach. Tuc RTF ~1,4x thoi gian thuc tren CPU; do la ly do giai
    #: doan nay can lan GPU chu khong phai chay chung voi lan ffmpeg.
    gpu_vram_mb={
        "asv_gpu.audio_prepare": 4000,   # htdemucs — CHUA DO
        "asv_gpu.transcribe": 6000,      # theo `autosubvideo.transcribe` da do
    },
    max_runtime_s={
        "asv_gpu.audio_prepare": 3600,
        "asv_gpu.transcribe": 3600,
    },
    #: GPU tren may nay dung chung voi ba ho khac (CLAUDE.md). Cho 20 giay giua
    #: hai lan hoi la hop ly cho viec dai hang phut; day khong phai truong hop
    #: cua LTT VOICE (viec 5 giay, phai hoi day hon).
    cho_tai_nguyen_s={"asv_gpu.audio_prepare": 20, "asv_gpu.transcribe": 20},
    notes="Pha 05: handler GIA, khong nap model, khong cham GPU that.",
)
