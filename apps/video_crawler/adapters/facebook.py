"""Adapter Facebook qua yt-dlp (spec §11, §18, §21) — CHỈ chế độ `link` (một video/reel).

Nguồn characterization donor (`D:\\Viral\\resources\\app-src\\tai_ytdlp.py`, ký hiệu Y) + ma trận nền
tảng (`docs/migrations/video_crawler/PLATFORM_MATRIX.md` dòng `fb`):
- Link 1 video/reel tải ẨN DANH được qua yt-dlp, nhưng PHẢI `impersonate=chrome` tường minh — không thì
  `[facebook] Cannot parse data` (donor đã đo THẬT, không impersonate → lỗi; impersonate=chrome → hết lỗi
  + 13 format có 720p; trích yt-dlp issue #15161 "impersonation needed", `Y:2126-2135`; cùng lớp
  bilibili.tv `Y:2126-2135`, `Y:1655-1661`).
- Liệt kê Page/kênh CẦN đăng nhập + trình duyệt cuộn (`_fb_liet_ke_kenh`/`_fb_scroll_links`, `Y:1155-1320`;
  ép đăng nhập ở tầng UI, `H:9878`) — yt-dlp KHÔNG có extractor liệt kê Page ⇒ chế độ `kenh` KHÔNG hỗ
  trợ ở lát này (yt-dlp không có phần GIAO cho đường này; Playwright ngoài phạm vi module này).
- Dán link Page vào ô "Theo link" ⇒ `Unsupported URL` (`chuan_hoa_kenh_facebook` từ chối input không
  phải link 1 video/bài, `Y:1477-1489`; PLATFORM_MATRIX dòng `fb` cột Anti-bot: "Unsupported URL nếu dán
  link Page vào ô link").
- Donor không có chế độ `tu_khoa`/`bo` cho Facebook (PLATFORM_MATRIX dòng `fb`: search ❌, collection ❌).

Nguồn yt-dlp 2026.03.17 (`site-packages/yt_dlp/extractor/facebook.py`):
- `FacebookIE` (`:33-66`, `IE_NAME='facebook'`) — `_VALID_URL` nhận `permalink.php|video/video.php|
  photo.php|video.php|video/embed|story.php|watch(?:/live)?/?` với `v|video_id|story_fbid=`, hoặc
  `<page>/videos/<id>`, `<page>/posts/<id>`, `groups/<g>/(permalink|posts)/<id>`; id là
  `pfbid[A-Za-z0-9]+|\\d+`. Test `watch/?v=647537299265662` (`:349-350`, KHÔNG `skip`) xác nhận URL
  `watch/?v=<id>` hợp lệ ẨN DANH cho id SỐ; ngược lại phần lớn test dùng id `pfbid...`/`posts`/`groups`
  bị đánh dấu `'skip': 'Requires logging in'` (`:99, :130, :216, :230, :246, :359`, …) ⇒ id số là dạng
  DUY NHẤT chắc chạy ẨN DANH. `id_hop_le` ở đây vì vậy CHỈ nhận SỐ (loại `pfbid...`), hẹp hơn `_VALID_URL`
  gốc (gốc còn nhận cả bài viết thường cần đăng nhập).
- `FacebookReelIE` (`:958-984`, `IE_NAME='facebook:reel'`) — `_VALID_URL=.../reel/(?P<id>\\d+)`.
  `_real_extract` (`:982-984`) tự `url_result(f'https://m.facebook.com/watch/?v={video_id}&_rdr',
  FacebookIE, video_id)` — CHÍNH yt-dlp coi `watch/?v=<id>` là dạng chính tắc của cả reel, xác nhận thêm
  cho lựa chọn `url_video` dưới. Donor `_fb_scroll_links` (`Y:1201-1207`) cũng coi `reel/<id>` là một
  dạng link video hợp lệ (dù ở ngữ cảnh liệt kê Page) ⇒ nằm trong GIAO donor ∩ yt-dlp cho chế độ `link`.
- `FacebookPluginsVideoIE`/`FacebookRedirectURLIE` (`:886-955`, tồn tại thật — `gen_extractor_classes()`
  liệt `IE_NAME` = `FacebookPluginsVideo`/`FacebookRedirectURL`) KHÔNG vào `allowed_extractors`: donor
  không nhắc dạng embed `/plugins/video.php` hay link rút gọn `/flx/warn` nào (ngoài GIAO donor); và
  `FacebookRedirectURLIE._VALID_URL` (`:922`) không có nhóm `id` — không dựng lại được `url_video(id)` từ
  đó, và có thể trỏ sang site KHÁC hẳn Facebook (test của nó trỏ sang YouTube, `:924`).
- Không có extractor yt-dlp nào cho `fb.watch/<code>` hay `share/v/<code>` (không khớp `_VALID_URL` của
  bất kỳ lớp facebook nào ở trên, đã tra toàn văn `facebook.py`) ⇒ hai dạng rút gọn này KHÔNG dựng lại
  được thành id qua yt-dlp trong lát này (không phải generic — cấm theo spec §21); khách phải dán link
  đầy đủ dạng `.../videos/<id>`, `watch/?v=<id>` hoặc `reel/<id>`.
yt-dlp được nạp lúc cần — module này import được khi chưa cài yt-dlp.
"""
from __future__ import annotations

import re
from typing import Any

from platform_core.i18n import _ as _t

from apps.video_crawler.adapters._ytdlp import YtdlpAdapter

__all__ = ["EXTRACTOR_CHO_PHEP", "FacebookAdapter"]

#: IE_NAME cho phép (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929). Chỉ 2
#: extractor có id SỐ dựng lại được `url_video` và nằm trong GIAO donor ∩ yt-dlp cho chế độ `link`
#: (xem docstring module) — không `facebookpluginsvideo`/`facebookredirecturl`.
EXTRACTOR_CHO_PHEP = ("facebook", "facebook:reel")

#: id Facebook (video/reel) — CHỈ SỐ, tối thiểu 5 ký tự để loại vụn số ngắn vô nghĩa. Loại `pfbid...`
#: (bài viết — phần lớn cần đăng nhập, xem docstring module).
_ID = re.compile(r"\d{5,}")


class FacebookAdapter(YtdlpAdapter):
    nen_tang = "facebook"
    allowed_extractors = EXTRACTOR_CHO_PHEP                    # spec §21
    ie_key_video = ("Facebook", "FacebookReel")
    impersonate = True                                         # Y:2126-2135 — không thì "Cannot parse data"

    def url_video(self, id: str) -> str:
        return f"https://www.facebook.com/watch/?v={id}"

    def id_hop_le(self, id: Any) -> bool:
        return isinstance(id, str) and _ID.fullmatch(id) is not None

    def url_kham_pha(self, che_do: str, dau_vao: str, n: int) -> str:
        if che_do != "link":
            raise NotImplementedError(
                _t("Facebook: chế độ '{che_do}' chưa hỗ trợ — yt-dlp không liệt kê được Page/kênh Facebook "
                   "(cần trình duyệt đã đăng nhập, donor `_fb_liet_ke_kenh`); chỉ 'Theo link' dùng ẩn danh được.")
                .format(che_do=che_do)
            )
        return dau_vao         # link: một video/reel, đưa thẳng cho yt-dlp (FacebookIE/FacebookReelIE tự khớp)
