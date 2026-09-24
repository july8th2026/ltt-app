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

    #: 🔴 **Ghi chu cu o day khai SAI, va cai sai do giu phep do treo 20 ngay.**
    #:
    #:    No viet "`torch` tren may nay la ban CPU-only (`2.11.0+cpu`,
    #:    `cuda False`)". Cau do dung cho **trinh thong dich chay test**
    #:    (`…\Programs\Python\Python313`) va SAI cho **venv cua worker**
    #:    (`C:\LTTPlatform\venv`, `torch 2.11.0+cu128`, `cuda True`) — noi
    #:    demucs that su chay. Phep nhac o `test_406` hoi cung nham venv, nen no
    #:    xanh suot trong khi may DA co card.
    #:
    #: ⭐ **Do that 23/09 (lan `toc-do-gpu`)**, tren phim khach that 106,8 s,
    #:    chay bang DUNG venv worker, khoa `cpu_nhieu`, may ranh:
    #:
    #:      demucs htdemucs  GPU  42,2 s  · VRAM dinh +1.083 MiB · RSS 1.781 MB
    #:      demucs htdemucs  CPU  72,0 s  · VRAM dinh +3 MiB     · RSS 1.909 MB
    #:
    #:    Stem GPU va CPU tuong duong: vocals 59,0 dB tin/lech, drums 54,4 dB,
    #:    other 36,6 dB, bass 28,7 dB (tuong quan >= 0,9993); ban nen ra
    #:    (drums+bass+other) **trung khit** — ca hai −17,1 LUFS, dinh 1,3 dBFS.
    #:    Bang day du: `docs/auto_scan_video_final/L_TOC_DO_GPU.md`.
    gpu_vram_mb={
        # ✅ DO THAT pha 13 (03/09): dinh 1.673 MiB, khong doi theo do dai.
        #    Do lai 23/09 tren venv worker: dinh +1.083 MiB — khop.
        "asv_gpu.audio_prepare": 2200,
        # ✅ DO THAT 23/09 (lan `toc-do-gpu`) — truoc do la 6.000, mot con so
        #    MUON cua `autosubvideo.transcribe` va no **khai THIEU**:
        #      WhisperX sidecar (duong san pham)          dinh +6.334 MiB
        #      faster-whisper large-v3 fp16 (duong lui)   dinh +5.221 MiB
        #    WhisperX nap HAI model (ASR + can chinh) nen no moi la dinh that.
        #    Khai = dinh cao nhat + ~20%.
        "asv_gpu.transcribe": 7600,
        # ✅ DO THAT 23/09 (asv-final, lan `giong`), tung bo do mot tien
        #    trinh con, chay LAN LUOT tren RTX 5060 Ti dang phuc vu khach:
        #      ASR faster-whisper large-v3 fp16, beam 5   dinh +4.265 MiB
        #      SQUIM_OBJECTIVE (lo 4 cua so)              dinh +2.256 MiB
        #    Card ve dung muc nen sau moi tien trinh con (do: 1.859 MiB
        #    truoc va sau). Khai = dinh cao nhat + ~20%.
        "asv_gpu.qc_do_luong": 5200,
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
