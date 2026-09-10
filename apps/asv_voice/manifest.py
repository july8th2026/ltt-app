"""Executor AN cua Auto Scan Video — lan `voice`.

Mot giai doan: doc ban dich thanh tieng, tung doan mot.

## Vi sao `requires=("voice",)` chu khong phai `("gpu",)`

`apps/ltt_voice` khai chinh xac nang luc nay, va no la mot **cai ten do app tu
dat** — `manifest.requires` khong bi rang buoc vao mot tu vung dong. May sinh
tieng chay sau loopback `127.0.0.1:8120` nhu mot dich vu NSSM rieng
(`LTTStudioVoice`), khong phai mot thu vien nap trong worker; nen "co GPU" va
"co may sinh tieng" la hai dieu kien khac nhau, va tron chung lam mot se dua job
toi mot may co card nhung khong co dich vu.

🔴 Va hau qua cua viec khai sai la **im lang**: `apps/ltt_voice/manifest.py:112`
   ghi lai rang neu production da dat `LTT_WORKER_POOLS` ma thieu lan `voice`
   thi job nam `queued` **mai mai, khong loi nao bao**. `setup/4-nghiem-thu.ps1`
   da co chot cho `ltt_voice`; chot do phai phu ca app nay truoc khi mo ban.

## Khong khai `gpu_vram_mb`

Do la co y. Tien trinh worker khong nap model nao — no goi HTTP sang sidecar.
VRAM cua may sinh tieng (do that: 641 MB dinh, CLAUDE.md) do **dich vu do** giu,
khong phai job nay. Khai o day se lam nen tang giu cho mot card cho mot viec
khong dung card.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest


def _gia(params: dict) -> int:
    """Luon 0 — chi `asv_run` giu tien (ADR-001 D4). Xem `asv_media/manifest.py`."""
    return 0


MANIFEST = AppManifest(
    slug="asv_voice",
    display_name=N_('Auto Scan Video — tạo tiếng nói'),
    route_prefix="/asv-voice",
    summary=N_('Executor nội bộ của Auto Scan Video. Không phải sản phẩm riêng.'),
    icon="🎙️",

    catalog_parent="auto_scan_video",
    surface="runtime",
    public=False,
    enabled=False,
    lifecycle="internal",

    job_types=("asv_voice.voice_synthesis",),
    requires=("voice",),
    credit_cost=_gia,

    #: Mot ban dich dai la hang tram doan, moi doan mot luot goi sidecar. Do
    #: that tren 5060 Ti: RTF 0,121 @3.000 ky tu, TTFA 398 ms (CLAUDE.md), nen
    #: phan lon thoi gian la so luot chu khong phai do dai tung luot.
    max_runtime_s={"asv_voice.voice_synthesis": 5400},

    #: May sinh tieng la mot dich vu DUY NHAT tren may nay. Cho 5 giay giua hai
    #: lan hoi, khong phai 20: mot luot doc mat ~5 giay, va bac 20 giay se lam
    #: GPU nam khong ~15 trong moi 20 — dung phep do da ghi o
    #: `platform_core/registry.py:346`.
    cho_tai_nguyen_s={"asv_voice.voice_synthesis": 5},

    notes="Goi dich vu cua `apps/ltt_voice` qua be mat da khai. Khong nap model.",
)
