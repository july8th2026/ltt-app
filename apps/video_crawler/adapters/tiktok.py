"""Adapter TikTok qua yt-dlp (spec §11, §18, §21).

Sự thật donor (`D:\\Viral\\resources\\app-src\\tai_ytdlp.py`, ký hiệu Y) + yt-dlp 2026.03.17 đã cài
(`yt_dlp/extractor/tiktok.py`, ký hiệu `TT`):
- Chế độ hỗ trợ = GIAO của (donor có) ∩ (yt-dlp có extractor thật cho đường đó):
  - `link` (một video/short link): donor tiền kiểm ảnh/video rồi fallback trình duyệt khi yt-dlp chỉ thấy
    audio (Y:2387-2490); adapter này CHỈ đi đường yt-dlp (`TikTokIE` + `TikTokVMIE` cho short link
    vm/vt.tiktok.com/`.../t/`) — không fallback trình duyệt (ngoài phạm vi lớp con). `TT:698,1492`.
  - `kenh` (channel): donor `chuan_hoa_kenh_tiktok` Y:382-393 ⇒ `TikTokUserIE` (`IE_NAME='tiktok:user'`,
    `_VALID_URL` `TT:999-1000`).
  - `bo` (collection): donor hỗ trợ link collection **hoặc** 1 tập có `dramaID` (API phim bộ riêng, không
    qua yt-dlp) — phần `dramaID` NGOÀI giao (không extractor yt-dlp nào đọc được), nên chế độ này ở đây
    CHỈ nhận link collection thật ⇒ `TikTokCollectionIE` (`IE_NAME='tiktok:collection'`,
    `_VALID_URL` `TT:1294-1295`).
  - `tu_khoa` (từ khoá): donor không có "search" TikTok thật — chỉ có trang HASHTAG `/tag/<kw>`, và trang
    đó **cần cookie đăng nhập** (Y:1541-1544); tải trực tiếp từ search cũng KHÔNG được hỗ trợ (Y:2181-2184).
    yt-dlp có `TikTokTagIE` (`IE_NAME='tiktok:tag'`, `_VALID_URL` `TT:1266-1267`) cho đúng URL đó ⇒ giao
    tồn tại, nhưng đăng nhập là điều kiện cần — đăng ký nền `can_dang_nhap=True` cho chế độ này (điều phối
    nối cookie phiên sau, S6/spec §16).
- KHÔNG chép của donor: cookie khi TẢI TikTok — donor đo thật là **cookie đăng nhập làm TikTok trả 403**
  khi tải, vì xung đột với cookie-challenge yt-dlp tự sinh (Y:1734-1741) — adapter này (và `_ytdlp.py`
  dùng chung) không có đường nào nhét cookie vào `tai()`, đúng ý donor "không tự nhét cookie khi tải".
- KHÔNG cần thêm `http_headers={'Referer': ...}` thủ công cho lỗi "Unexpected response from webpage
  request" donor từng vá (Y:2053-2054, vá cho yt-dlp 2026.7.4/2026.8.16): bản 2026.03.17 đã tự đặt
  `http_headers={'Referer': webpage_url}` ngay trong info của định dạng (`TT:660`, `_parse_aweme_video_web`)
  — vá ở tầng extractor, không phải tầng gọi.
- KHÔNG `impersonate`: donor chỉ dùng `impersonate=chrome` cho bilibili.tv/facebook, không cho TikTok
  (`Y:2126-2135`); bản thân extractor TikTok đã tự impersonate ở lệnh gọi trang nội bộ
  (`_extract_web_data_and_status` gọi `impersonate=True`, `TT:279`) — không phải cấu hình `YoutubeDL` toàn cục.
- Ảnh slideshow (bài `/photo/`) không có video — dùng CHUNG id với `/video/` (Y:2387-2408) nhưng không có
  định dạng video; lớp cha `_ytdlp.py`/`loi.py` đã có mã `chi_la_anh` cho "No video formats found" khi tải,
  đây KHÔNG lọc được ở bước khám phá (extract_flat không có `formats`) — rủi ro ghi trong báo cáo lane.

Máy móc yt-dlp chung (hook, nhịp tim, huỷ, lọc, tìm tệp) ở `_ytdlp.py`; đây chỉ là cấu hình TikTok.
yt-dlp được nạp lúc cần — module này import được khi chưa cài yt-dlp.
"""
from __future__ import annotations

