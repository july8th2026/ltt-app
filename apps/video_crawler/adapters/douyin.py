"""Adapter Douyin (spec §11, §18, §21): `link` + `tai` qua yt-dlp; `tu_khoa`/`kenh` qua client web `douyin_web.py`.

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

Chế độ: `link` (yt-dlp), `tu_khoa` + `kenh` (client web ký a_bogus — port f2 Apache-2.0, xem `douyin_web.py`;
chủ dự án chấp nhận rủi ro ToS N10 ngày 22/09). `bo` (collection) chưa làm. Mục tìm được vẫn TẢI qua yt-dlp
bằng link chuẩn `douyin.com/video/<aweme_id>` với cookie khách.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from platform_core.i18n import _ as _t

from apps.video_crawler.adapters import douyin_web
from apps.video_crawler.adapters._ytdlp import YtdlpAdapter
from apps.video_crawler.adapters.base import BaoTienDo, CrawlItem, YeuCauCao

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

    def __init__(self, ydl_factory: Callable[[dict], Any] | None = None, *,
                 van_chuyen_factory: Callable[[str | None], douyin_web.VanChuyen] | None = None,
                 ky: douyin_web.KyTen | None = None, **kw: Any):
        super().__init__(ydl_factory, **kw)
        self._van_chuyen_factory = van_chuyen_factory or douyin_web.van_chuyen_ytdlp
        self._ky = ky or douyin_web.ky_a_bogus

    def url_video(self, id: str) -> str:
        return f"https://www.douyin.com/video/{id}"

    def id_hop_le(self, id: Any) -> bool:
        return isinstance(id, str) and _ID.fullmatch(id) is not None

    def url_kham_pha(self, che_do: str, dau_vao: str, n: int) -> str:
        if che_do != "link":                      # tu_khoa/kenh đi `kham_pha` riêng (client web), không qua đây
            raise NotImplementedError(_t("Douyin chưa hỗ trợ chế độ {che_do!r}.").format(che_do=che_do))
        return chuan_hoa_link_douyin(dau_vao)

    # ------------------------------------------------------------ tu_khoa / kenh (client web)
    def kham_pha(self, yeu_cau: YeuCauCao, *, bao_tien_do: BaoTienDo) -> list[CrawlItem]:
        che_do = yeu_cau.che_do
        if che_do not in ("tu_khoa", "kenh"):
            return super().kham_pha(yeu_cau, bao_tien_do=bao_tien_do)
        n = int(yeu_cau.so_luong)
        vao = yeu_cau.dau_vao.strip()
        sec_uid: str | None = None
        if che_do == "kenh":
            sec_uid = douyin_web.sec_uid_tu_link(vao)
            if sec_uid is None:                   # link rút gọn/không phải trang người dùng — không đọc mạng để giải
                raise douyin_web.loi_url_sai()
        elif not self.tep_cookie:                 # donor: tìm Douyin đòi đăng nhập (DOUYIN_NEED_LOGIN 2483)
            raise douyin_web.loi_can_dang_nhap()
        bao_tien_do(0, _t("đang tìm video"))
        web = douyin_web.DouyinWeb(self._van_chuyen_factory(self.tep_cookie),
                                   ms_token=douyin_web.doc_cookie(self.tep_cookie, "msToken"), ky=self._ky)

        def bao(pct: int) -> None:
            bao_tien_do(pct, _t("đang tìm video"))

        def nhan(m: dict) -> bool:
            return self.id_hop_le(m["id"]) and self.ly_do_tu_choi({"duration": m["thoi_luong_s"]}) is None

        tho = (web.tim_video(vao, n, bao=bao, nhan=nhan) if che_do == "tu_khoa"
               else web.video_cua_nguoi_dung(sec_uid or "", n, bao=bao, nhan=nhan))
        ra = [CrawlItem(nen_tang=self.nen_tang, url=self.url_video(m["id"]), **m) for m in tho[:n]]
        bao_tien_do(100, _t("tìm thấy {n} video").format(n=len(ra)))
        return ra
