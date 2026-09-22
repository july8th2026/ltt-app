"""Executor AN cua Auto Scan Video — lan `gpu`.

Hai giai doan, ca hai deu nap model len card: tach nguon tieng (demucs) va chep
loi (whisper). Xem `apps/asv_media/manifest.py` de biet vi sao phai la mot app
rieng thay vi mot `job_type` trong app kia.

## `gpu_vram_mb` — con so phai DO roi moi khai

Nen tang dung con so nay lam **san de xep cho**: no loai cac card khong con du
trong, roi giu cho nguyen tu qua `platform_core.gpu_lease`. Khai thieu thi job
bi xep vao card chat va OOM; khai thua thi job cho lau hon can thiet.

✅ **`asv_gpu.audio_prepare` DA DUOC DO** — pha 13, ngay 03/09, tren venv san
   pham (`torch 2.11.0+cu128`, RTX 5060 Ti 16 GiB), qua nam do dai tu 60 giay
   den 7.200 giay (dung tran `nhap_media.THOI_LUONG_TOI_DA_S`):

     VRAM dinh do duoc: 1.089 - 1.673 MiB, **khong doi theo do dai dau vao**.

   Khai **2.200** = dinh cao nhat do duoc + ~30% du. Truoc pha 13 cho nay khai
   4.000 — mot uoc luong chua do, va no thua 2,4 lan, tuc moi lan xep cho lai
   loai oan nhung card con thua 2 GiB.

⚠️ `asv_gpu.transcribe` VAN chua do — no muon con so cua `autosubvideo.transcribe`.

## 🔴 Va cai KHONG khai duoc o day moi la cai nguy hiem

Pha 13 do ra rang voi demucs, **VRAM la thu KHONG tang theo do dai** — RAM moi
tang, va tang tuyen tinh:

    truoc pha 13:  RSS ~ 1.253 MB + 3,35 MB moi giay tieng
                   => mot video 120 phut (HOP LE) can ~24,8 GiB tren mot may
                      co 31,9 GiB va ~17,8 GiB trong khi dang phuc vu khach

`AppManifest` co `gpu_vram_mb` nhung **khong co truong nao de khai RAM**. Tuc
tai nguyen duy nhat that su tang theo dau vao la tai nguyen nen tang khong nhin
thay. Pha 13 xu ly bang cach **chan muc tieu thu trong app** — tach theo khoi,
xem `demucs_runner.KHOI_GIAY` — nen sau pha 13 RSS phang o ~2,6 GiB o MOI do
dai (do that: 2.246 MB o 600 s, 2.605 MB o 3.600 s, 2.591 MB o 7.200 s).

⛔ Nhung do la **chua xu ly cai lo hong o hop dong**, chi la khong con di qua no.
   Ghi ra day thay vi tu them mot truong vao `AppManifest`: sua nen tang nam
   ngoai pham vi pha 13, va mot lo hong hop dong duoc va lang le trong mot app
   thi app SAU se lai roi vao no.

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

    job_types=("asv_gpu.audio_prepare", "asv_gpu.transcribe",
               "asv_gpu.qc_do_luong"),
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
        # ✅ DO THAT pha 13 (03/09): dinh 1.673 MiB, khong doi theo do dai.
        "asv_gpu.audio_prepare": 2200,
        "asv_gpu.transcribe": 6000,      # theo `autosubvideo.transcribe` da do
        # __VRAM_DO_LUONG__
    },
    max_runtime_s={
        "asv_gpu.audio_prepare": 3600,
        "asv_gpu.transcribe": 3600,
        "asv_gpu.qc_do_luong": 3600,
    },
    #: GPU tren may nay dung chung voi ba ho khac (CLAUDE.md). Cho 20 giay giua
    #: hai lan hoi la hop ly cho viec dai hang phut; day khong phai truong hop
    #: cua LTT VOICE (viec 5 giay, phai hoi day hon).
    cho_tai_nguyen_s={"asv_gpu.audio_prepare": 20, "asv_gpu.transcribe": 20,
                      "asv_gpu.qc_do_luong": 20},
    notes="Pha 05: handler GIA, khong nap model, khong cham GPU that.",
)