import re
import urllib.parse
from typing import Any

from apps.video_crawler.adapters._ytdlp import YtdlpAdapter

__all__ = ["EXTRACTOR_CHO_PHEP", "TikTokAdapter", "chuan_hoa_kenh_tiktok", "url_hashtag_tiktok"]

#: IE_NAME (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929). Không generic.
#: `tiktok` = video lẻ (`TikTokIE`, IE_NAME mặc định = tên lớp bỏ "IE"); `tiktok:user` = kênh;
#: `tiktok:collection` = bộ; `vm.tiktok` = short link vm/vt.tiktok.com (resolve ra video thật);
#: `tiktok:tag` = trang hashtag (chế độ từ khoá, cần cookie đăng nhập — điều phối nối sau).
EXTRACTOR_CHO_PHEP = ("tiktok", "tiktok:user", "tiktok:collection", "vm.tiktok", "tiktok:tag")

#: id video TikTok: chuỗi số (snowflake, thường 19 chữ số) — khớp đúng `\d+` trong `_VALID_URL` của
#: `TikTokIE` (`TT:698`). Không dùng độ dài cố định vì `_VALID_URL` không ràng buộc độ dài.
_ID = re.compile(r"\d+")

#: Trích @handle từ link kênh TikTok — port `chuan_hoa_kenh_tiktok` (Y:382-393), bỏ phần "cố gắng nhận
#: `tiktokuser:<secUid>`" của donor (comment donor nói bản cũ yt-dlp từ chối dạng đó; bản 2026.03.17 thật
#: ra vẫn chấp nhận tiền tố này trong `TikTokUserIE._VALID_URL`, nhưng donor tự chọn KHÔNG dùng nó — chỉ
#: dùng URL `@username` đã kiểm liệt kê được — nên adapter theo đúng lựa chọn đã kiểm chứng của donor).
_HANDLE = re.compile(r"tiktok\.com/@([\w.\-]+)", re.I)


def chuan_hoa_kenh_tiktok(s: Any) -> str:
    """@user / link kênh TikTok -> URL kênh chuẩn 'https://www.tiktok.com/@<user>'. '' nếu không rõ."""
    s = (s or "").strip()
    if not s:
        return ""
    m = _HANDLE.search(s)
    handle = (m.group(1) if m else s).lstrip("@").strip()
    if not handle:
        return ""
    return "https://www.tiktok.com/@" + handle


def url_hashtag_tiktok(kw: str) -> str:
    """Từ khoá -> URL trang hashtag TikTok (donor: search TikTok = trang `/tag/<kw>`, Y:1541-1544).
    Bỏ dấu '#' và khoảng trắng như donor (Y:1735: `kw.lstrip('#').replace(' ', '').strip()`)."""
    slug = (kw or "").lstrip("#").replace(" ", "").strip()
    return "https://www.tiktok.com/tag/" + urllib.parse.quote(slug)


class TikTokAdapter(YtdlpAdapter):
    nen_tang = "tiktok"
    allowed_extractors = EXTRACTOR_CHO_PHEP                    # spec §21
    extractor_args: dict = {}
    ie_key_video = ("TikTok",)
    impersonate = False                                        # Y:2126-2135 — TikTok không impersonate

    def url_video(self, id: str) -> str:
        # `TikTokBaseIE._create_url(user_id, video_id)` (TT:105-107): placeholder "_" khi không biết
        # handle — URL vẫn khớp `TikTokIE._VALID_URL` vì `@(?P<user_id>...)?` cho phép user_id bất kỳ.
        return f"https://www.tiktok.com/@_/video/{id}"

    def id_hop_le(self, id: Any) -> bool:
        return isinstance(id, str) and _ID.fullmatch(id) is not None

    def url_kham_pha(self, che_do: str, dau_vao: str, n: int) -> str:
        if che_do == "tu_khoa":
            return url_hashtag_tiktok(dau_vao)                 # TikTokTagIE — cần cookie (đăng ký nền)
        if che_do == "kenh":
            return chuan_hoa_kenh_tiktok(dau_vao)               # TikTokUserIE
        return dau_vao          # bo: URL collection (TikTokCollectionIE) · link: 1 video/short link
