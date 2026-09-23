"""Adapter Weibo qua yt-dlp (spec §11, §18, §21).

Donor (`D:\\Viral`) **KHÔNG** dùng yt-dlp cho weibo: nền `wb` bị **ẩn** trên UI (CSS `H:242`), backend chỉ có
`tim_anh` (cào ẢNH) qua MediaCrawler — giấy phép NON-COMMERCIAL, **không đọc/chép** module đó
(`docs/migrations/video_crawler/PLATFORM_MATRIX.md:30`). Adapter này viết mới hoàn toàn từ đặc tả yt-dlp
2026.03.17 (`yt_dlp/extractor/weibo.py`), không port dòng nào của donor hay MediaCrawler.

Chế độ hỗ trợ = GIAO (donor có ∩ yt-dlp có extractor thật, spec §12):
- `link`: `WeiboIE` (`weibo.com/<uid>/<mblogid>`, `m.weibo.cn/status|detail/<mid>`) + `WeiboVideoIE`
  (`weibo.com/tv/show/<fid>`, `video.weibo.com/show?fid=<fid>` — chỉ redirect `url_result` sang `WeiboIE`,
  `weibo.py:284-291`).
- `kenh`: `WeiboUserIE` (`weibo.com/u/<uid>`) — **liệt kê video THẬT** (không phẳng): `_entries` (`weibo.py:345-353`)
  gọi `_parse_video_info` đầy đủ cho từng mục, `_TESTS` xác nhận `playlist_mincount` 195/61 (`weibo.py:296-313`).
- KHÔNG `tu_khoa`: yt-dlp không có `WeiboSearch` (tra `gen_extractor_classes()`, không extractor nào tên có
  "weibo" ngoài `Weibo`/`WeiboUser`/`WeiboVideo`).
- KHÔNG `bo`: donor liệt `❌` cho "Theo bộ" (`PLATFORM_MATRIX.md:30`) và yt-dlp không có extractor album/bộ sưu
  tập weibo.

Đăng nhập: donor có cookie `SUB`/`SUBP` nhưng thẻ login bị comment (`PLATFORM_MATRIX.md:30`). yt-dlp tự sinh
cookie khách khi ẩn danh (`WeiboBaseIE._update_visitor_cookies`, `weibo.py:24-54`, gọi khi redirect tới
`passport.weibo.com`) — vá 403 ẩn danh ở GitHub `yt-dlp/yt-dlp` PR #14012 "[ie/weibo] Fix extractors"
(đóng issue #13938 "weibo downloads broken - 403 forbidden", 2025-08-16). Bản 2026.03.17 đã cài có vá này ⇒
**không cần đăng nhập, không cần `impersonate`** (khác bilibili.tv/facebook, `Y:2126-2135`).

id chuẩn của adapter là **mid số** của status (trường `id`/`id_str`/`mid` sau khi trích, `weibo.py:104-105`),
KHÔNG phải mblogid chữ+số trong URL gốc. URL chuẩn dựng lại `weibo.com/0/<mid>` là chính dạng yt-dlp dùng nội
bộ để redirect từ `WeiboVideoIE` (`weibo.py:291`) và là `_TESTS` thứ 3 của `WeiboIE` ("no playback_list example",
`weibo.py:181-184`) — `WeiboIE._VALID_URL` nhận `weibo.com/\\d+/<id>` nên uid "0" hợp lệ.
yt-dlp được nạp lúc cần — module này import được khi chưa cài yt-dlp.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from apps.video_crawler.adapters._ytdlp import CHUOI_FORMAT, YtdlpAdapter

__all__ = ["CHUOI_FORMAT", "EXTRACTOR_CHO_PHEP", "WeiboAdapter", "chuan_hoa_kenh_weibo", "tuy_chon"]

#: IE_NAME thật (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929). Không generic.
EXTRACTOR_CHO_PHEP = ("weibo", "weibouser", "weibovideo")

#: mid số của status Weibo — 13-19 chữ số, không số 0 đứng đầu (mọi mẫu `_TESTS` của weibo.py là 16 chữ số;
#: nới biên vì mid tăng dần theo thời gian). Không khớp mblogid (chữ+số) hay id kênh.
_ID = re.compile(r"[1-9]\d{12,18}")


def chuan_hoa_kenh_weibo(s):
    """Kênh Weibo -> URL `weibo.com/u/<uid>`. uid trần ⇒ dựng URL; URL đã có ⇒ chỉ thêm scheme khi thiếu
    (giữ nguyên query như `?tabtype=...`: `WeiboUserIE` tự đọc query, và `_yes_playlist` luôn ưu tiên danh
    sách khi `noplaylist` không được đặt — adapter không đặt cho chế độ `kenh`)."""
    s = (s or "").strip()
    if not s:
        return s
    if s.isdigit():
        return f"https://weibo.com/u/{s}"
    if not s.lower().startswith("http"):
        s = "https://" + s
    return s


def tuy_chon(thu_muc: Path | None = None, *, progress_hooks: list | None = None,
             postprocessor_hooks: list | None = None) -> dict[str, Any]:
    """Dựng tuỳ chọn yt-dlp (thuần). `thu_muc` có ⇒ tuỳ chọn tải một mục vào đó."""
    return WeiboAdapter.tuy_chon_goc(thu_muc, progress_hooks=progress_hooks,
                                      postprocessor_hooks=postprocessor_hooks)


class WeiboAdapter(YtdlpAdapter):
    nen_tang = "weibo"
    allowed_extractors = EXTRACTOR_CHO_PHEP
    extractor_args = {}
    ie_key_video = ("Weibo",)
    impersonate = False

    def url_video(self, id: str) -> str:
        return f"https://weibo.com/0/{id}"

    def id_hop_le(self, id: Any) -> bool:
        return isinstance(id, str) and _ID.fullmatch(id) is not None

    def url_kham_pha(self, che_do: str, dau_vao: str, n: int) -> str:
        if che_do == "kenh":
            return chuan_hoa_kenh_weibo(dau_vao)
        return dau_vao                                 # link: một video (WeiboIE/WeiboVideoIE tự giải quyết)
