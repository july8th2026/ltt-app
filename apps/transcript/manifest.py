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

from .gia import uoc_luong_credit
from .services.he import HE, MAC_DINH


#: Giá theo phút audio (`gia.py`, chủ dự án chốt 22/09/2026). `duration_s` do
#: MÁY CHỦ đo (route web trước khi gửi; API qua `measured_from`), không phải số
#: người gọi khai. Worker đo lại và quyết toán `min(giá thật, đã giữ)` — Q84.
def _gia(params: dict) -> int:
    return uoc_luong_credit((params or {}).get("duration_s"))


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

    # Mở cho khách 22/09/2026 (chủ dự án): quy tắc đã đối soát với bot_transcript
    # (khớp tuyệt đối trên EN 98/98 đoạn), E2E trên app.lttstudios.com.
    enabled=True,
    public=True,
    surface="customer",
    lifecycle="released",
    capabilities=("audio",),

    tools=(ToolSpec(
        name="transcript.run",
        job_type="transcript.run",
        description=N_('Phiên âm một tệp âm thanh thành dòng thời gian có mốc.'),
        ten_ngan=N_('Phiên âm có mốc thời gian'),
        params_schema={
            "audio": {"type": "audio", "required": True},
            "language": {"type": "string", "required": False, "max_length": 8},
            # 1.5 = segment.min_s cua cau hinh legacy DANG CHAY (khong phai 3.0).
            "min_s": {"type": "number", "min": 0.5, "max": 30.0, "default": 1.5},
            "max_s": {"type": "number", "min": 1.0, "max": 60.0, "default": 6.0},
            "include_silence": {"type": "bool", "default": True},
            # He phien am (services/he.py) — them he = them mot muc o do.
            "he": {"type": "enum", "values": list(HE), "default": MAC_DINH},
            # Máy chủ đo từ chính tệp đã tải lên; số người gọi khai không chạm
            # vào giá (Q84, H35.10a — cùng khuôn `apps/autosubvideo`).
            "duration_s": {"type": "number", "min": 0, "measured_from": "audio"},
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
        # Mở 22/09/2026 sau đối soát quy tắc legacy + E2E (xem docstring đầu tệp).
        customer_visible=True,
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

        # ── Public API (mở 22/09/2026) ──────────────────────────────────────
        # Giá đo từ tệp (`duration_s` + `measured_from`) nên báo giá máy-gọi-máy
        # giữ được lời hứa Q84. Cổng thứ ba là `LTT_PUBLIC_API_TOOLS` trên
        # production (`setup/cong_tac_tool_api.ps1 -Tool transcript.run -Bat`).
        api_exposed=True,
        api_contract={
            "scopes": ("jobs:create",),
            "description": ("Transcribe an audio file into a timeline of "
                            "speech and silence segments with start and end "
                            "times, in Vietnamese or English. Costs 2 credits "
                            "per started minute of audio (minimum 1). The "
                            "duration is measured from the file you upload, "
                            "not from anything you send."),
            "hidden": ("duration_s",),
            "params": {
                "audio": {
                    "description": ("The audio to transcribe, given as the id "
                                    "of an upload you confirmed or of an "
                                    "artifact from an earlier job."),
                    "example": "upl_from_POST_/api/v1/uploads",
                },
                "language": {
                    "description": ("`vi` or `en`. Leave empty to detect the "
                                    "language automatically."),
                    "example": "vi",
                },
                "min_s": {
                    "description": ("Shortest speech segment you want, in "
                                    "seconds. Segments are cut at sentence "
                                    "ends and pauses."),
                    "example": 1.5,
                },
                "max_s": {
                    "description": "Longest speech segment you want, in seconds.",
                    "example": 6.0,
                },
                "include_silence": {
                    "description": ("Keep pauses as separate `silence` "
                                    "segments in the timeline."),
                    "example": True,
                },
                "he": {
                    "description": ("Transcription engine. `ltt` is the "
                                    "standard engine and the default."),
                    "example": "ltt",
                },
            },
        },
    ),),
)
