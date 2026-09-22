"""Adapter Douyin qua yt-dlp (spec §11, §18, §21) — CHỈ chế độ `link`.

Máy móc yt-dlp chung (hook, nhịp tim, huỷ, lọc, tìm tệp) ở `_ytdlp.py`; đây chỉ là cấu hình Douyin.
yt-dlp được nạp lúc cần — module này import được khi chưa cài yt-dlp.

Bằng chứng (KHÔNG đọc/copy MediaCrawler — giấy phép NON-COMMERCIAL):
- Donor `docs/migrations/video_crawler/PLATFORM_MATRIX.md:19` (dòng `dy`): search/link/kênh/bộ đều
  đi qua MediaCrawler; link tự chuẩn hoá `modal_id`/`vid`/`note` ⇒ `douyin.com/video/<id>`; đăng nhập
  QR, cookie `sessionid`/`sessionid_ss`/`sid_tt`; `DOUYIN_NEED_LOGIN` (2483) khi search; dedup
  `aweme_id`.
- `docs/migrations/video_crawler/AUDIT_VIRAL_CAO_NGAY.md` §7 (`W:4408-4436`): `modal_id`/`vid`/
  `/note/<id>` ⇒ `douyin.com/video/<id>`, khử trùng giữ thứ tự.
- yt-dlp 2026.03.17 đã cài, `site-packages/yt_dlp/extractor/tiktok.py`:
  - `class DouyinIE(TikTokBaseIE)` (:1351): `_VALID_URL = r'https?://(?:www\\.)?douyin\\.com/video/
    (?P<id>[0-9]+)'` (:1352); `IE_NAME`/`ie_key()` == `"Douyin"` (mặc định từ tên lớp).
  - `_TESTS` (:1353-1471): 5 mẫu, id đều 19 chữ số ⇒ `id_hop_le` chốt `\\d{19}` (chặt hơn `[0-9]+`
    của `_VALID_URL`, theo dữ liệu thật quan sát được — không có mẫu id khác độ dài trong yt-dlp).
  - `_real_extract` (:1475-1488): gọi `https://www.douyin.com/aweme/v1/web/aweme/detail/` bằng
    `_download_json` thường (KHÔNG `impersonate=True` — khác bilibili.tv/facebook, `Y:2126-2135`);
    JSON rỗng ⇒ `raise ExtractorError('Fresh cookies (not necessarily logged in) are needed', ...)`.
    Không `_configuration_arg` nào ⇒ `extractor_args = {}`.
  - yt-dlp chỉ có MỘT extractor Douyin (một video) — không search/user/channel:
    `yt-dlp/yt-dlp#2120` "Add DouyinUserIE" (vẫn mở, 2026-09-22); cookie "tươi" hỏng theo thời gian:
    `yt-dlp/yt-dlp#16867` "[Douyin] Fresh cookies issue with valid cookies on nightly".

Chế độ hỗ trợ = GIAO của (donor có: search/link/kênh/bộ) ∩ (yt-dlp có extractor thật): chỉ `link`.
search/kênh/bộ đòi ký request + phân trang riêng của Douyin (donor dùng MediaCrawler, NON-COMMERCIAL,
không thể tự dùng lại) ⇒ cần viết MỘT client Douyin riêng — việc lớn, để điều phối lên kế hoạch riêng.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from platform_core.i18n import _ as _t

from apps.video_crawler.adapters._ytdlp import YtdlpAdapter

__all__ = ["DouyinAdapter", "chuan_hoa_link_douyin", "tuy_chon"]

#: IE_NAME (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929). Không generic.
EXTRACTOR_CHO_PHEP = ("douyin",)

_ID = re.compile(r"[0-9]{19}")

# Ba dạng link chia sẻ Douyin donor tự chuẩn hoá về `/video/<id>` (AUDIT §7, `W:4408-4436`):
# query `modal_id=`, query `vid=`, và đường dẫn `/note/<id>`. Link đã chuẩn (`/video/<id>`) đi qua
# thẳng. Dạng rút gọn `v.douyin.com` (redirect) yt-dlp KHÔNG có extractor cho nó ⇒ không tự resolve
# ở đây (đọc mạng); giữ nguyên để `kham_pha`/`tai` tự từ chối.
_RE_CANONICAL = re.compile(r"douyin\.com/video/(?P<id>[0-9]{19})")
_RE_MODAL_ID = re.compile(r"[?&]modal_id=(?P<id>[0-9]{19})")
_RE_VID = re.compile(r"[?&]vid=(?P<id>[0-9]{19})")
_RE_NOTE = re.compile(r"douyin\.com/note/(?P<id>[0-9]{19})")


def chuan_hoa_link_douyin(s: str) -> str:
    """`modal_id=`/`vid=`/`/note/<id>` ⇒ `https://www.douyin.com/video/<id>` (AUDIT §7, `W:4408-4436`).
    Không khớp dạng nào (kể cả link rút gọn `v.douyin.com`) ⇒ giữ nguyên."""
    s = (s or "").strip()
    for rgx in (_RE_CANONICAL, _RE_MODAL_ID, _RE_VID, _RE_NOTE):
        m = rgx.search(s)
        if m:
            return f"https://www.douyin.com/video/{m['id']}"
    return s


def tuy_chon(thu_muc: Path | None = None, *, progress_hooks: list | None = None,
             postprocessor_hooks: list | None = None) -> dict[str, Any]:
    """Dựng tuỳ chọn yt-dlp (thuần). `thu_muc` có ⇒ tuỳ chọn tải một mục vào đó."""
    return DouyinAdapter.tuy_chon_goc(thu_muc, progress_hooks=progress_hooks,
                                      postprocessor_hooks=postprocessor_hooks)


class DouyinAdapter(YtdlpAdapter):
    nen_tang = "douyin"
    allowed_extractors = EXTRACTOR_CHO_PHEP                # spec §21
    extractor_args = {}                                     # DouyinIE không có _configuration_arg
    ie_key_video = ("Douyin",)
    impersonate = False                                     # _real_extract không dùng impersonate=True

    def url_video(self, id: str) -> str:
        return f"https://www.douyin.com/video/{id}"

    def id_hop_le(self, id: Any) -> bool:
        return isinstance(id, str) and _ID.fullmatch(id) is not None

    def url_kham_pha(self, che_do: str, dau_vao: str, n: int) -> str:
        if che_do != "link":
            raise NotImplementedError(
                _t("Douyin chưa hỗ trợ chế độ {che_do!r}: cần client Douyin riêng (ký request, phân "
                   "trang) — donor dựa vào MediaCrawler (NON-COMMERCIAL), không thể tự dùng lại.")
                .format(che_do=che_do)
            )
        return chuan_hoa_link_douyin(dau_vao)
