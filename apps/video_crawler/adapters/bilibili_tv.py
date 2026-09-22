"""Adapter Bilibili quốc tế (bilibili.tv) qua yt-dlp (spec §11, §18, §21).

Donor CHỈ hỗ trợ chế độ "Theo link" cho nền này — không tìm-theo-từ-khoá, không trang cá nhân,
không "Theo bộ" (registry `_EP_CHE_DO["bilibili_tv"] = "detail"`, `apps/video_crawler/nen_tang.py:33`;
`docs/migrations/video_crawler/PLATFORM_MATRIX.md` dòng `bilitv`: search ❌, channel ❌,
collection ❌, link ✅ duy nhất). Donor CLI chặn tường minh mọi chế độ khác cho `bilitv`
(`Y:1655-1661`: "bilibili.tv chỉ hỗ trợ 'Theo link' ... Trang này không có tìm-theo-từ-khoá
và không có trang cá nhân"). Không `impersonate` ⇒ `www.bilibili.tv` RESET kết nối giữa chừng
(đo 0/9 lượt lấy metadata); có `impersonate=chrome` ⇒ 6/6 trên 2 URL công khai (`Y:2126-2135`).

Nguồn characterization yt-dlp 2026.03.17 (site-packages `yt_dlp/extractor/bilibili.py`):
- `BiliIntlIE` (:2192-2193) — `_VALID_URL` khớp HAI dạng: `/play/<season_id>/<ep_id>` (một tập
  trong một season) hoặc `/video/<aid>` (video độc lập). `IE_NAME` tự suy từ tên lớp = "BiliIntl"
  (không khai tường minh trong nguồn).
- `_real_extract` (:2430) — `video_id = ep_id or aid`; season_id CHỈ dùng nội bộ để gọi API,
  KHÔNG có trong info-dict trả lại (`_extract_video_metadata` chỉ merge title/description/json-ld).
  Hệ quả: một link dạng `/play/<season>/<ep>` trích ra `id = ep_id`, nhưng KHÔNG đủ dữ liệu để
  `url_video(id)` dựng lại đúng URL gốc (thiếu season_id) — vi phạm hợp đồng adapter (registry
  `nen_tang.py:66-67`: "Có mẫu URL ⇒ URL khách gửi bị BỎ khi tải: một id kèm URL playlist/kênh
  từng tải cả playlist với giá 1 credit, BLOCKER"). Do đó adapter này CHỈ nhận dạng `/video/<aid>`
  (id độc lập, tự đủ để dựng URL); `url_kham_pha` chặn dạng `/play/<season>/<ep>` NGAY TỪ ĐẦU
  (trước khi dựng YoutubeDL) để không âm thầm cào/tải nhầm sang endpoint `aid=<ep_id>` — đúng
  loại lỗi "hỏng ÊM" mà donor đã cảnh báo ở `Y:1655-1661`.
  ⚠ GHI CHO ĐIỀU PHỐI: mở rộng sang dạng `/play/<season>/<ep>` cần `CrawlItem`/`_ytdlp.py::_sang_item`
  mang thêm season_id — ngoài phạm vi hai tệp được giao (BRIEF "Bạn được sửa ĐÚNG hai tệp"); KHÔNG
  sửa `_ytdlp.py` ở đây.
- `BiliIntlSeriesIE` (:2463, IE_NAME "biliIntl:series") — trích danh sách tập của một season
  (`/play/<id>` không kèm ep, hoặc `/media/<id>`) = "Theo bộ", donor không hỗ trợ (❌) ⇒ KHÔNG đưa
  vào `allowed_extractors` (spec §21: chỉ extractor của chế độ đang hỗ trợ, không đưa season/kênh).

Máy móc yt-dlp chung (hook, nhịp tim, huỷ, lọc, tìm tệp) ở `_ytdlp.py`; đây chỉ là cấu hình bilibili.tv.
yt-dlp được nạp lúc cần — module này import được khi chưa cài yt-dlp.
"""
from __future__ import annotations

import re
from typing import Any

from apps.video_crawler.adapters._ytdlp import YtdlpAdapter
from apps.video_crawler.adapters.base import LoiCao

__all__ = ["EXTRACTOR_CHO_PHEP", "BilibiliTvAdapter"]

#: IE_NAME (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929). Không generic,
#: không `biliIntl:series` (season/"Theo bộ" — donor không hỗ trợ cho bilitv).
EXTRACTOR_CHO_PHEP = ("BiliIntl",)

#: id video độc lập (`aid`) — dạng số nguyên, khớp nhóm `aid` trong `BiliIntlIE._VALID_URL`.
_ID = re.compile(r"[0-9]+")


class BilibiliTvAdapter(YtdlpAdapter):
    nen_tang = "bilibili_tv"
    allowed_extractors = EXTRACTOR_CHO_PHEP                       # spec §21
    extractor_args = {}
    ie_key_video = ("BiliIntl",)
    impersonate = True                                            # Y:2126-2135 — thiếu thì bị reset kết nối

    def url_video(self, id: str) -> str:
        return f"https://www.bilibili.tv/video/{id}"

    def id_hop_le(self, id: Any) -> bool:
        return isinstance(id, str) and _ID.fullmatch(id) is not None

    def url_kham_pha(self, che_do: str, dau_vao: str, n: int) -> str:
        """link: video độc lập — nền chỉ có chế độ này (`Y:1655-1661`).

        Chặn TRƯỚC khi dựng YoutubeDL: chỉ nhận dạng `/video/<aid>` thật của `BiliIntlIE`
        (nhóm `aid` khớp). Dạng `/play/<season>/<ep>` (một tập) bị từ chối vì `id` trích ra
        (ep_id) không tự đủ để `url_video(id)` dựng lại đúng URL gốc — xem docstring module.
        """
        from yt_dlp.extractor.bilibili import BiliIntlIE

        vao = (dau_vao or "").strip()
        m = BiliIntlIE._VALID_URL and re.match(BiliIntlIE._VALID_URL, vao)
        if not m or not m.group("aid"):
            raise LoiCao("url_khong_ho_tro",
                         "Chỉ hỗ trợ dán link video độc lập bilibili.tv (không hỗ trợ link tập phim/season).",
                         tam_thoi=False)
        return vao
