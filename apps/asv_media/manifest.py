"""Executor AN cua Auto Scan Video — lan `ffmpeg`.

Khach khong bao gio nhin thay app nay: `surface="runtime"`, `public=False`,
`catalog_parent="auto_scan_video"`. No ton tai vi mot ly do ky thuat duy nhat.

## Vi sao phai tach app thay vi khai `requires=("ffmpeg","gpu")` o mot cho

`platform_core/jobs.py:158-164` loc quyen nhat job theo **APP**:

    eligible = [app for app in discover()
                if set(app.manifest.requires).issubset(capabilities)]

Khong co dinh tuyen theo `job_type`. Nen mot app khai ca hai nang luc chi duoc
nhat boi mot lan co **du ca hai**; tren doi hinh chia lan
(`LTT_WORKER_POOLS="api:8, ffmpeg:2, gpu:2"`) job cua no vo hinh voi moi worker
va nam `queued` **mai mai, khong loi nao bao**.

`tests/test_400_asv_bat_bien_thi_hanh.py::test_app_gop_ca_hai_nang_luc_bi_ca_HAI_lan_le_tu_choi`
tai hien dung canh do bang mot app that.

## Vi sao RENDER nam o day chu khong o lan GPU

`MVP_CONTRACT.md` D-ASV-03: MVP **sao chep** luong video chu khong ma hoa lai,
vi khong giai doan nao doi mot diem anh. Nen RENDER la mot phep mux
(`-c:v copy -c:a aac`), khong phai mot phep transcode — no can ffmpeg, khong can
card. Do la ly do giai doan **dai nhat** cua san pham thoi tranh GPU voi cac ho
khac tren may.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest

#: Giai doan gia cua pha 05 khong ton gi. Gia THAT thuoc pha 21.
#:
#: ⛔ Tra 0 la CO Y va no phai o lai ke ca khi co engine that: chi `asv_run` giu
#:    tien (ADR-001 D4). Mot job giai doan tu khai gia khac 0 se lam khach bi
#:    tinh tien hai lan cho cung mot viec — mot lan o run, mot lan o day.
def _gia(params: dict) -> int:
    return 0


MANIFEST = AppManifest(
    slug="asv_media",
    display_name=N_('Auto Scan Video — xử lý media'),
    route_prefix="/asv-media",
    summary=N_('Executor nội bộ của Auto Scan Video. Không phải sản phẩm riêng.'),
    icon="🎞️",

    catalog_parent="auto_scan_video",
    surface="runtime",
    public=False,
    enabled=False,
    lifecycle="internal",

    job_types=(
        "asv_media.media_prepare",
        "asv_media.content_process",
        "asv_media.voice_synthesis",
        "asv_media.timing_align",
        "asv_media.compose",
        "asv_media.render",
        "asv_media.qc",
    ),
    requires=("ffmpeg",),
    credit_cost=_gia,

    #: Tran thoi gian theo tung giai doan. Nhat job mo coi chi bat worker
    #: **chet**; mot job **treo** ma van dap nhip se giu suat vo han.
    max_runtime_s={
        "asv_media.media_prepare": 900,
        "asv_media.content_process": 1800,
        "asv_media.voice_synthesis": 3600,
        "asv_media.timing_align": 1800,
        "asv_media.compose": 300,
        "asv_media.render": 3600,
        "asv_media.qc": 600,
    },
    notes="Pha 05: handler GIA. Khong goi engine that.",
)
