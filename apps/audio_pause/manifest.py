"""App `audio_pause` — chèn khoảng lặng theo mốc văn bản, migrate từ `bot_pause`.

Hợp đồng đóng băng: `docs/migration/workflow_apps/23_APP_BOUNDARIES.md` và
`24_NODE_CONTRACTS.md`. Bốn cổng (`public`/`lifecycle`/`api_exposed`) đóng ở V1
là chủ ý — mở từng cái **sau** khi parity đóng.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry, ToolSpec


def _gia(params: dict) -> int:
    """Giá tạm cho V1. App chưa mở cho khách nên con số này chưa chạm sổ của ai;
    phải đo lại theo thời lượng audio trước khi mở cổng."""
    return 1


MANIFEST = AppManifest(
    slug="audio_pause",
    display_name=N_('Chèn khoảng lặng theo lời'),
    route_prefix="/audio-pause",
    summary=N_('Chèn khoảng lặng vào bản thu tại đúng những câu bạn chỉ định, '
               'cắt ở chỗ im thật chứ không cắt giữa từ, và dịch lại mốc thời '
               'gian của bản ghi lời.'),
    icon="⏸️",
    accent="#7C3AED",
    group="Workflow",

    nav=(NavEntry(label=N_('Chèn khoảng lặng'), path="/audio-pause",
                  nav_key="audio_pause"),),

    job_types=("audio_pause.run",),
    requires=("gpu",),
    credit_cost=_gia,

    enabled=True,
    public=False,
    surface="customer",
    lifecycle="development",
    capabilities=("audio",),

    tools=(ToolSpec(
        name="audio_pause.run",
        job_type="audio_pause.run",
        description=N_('Chèn khoảng lặng vào một bản thu tại các mốc văn bản.'),
        params_schema={
            "audio": {"type": "audio", "required": True},
            "pause_plan": {"type": "json", "required": True},
            # ⛔ `enum`, khong phai `string` tu do: ho so STT cua App nay KHAC
            #    NHAU theo ngon ngu (beam_size 5 voi `vi`, 1 voi `en`). Mot ngon
            #    ngu ngoai danh sach se phai doan mot ho so — va mot lan doan o
            #    day van ra ket qua hop le, chi la khac di.
            "language": {"type": "enum", "values": ["vi", "en"], "default": "vi"},
            "min_pause_ms": {"type": "int", "min": 1, "max": 60000, "default": 50},
            "max_pause_ms": {"type": "int", "min": 1, "max": 60000,
                             "default": 15000},
            "min_gap_s": {"type": "number", "min": 0.0, "max": 30.0,
                          "default": 0.8},
            "nguong_khop": {"type": "number", "min": 0.1, "max": 1.0,
                            "default": 0.65},
        },
        # HAI dau ra, va ca hai deu P0: transcript da dich moc la thu buoc sau
        # tieu thu. Tra ve mot minh tep am thanh la lam dut mach.
        returns={"audio": "audio", "transcript": "json"},

        side_effect="none",
        # `language` NAM TRONG khoa o day — khac `transcript.run`. Ly do that:
        # no chon HO SO STT, nen doi no la doi ket qua phien am, tuc doi vi tri
        # cat. Hai lan chay cung audio + cung ke hoach nhung khac ngon ngu la
        # HAI viec khac nhau.
        idempotency={"key_fields": ("audio", "pause_plan", "language")},
        resource={"class": "gpu", "vram_min_mb": 5000, "slots": 1,
                  "est_duration_s": 180},
        admission_resource="gpu_stt",
        admission_slots=1,

        api_exposed=False,
    ),),
)
