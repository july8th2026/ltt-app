"""Adapter YouTube qua yt-dlp (spec §11, §18, §21).

Port từ donor `D:\\Viral\\resources\\app-src\\tai_ytdlp.py` (Y). Cố ý KHÔNG chép của donor:
`ignoreerrors=True` (nuốt huỷ, Y:2023), `nocheckcertificate` (Y:2024), cookie (Y:2042-2047),
`remote_components` (Y:2066), `download_archive` (Y:2038) và `outtmpl` theo người dùng.
Máy móc yt-dlp chung (hook, nhịp tim, huỷ, lọc, tìm tệp) ở `_ytdlp.py`; đây chỉ là cấu hình YouTube.
yt-dlp được nạp lúc cần — module này import được khi chưa cài yt-dlp.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from apps.video_crawler.adapters._ytdlp import CHUOI_FORMAT, YtdlpAdapter

__all__ = ["CHUOI_FORMAT", "EXTRACTOR_CHO_PHEP", "YoutubeAdapter", "chuan_hoa_kenh_youtube", "tuy_chon"]

# Các tab hợp lệ của trang kênh YouTube (URL kết thúc bằng tab nào thì giữ nguyên) — Y:228.
_YT_TABS = ("videos", "shorts", "streams", "live", "featured", "playlists", "community", "posts")

#: IE_NAME (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929). Không generic,
#: không extractor cần đăng nhập (history/subscriptions/watchlater...), không web.archive.
EXTRACTOR_CHO_PHEP = (
    "youtube", "youtube:tab", "youtube:playlist", "youtube:search", "youtubeytbe",
    "youtube:clip", "youtube:truncated_id", "youtube:truncated_url",
)

_ID = re.compile(r"[A-Za-z0-9_-]{11}")


def chuan_hoa_kenh_youtube(s):
    """Kênh YouTube -> URL tab '/videos' (port nguyên Y:231-252).
    Giữ nguyên link 1 video/short hoặc tab đã chỉ định."""
    s = (s or "").strip()
    if not s:
        return s
    low = s.lower()
    if "watch?v=" in low or "youtu.be/" in low or re.search(r"/shorts/[\w-]+", low):
        return s
    if not low.startswith("http") and "/" not in s:
        h = s if s.startswith("@") else "@" + s
        return f"https://www.youtube.com/{h}/videos"
    if not low.startswith("http"):
        s = "https://" + s
    base_url = s.split("?")[0].split("#")[0].rstrip("/")
    if base_url.rsplit("/", 1)[-1].lower() in _YT_TABS:
        return base_url
    return base_url + "/videos"


def tuy_chon(thu_muc: Path | None = None, *, progress_hooks: list | None = None,
             postprocessor_hooks: list | None = None) -> dict[str, Any]:
    """Dựng tuỳ chọn yt-dlp (thuần). `thu_muc` có ⇒ tuỳ chọn tải một mục vào đó."""
    return YoutubeAdapter.tuy_chon_goc(thu_muc, progress_hooks=progress_hooks,
                                       postprocessor_hooks=postprocessor_hooks)


class YoutubeAdapter(YtdlpAdapter):
    nen_tang = "youtube"
    allowed_extractors = EXTRACTOR_CHO_PHEP                                   # spec §21
    extractor_args = {"youtube": {"player_client": ["web_embedded", "default"]}}  # Y:2081-2083
    ie_key_video = ("Youtube",)
    #: Giải "n challenge"/chữ ký bằng node (máy có sẵn v24) thay vì deno mặc định (N5). Script giải lấy từ gói
    #: `yt-dlp-ejs` (cùng major.minor với bản vendor của yt-dlp, 2026.03.17 ⇒ 0.8.x); thiếu gói ⇒ yt-dlp chỉ cảnh báo
    #: "n challenge solving failed" và bớt format, không vỡ. KHÔNG `remote_components` (tải mã JS lúc chạy).
    js_runtimes = {"node": {}}

    def url_video(self, id: str) -> str:
        return f"https://www.youtube.com/watch?v={id}"

    def id_hop_le(self, id: Any) -> bool:
        return isinstance(id, str) and _ID.fullmatch(id) is not None

    def url_kham_pha(self, che_do: str, dau_vao: str, n: int) -> str:
        if che_do == "tu_khoa":
            return f"ytsearch{n}:{dau_vao}"            # Y:2169
        if che_do == "kenh":
            return chuan_hoa_kenh_youtube(dau_vao)
        return dau_vao                                 # bo: URL playlist · link: một video
