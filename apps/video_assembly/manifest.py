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
            "bat_cham_diem": {"type": "bool", "default": False},
        },
        returns={"video": "video"},

        side_effect="none",
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
