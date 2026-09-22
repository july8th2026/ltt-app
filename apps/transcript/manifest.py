"""App `transcript` — phiên âm có dòng thời gian, migrate từ `bot_transcript`.

Nền tảng **chỉ đọc tệp này**. Hợp đồng đã đóng băng ở
`docs/migration/workflow_apps/23_APP_BOUNDARIES.md` và `24_NODE_CONTRACTS.md`.

## Bốn cột đóng ở V1 là CHỦ Ý, không phải quên

`public=False` + `lifecycle="development"` giữ App khỏi catalog công khai trong
khi parity chưa đóng. `api_exposed=False` giữ nó khỏi `/api/v1` — và dù có bật
thì vẫn còn hai cổng nữa (`LTT_PUBLIC_API`, `LTT_PUBLIC_API_TOOLS`). Mở từng
cổng **sau** khi parity đóng, mỗi lần một cổng.

## `group="Workflow"` — bốn chữ, không phải một trang mới

`AppManifest.group` đã có sẵn và điều hướng đọc nó. Đó là toàn bộ cách yêu cầu
*"một khu vực tên Workflow"* được đáp ứng, không cần Hub — `26_WORKFLOW_UX.md`.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry, ToolSpec

from .services.he import HE, MAC_DINH

#: Giá tạm cho V1. App chưa mở cho khách (`public=False`), nên con số này chưa
#: chạm sổ của ai. Phải đo lại theo thời lượng audio trước khi mở cổng.
#:
#: ⚠️ Đừng biến nó thành một hằng số "đã cân nhắc": nó là một chỗ giữ chỗ, và
#:    memory *sàn làm tròn là một tầng khác với bảng giá* nói rõ chuyện gì xảy
#:    ra khi một con số tạm được coi là giá thật.
def _gia(params: dict) -> int:
    return 1


MANIFEST = AppManifest(
    slug="transcript",
    display_name=N_('Phiên âm có dòng thời gian'),
    route_prefix="/transcript",
    summary=N_('Chuyển một tệp âm thanh thành bản ghi lời có mốc thời gian, '
               'chia đoạn theo độ dài đặt trước, kèm các khoảng lặng.'),
    icon="🎧",
    accent="#0F766E",
    group="Workflow",

    nav=(NavEntry(label=N_('Phiên âm'), path="/transcript", nav_key="transcript"),),

    job_types=("transcript.run",),
    requires=("gpu",),
    # 🔴 Whisper `large-v3` float16 nap tren card: do that ~4,5 GB, khai 5000
    #    de con cho cho VAD va bo dem. Runner doc CHINH truong nay
    #    (`job_runner._vram_can` -> `manifest.vram_for`) — `ToolSpec.resource
    #    ["vram_min_mb"]` la ban khai cho NGUOI DOC, khong ai xep cho theo no.
    gpu_vram_mb={"transcript.run": 5000},
    cho_tai_nguyen_s={"transcript.run": 20},
    credit_cost=_gia,

    # Chưa mở cho khách: parity chưa đóng.
    enabled=True,
    public=False,
    surface="customer",
    lifecycle="development",
    capabilities=("audio",),

    tools=(ToolSpec(
        name="transcript.run",
        job_type="transcript.run",
        description=N_('Phiên âm một tệp âm thanh thành dòng thời gian có mốc.'),
        params_schema={
            "audio": {"type": "audio", "required": True},
            "language": {"type": "string", "required": False, "max_length": 8},
            # 1.5 = segment.min_s cua cau hinh legacy DANG CHAY (khong phai 3.0).
            "min_s": {"type": "number", "min": 0.5, "max": 30.0, "default": 1.5},
            "max_s": {"type": "number", "min": 1.0, "max": 60.0, "default": 6.0},
            "include_silence": {"type": "bool", "default": True},
            # He phien am (services/he.py) — them he = them mot muc o do.
            "he": {"type": "enum", "values": list(HE), "default": MAC_DINH},
        },
        returns={"transcript": "json"},

        # ⛔ `external` danh cho thu goi ra ngoai va khong lam lai duoc. Day
        #    chay cuc bo, ket qua tat dinh theo (audio, ho so) — nen `none`.
        # ⛔ CUA THU NHAT trong bon cua, va no dang MO khi khong nen mo.
        #
        # 🔴 Do o Phase 14: bo loc bang cong cu cua khach la
        #    `presentationAdapter.ts:65` — `tool.customer_visible!==false`, HET.
        #    Khong co bo loc `lifecycle` nao trong ca duong Agent.
        #
        #    Nen mot App khai `lifecycle="development"`, `public=False`, CHUA
        #    nghiem thu E2E, van hien trong palette cua khach va bam chay duoc.
        #    `public=False` chi giau trang web cua App; no khong giau tool.
        #
        # ⇒ Dong cua nay lai cho toi khi parity dong va nghiem thu E2E xong. Day
        #   la sua METADATA cua Tool, dung nhu Phase 14 yeu cau ("uu tien sua
        #   Tool metadata truoc planner; khong nhet luat App-specific vao Agent").
        #
        # ⚠️ `customer_visible=False` KHONG go nang luc: `discover_tools()` van
        #    thay, `runtime_noi_bo.bao_gia()` van tra duoc gia, va workflow da
        #    dung no van chay. Cung khuon `apps/chatltt` da dung.
        customer_visible=False,
        side_effect="external",
        # Cung mot audio + cung hai tran do dai => cung mot dong thoi gian.
        # `language` KHONG nam trong khoa: de trong nghia la tu do, va hai lan
        # tu do tren cung tep cho cung ket qua.
        # `he` doi model STT => ket qua khac: phai nam trong khoa.
        idempotency={"key_fields": ("audio", "min_s", "max_s", "he")},
        resource={"class": "gpu", "vram_min_mb": 5000, "slots": 1,
                  "est_duration_s": 120},
        admission_resource="gpu_stt",
        admission_slots=1,

        # Ba cong deu dong o V1 — xem docstring dau tep.
        api_exposed=False,
    ),),
)
