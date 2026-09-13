"""App `video_assembly` — clip thô + nhạc → một video hoàn chỉnh.

Migrate từ `bot_dungvideo`. Hợp đồng đóng băng ở
`docs/migration/workflow_apps/23_APP_BOUNDARIES.md` và `24_NODE_CONTRACTS.md`.

## App nặng nhất trong bốn, và bản khai phải nói đúng điều đó

Bốn model thật trong **một** job: `whisper` · `YOLO` · `CLIP` · `Demucs`. Bot
legacy tự quản bằng `gpu_arbiter.py` (1.520 dòng) + `gpu_claims.py`; ở đây việc
ấy thuộc `admission_resource` + `admission_slots` của nền tảng.

🔴 **`admission_slots` phải khai, và khai `0` là không khai.** Ngân sách `-n` của
bộ test **không đếm tiến trình cháu**: ngày 03/09 đo được **12 tiến trình
`demucs`, mỗi cái 460–984% CPU** trên một máy 10 lõi, và máy sập. Một suất
đồng thời là con số đúng cho tới khi có phép đo nói khác.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry, ToolSpec


def _gia(params: dict) -> int:
    """Giá tạm cho V1 — App chưa mở cho khách nên nó chưa chạm sổ của ai.

    ⚠️ Phải đo lại theo **thời lượng video ra** trước khi mở cổng: đây là job
       đắt nhất trong bốn App, và một giá phẳng ở đây sẽ hoặc lỗ nặng ở video
       dài, hoặc chặn oan video ngắn.
    """
    return 1


MANIFEST = AppManifest(
    slug="video_assembly",
    display_name=N_('Dựng video từ clip'),
    route_prefix="/video-assembly",
    summary=N_('Từ một thư mục clip thô và một thư mục nhạc, chọn clip khớp '
               'lời, ghép, tách nhạc nền, trộn tiếng và cháy phụ đề thành một '
               'video hoàn chỉnh.'),
    icon="🎞️",
    accent="#BE123C",
    group="Workflow",

    nav=(NavEntry(label=N_('Dựng video'), path="/video-assembly",
                  nav_key="video_assembly"),),

    job_types=("video_assembly.run",),
    requires=("gpu", "ffmpeg"),
    # Whisper + CLIP + YOLO + Demucs co the nap chong nhau trong mot luot
    # dung. 8000 la muc khai o `ToolSpec.resource`; con so CHUA DO THAT
    # (ghi trong `docs/migration/workflow_apps/`), nen day la uoc tren.
    gpu_vram_mb={"video_assembly.run": 8000},
    cho_tai_nguyen_s={"video_assembly.run": 30},
    credit_cost=_gia,

    enabled=True,
    public=False,
    surface="customer",
    lifecycle="development",
    capabilities=("AI Video",),

    tools=(ToolSpec(
        name="video_assembly.run",
        job_type="video_assembly.run",
        description=N_('Dựng một video hoàn chỉnh từ clip thô và nhạc.'),
        params_schema={
            "clips": {"type": "video[]", "required": True},
            "music": {"type": "audio", "required": False},
            "cau_hinh": {"type": "json", "required": False},
            # `sequential` la gia tri DANG CHAY tren production, khong phai mac
            # dinh trong ma legacy (`semantic`). Xem `08_CAU_HINH_THAT...` §1.
            "che_do_khop": {"type": "enum", "values": ["sequential", "semantic"],
                            "default": "sequential"},
            "bat_demucs": {"type": "bool", "default": True},
            "bat_phu_de": {"type": "bool", "default": True},
        },
        returns={"video": "video"},

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
        idempotency={"key_fields": ("clips", "music", "cau_hinh",
                                    "che_do_khop")},
        # ⚠️ `vram_min_mb` la UOC TINH CHUA DO: bon model trong mot job. Phai do
        #    that roi sua lai — mot con so doan o day se hoac chan oan mot may
        #    du VRAM, hoac cho qua mot may khong du roi hong giua giai doan 7.
        resource={"class": "gpu", "vram_min_mb": 8000, "slots": 1,
                  "est_duration_s": 900},
        admission_resource="gpu_video",
        admission_slots=1,

        api_exposed=False,
    ),),
)
