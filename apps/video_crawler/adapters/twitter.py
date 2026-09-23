"""Adapter Twitter/X qua yt-dlp (spec §11, §18, §21) — chỉ chế độ "link" (một tweet).

Máy móc yt-dlp chung (hook, nhịp tim, huỷ, lọc, tìm tệp) ở `_ytdlp.py`; đây chỉ là cấu hình Twitter/X.
yt-dlp được nạp lúc cần — module này import được khi chưa cài yt-dlp.

Sự thật donor (`D:\\Viral\\resources\\app-src`, snapshot `368f8be`, ký hiệu theo audit) — nền `tw`:
`docs/migrations/video_crawler/PLATFORM_MATRIX.md` dòng `tw`: **ẩn** trên UI, search ❌, link ✅
(backend), kênh (user) ✅ (backend), "Theo bộ" ❌, xem trước ❌; cookie `auth_token`/`ct0` bị BẮT
(`NEN_CAN_COOKIE`, `Y:89`); bộ tải yt-dlp; khoá dedup = `id` yt-dlp; bằng chứng `H:242`, `Y:89`,
`Y:2280-2285`, `W:17847`. Donor CHỈ `impersonate=chrome` cho `fb`/`bili`/`bilitv`
(`tai_ytdlp.py:2126-2135`) — KHÔNG cho `tw` ⇒ `impersonate=False` ở đây.

Chế độ hỗ trợ = GIAO (donor có) ∩ (yt-dlp 2026.03.17 có extractor thật cho đường đó):
- `link` — GIỮ. Donor có (backend, ma trận cột "link" ✅). yt-dlp có `TwitterIE`
  (`yt_dlp/extractor/twitter.py:268-270`, `IE_NAME="twitter"`), `_VALID_URL` khớp
  `.../status/<id_so>`, `i/web/status/<id_so>` và `i/status/<id_so>` (nhánh `[^/]+/status` với
  `[^/]+` = `"i"`; `_BASE_REGEX` dòng 38 chấp `(?:twitter|x)\\.com`, đã kiểm `x.com` khớp).
- `kenh` (user timeline) — BỎ. Donor có (ma trận cột "channel" ✅, backend), nhưng yt-dlp 2026.03.17
  chỉ đăng ký đúng 6 extractor Twitter (`yt_dlp/extractor/_extractors.py:2234-2240`):
  `TwitterAmplifyIE, TwitterBroadcastIE, TwitterCardIE, TwitterIE, TwitterShortenerIE, TwitterSpacesIE`
  — không có extractor liệt kê timeline người dùng ⇒ giao rỗng ⇒ không hỗ trợ ở lớp yt-dlp.
- `tu_khoa` (search) — BỎ. Donor không có (ma trận cột search = ❌).
- `bo` (collection) — BỎ. Donor không có (ma trận cột "Theo bộ" = ❌).

`allowed_extractors` chỉ gồm `"twitter"` (IE_KEY `Twitter`) — tweet video/GIF/amplify chuẩn được
`TwitterIE._real_extract` trích TRỰC TIẾP trong lớp này (`extractor/twitter.py:1268-1346`; nhánh
`amplify` gọi `_extract_formats_from_vmap_url` ngay tại chỗ, KHÔNG qua `TwitterAmplifyIE` — lớp đó chỉ
khớp domain riêng `amp.twimg.com/v/<uuid>`, ngoài phạm vi "link" tweet của lớp này). Loại
`twitter:card`/`twitter:broadcast`/`twitter:spaces`: nội dung không phải video-tweet chuẩn (card
nhúng/live/audio Space) donor không cào ở nền `tw`. Loại `twitter:shortener`: chỉ resolve `t.co`,
không tự nó là video. Loại `twitter:amplify`: ngoài phạm vi "link" (xem trên).

Anti-bot / đăng nhập (S6, NGOÀI PHẠM VI làn này — spec §11 "check_session/login thêm khi có nền cần
login (YAGNI)"): guest token ẩn danh dùng được cho tweet công khai thường, nhưng KHÔNG ổn định — cộng
đồng yt-dlp/yt-dlp báo "Bad guest token" lặp lại (issue #3796, #5768, #5548) — và tweet nhạy cảm/NSFW
đòi đăng nhập (issue #11770 "NSFW tweet requires authentication", #14115
"NsfwViewerHasNoStatedAge", #12291 "TweetResultByRestId need login"). Khớp donor bắt cookie
`auth_token`/`ct0` (`Y:89`). Adapter này chạy ẩn danh (không tự nhét cookie — spec §21: không nhận
`cookiefile` từ người dùng); tweet riêng tư/nhạy cảm sẽ lỗi và được `loi.py` phân loại (không sửa ở
tệp này).

id = id trạng thái (tweet id, chuỗi chữ số — donor và yt-dlp đều dùng làm khoá dedup, `Y:2280-2285`).
URL chuẩn dựng lại `https://x.com/i/status/<id>` — khớp `TwitterIE._VALID_URL` (đã kiểm bằng
`re.fullmatch` trong test).
"""
from __future__ import annotations

import re
from typing import Any

from apps.video_crawler.adapters._ytdlp import YtdlpAdapter

__all__ = ["EXTRACTOR_CHO_PHEP", "TwitterAdapter"]

#: IE_NAME cho phép (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929). Chỉ tweet
#: video chuẩn — không generic, không card/broadcast/spaces/shortener/amplify (xem docstring module).
EXTRACTOR_CHO_PHEP = ("twitter",)

_ID = re.compile(r"[0-9]+")


class TwitterAdapter(YtdlpAdapter):
    nen_tang = "twitter"
    allowed_extractors = EXTRACTOR_CHO_PHEP
    extractor_args = {}
    ie_key_video = ("Twitter",)
    impersonate = False

    def url_video(self, id: str) -> str:
        return f"https://x.com/i/status/{id}"

    def _sang_item(self, e: dict):
        """TwitterIE: `id` = id MEDIA, `display_id` = id TWEET (smoke thật 22/09). URL tải cần id tweet."""
        tweet = str(e.get("display_id") or "")
        if _ID.fullmatch(tweet):
            e = {**e, "id": tweet}
        return super()._sang_item(e)

    def id_hop_le(self, id: Any) -> bool:
        return isinstance(id, str) and _ID.fullmatch(id) is not None

    def url_kham_pha(self, che_do: str, dau_vao: str, n: int) -> str:
        if che_do != "link":
            raise NotImplementedError(f"nen twitter chi ho tro che_do 'link', nhan '{che_do}'")
        return dau_vao
