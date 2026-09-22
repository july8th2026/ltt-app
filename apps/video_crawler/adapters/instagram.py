"""Adapter Instagram qua yt-dlp (spec §11, §18, §21).

Chỉ chế độ `link` (bài lẻ `/p/`, `/reel(s)/`, `/tv/`) — GIAO của donor ∩ yt-dlp 2026.03.17 đã cài:

- Donor `docs/migrations/video_crawler/PLATFORM_MATRIX.md` dòng `ig`: `tu_khoa` ❌, `link` ✅ (tự nhận
  `_ig_bai_le`), `kenh` ✅ nhưng đi qua TRÌNH DUYỆT `_ig_liet_ke_kenh` (`Y:1017-1150`) — không qua
  yt-dlp, `bo` ❌. Đăng nhập bằng cookie `sessionid`/`ds_user_id` xuất sang `cookies.txt`
  (`Y:1490-1528`); bài công khai tải được ẩn danh, không có cookie thì bài riêng tư/giới hạn báo lỗi
  bình thường qua `loi.phan_loai` (không đặc cách ở đây).
- yt-dlp `yt_dlp/extractor/instagram.py`:
  - `InstagramIE` (IE_NAME `Instagram`, `:224` `_VALID_URL`) khớp `/p/`, `/tv/`, `/reel(s)/` — dùng
    cho `link`. Ký tự shortcode thật theo `_ENCODING_CHARS` (`:26`); bài riêng tư có id dài hơn
    (shortcode + tối đa 28 ký tự phụ, `:443-447`) nên biên trên rộng hơn 11 ký tự của shortcode
    thường.
  - `InstagramUserIE` (IE_NAME `instagram:user`, `:606-610`) có `_WORKING = False` (`:607`) — yt-dlp
    tự đánh dấu HỎNG CỨNG, không nạp được dù có cookie hay không. yt-dlp/yt-dlp#4394 (mở từ 2022,
    còn mở tới 2026-08) và #17683 (báo lại trên bản 2026.08.19: "functionality... marked as broken",
    đóng `not_planned`) xác nhận vẫn hỏng. ⇒ `kenh` KHÔNG nằm trong giao cho adapter yt-dlp này — chỉ
    cào được qua trình duyệt, ngoài phạm vi tệp này (điều phối quyết định lớp riêng nếu cần).
  - Bài chỉ có ảnh: `_extract_product_media` trả `{}` khi thiếu `video_versions`/`video_dash_manifest`
    (`:108-114`) ⇒ yt-dlp lõi tự ném `"No video formats found!"` (`YoutubeDL.raise_no_formats`) —
    khớp đúng tín hiệu donor ghi trong PLATFORM_MATRIX `ig`. `apps/video_crawler/loi.py` đã có mã
    `chi_la_anh` cho tín hiệu này (spec §19) — KHÔNG sửa `loi.py`.
  - Link chia sẻ mang query rác `?igsi=`/`?s=` — donor `chuan_hoa_user` cắt trước khi dùng
    (`Y:205-228`); áp dụng cho `url_kham_pha` ở đây.
  - Không cần `impersonate` (donor chỉ dùng cho bilibili.tv/facebook, `Y:2126-2135`).

yt-dlp được nạp lúc cần — module này import được khi chưa cài yt-dlp.
"""
from __future__ import annotations

import re
from typing import Any

from apps.video_crawler.adapters._ytdlp import YtdlpAdapter

__all__ = ["EXTRACTOR_CHO_PHEP", "InstagramAdapter", "cat_bo_query"]

#: IE_NAME cho phép (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929). Chỉ bài
#: lẻ — `instagram:user` bị `_WORKING = False` (xem docstring module), không dùng được.
EXTRACTOR_CHO_PHEP = ("instagram",)

#: Ký tự shortcode thật (`_ENCODING_CHARS`, yt_dlp/extractor/instagram.py:26); bài riêng tư có thêm
#: tối đa 28 ký tự phụ (`:443-447`) nên biên trên rộng hơn 11 ký tự của shortcode công khai thường.
_ID = re.compile(r"[A-Za-z0-9_-]{5,40}")


def cat_bo_query(s: str) -> str:
    """Cắt query + fragment khỏi link chia sẻ (`?igsi=...`, `?s=...`) — donor `chuan_hoa_user`,
    `Y:205-228`. Không đụng phần đường dẫn (`/p/<id>/`, `/reel/<id>/`...)."""
    s = (s or "").strip()
    return s.split("?")[0].split("#")[0]


class InstagramAdapter(YtdlpAdapter):
    nen_tang = "instagram"
    allowed_extractors = EXTRACTOR_CHO_PHEP
    ie_key_video = ("Instagram",)

    def url_video(self, id: str) -> str:
        return f"https://www.instagram.com/p/{id}/"

    def id_hop_le(self, id: Any) -> bool:
        return isinstance(id, str) and _ID.fullmatch(id) is not None

    def url_kham_pha(self, che_do: str, dau_vao: str, n: int) -> str:
        """Chỉ `link` được hỗ trợ (registry/UI chặn các chế độ khác trước khi gọi tới đây)."""
        return cat_bo_query(dau_vao)
