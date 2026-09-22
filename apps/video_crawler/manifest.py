"""App `video_crawler` — "Cào ngay": khám phá + tải video nguồn vào LTT Storage.

Di trú hành vi từ ViralCrawl (D:/Viral @ 368f8be, CHỈ THAM CHIẾU). Thiết kế + lý do từng quyết định:
`docs/superpowers/specs/2026-09-22-video-crawler-design.md`.

- `requires=("api",)`, KHÔNG `("ffmpeg",)`: production chỉ có MỘT worker `gpu+ffmpeg`, job tải sẽ xếp sau job GPU
  2 giờ (spec §8). ffmpeg vẫn có trên máy A; `requires` chỉ quyết định làn nào nhận job.
- `tai` được 7200 s: tải + ghép video dài vượt trần 1800 s của lớp api.
- Chưa mở bán (`public=False`, `lifecycle="development"`). Route còn khoá bằng cờ env (`routes.py`), vì
  `enabled=False` không chặn route hay worker (spec §26).
"""
from __future__ import annotations

from apps.video_crawler import gia
from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry

#: Trần số mục mỗi job — `/jobs/{id}/artifacts` chỉ liệt kê 20 tệp (server/routes/jobs.py:39,45).
SO_MUC_TOI_DA = 20


def _so_nguyen(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _gia(params: dict) -> int:
    """Khám phá miễn phí. Tải: giữ chỗ `gia.GIA_GIU_CHO` mỗi mục xin tải; handler quyết toán `credit_cost`
    = tổng `gia.gia_muc(thoi_luong_s thật)` của các mục ĐÃ TẢI (một nguồn giá: `apps/video_crawler/gia.py`)."""
    if isinstance(params.get("muc"), list):
        n = len(params["muc"])
    elif isinstance(params.get("nguon"), dict):
        n = _so_nguyen(params["nguon"].get("so_luong"))
    else:
        return 0
    return max(0, min(n, SO_MUC_TOI_DA)) * gia.GIA_GIU_CHO


MANIFEST = AppManifest(
    slug="video_crawler",
    display_name=N_("Cào video nguồn"),
    route_prefix="/video-crawler",
    summary=N_("Tìm và tải video nguồn (từ khoá, link, kênh, playlist) vào kho của bạn."),
    icon="🎞️",
    accent="#0F766E",
    nav=(NavEntry(N_("Cào video"), "/video-crawler", "🎞️", "video_crawler"),),
    job_types=("video_crawler.kham_pha", "video_crawler.tai"),
    requires=("api",),
    credit_cost=_gia,
    max_runtime_s={"video_crawler.tai": 7200},
    table_prefix="vc",        # bảng riêng: vc_phien (phiên đăng nhập mã hoá, tables.py)
    capabilities=("Video",),
    enabled=False,          # ẩn khỏi nav/catalog tới khi mở thử; Public API cũng bị chặn (catalog.py:229)
    public=False,
    lifecycle="development",
    notes="Release 1: YouTube. Nền cần đăng nhập ở slice 2 (spec §8, §16).",
)
