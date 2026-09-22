"""Adapter Bilibili (bilibili.com) qua yt-dlp (spec §11, §18, §21).

Sự thật donor (`docs/migrations/video_crawler/PLATFORM_MATRIX.md` dòng `bili`, `AUDIT_VIRAL_CAO_NGAY.md`
§6-§8): search, link (`b23.tv` ⇒ redirect ⇒ BV), channel (`space.bilibili.com/<mid>`) và collection
(API `ugc_season`) đều có ở donor qua MediaCrawler (giấy phép NON-COMMERCIAL — module này KHÔNG đọc/chép
mã MediaCrawler, chỉ dùng sự thật đã tổng hợp trong hai tài liệu trên). Mã lỗi `-101` ẩn danh vẫn cào
được (không phải lỗi đăng nhập). Dedup donor: `aid` + `bvid`.

Giao (donor có) ∩ (yt-dlp 2026.03.17 đã cài có extractor THẬT — kiểm trực tiếp
`site-packages/yt_dlp/extractor/bilibili.py`, không đọc bằng suy đoán):
- `link`    → `BiliBiliIE`               IE_NAME `BiliBili`               `_VALID_URL` dòng 307.
- `tu_khoa` → `BiliBiliSearchIE`         IE_NAME `BiliBiliSearch`         `_SEARCH_KEY='bilisearch'` dòng 1817-1820.
- `kenh`    → `BilibiliSpaceVideoIE`     IE_NAME `BilibiliSpaceVideo`     `_VALID_URL` dòng 1270-1271.
- `bo`      → `BilibiliCollectionListIE` IE_NAME `BilibiliCollectionList` dòng 1423-1427 (API
              `seasons_archives_list` — đúng tính năng "collection chính thức `ugc_season`" donor nêu).

KHÔNG dùng (không khớp GIAO hoặc không phải tính năng donor có):
- `BilibiliSeriesListIE` (series — khác `ugc_season`), `BilibiliCategoryIE` (donor không có "danh mục"),
  `BiliIntl*`/`BiliLive*` (nền `bilitv`/livestream — PLATFORM_MATRIX dòng khác, không phải `bili`).
- `b23.tv` (donor: rút gọn ⇒ redirect ⇒ BV): yt-dlp 2026.03.17 KHÔNG có extractor riêng cho domain này
  (đã `grep b23` trong `extractor/`, không thấy tệp/khớp nào ngoài các trùng chữ ngẫu nhiên ở nền khác);
  chỉ `GenericIE` theo được redirect, mà spec §21 cấm `allowed_extractors` chứa generic. ⇒ `link` mode
  của adapter này chỉ nhận URL `bilibili.com/video/...` đã chuẩn hoá — b23.tv phải được giải ở lớp trên
  (app resolve redirect) nếu cần, KHÔNG phải việc của adapter (brief: không sửa `_ytdlp.py`/`base.py`).

id hai dạng cùng hợp lệ trên `bilibili.com` (`BiliBiliIE._VALID_URL` nhận cả prefix `av`/`BV`, dòng 307):
- `bvid` = `BV[0-9A-Za-z]{10}` — `kenh`/`bo` trả trực tiếp dạng này (`BilibiliSpaceVideoIE`/
  `BilibiliCollectionListIE` gọi `url_result(f'https://www.bilibili.com/video/{bvid}', BiliBiliIE, bvid)`,
  dòng 1367 và 1410).
- `aid` (số) — `BiliBiliSearchIE._search_results` (dòng 1869-1870) CHỈ trả
  `url_result(video['arcurl'], 'BiliBili', str(video['aid']))`; với `extract_flat="in_playlist"` (bắt
  buộc ở `_ytdlp.py.kham_pha`, không sửa được), `YoutubeDL.py` dòng 1888-1909 KHÔNG resolve tiếp nên
  `entry['id']` khi khám phá bằng `tu_khoa` là aid số, không phải bvid. Không nhận cả hai dạng thì
  `tu_khoa` luôn rỗng (mọi mục bị `id_hop_le` loại) — vì vậy `id_hop_le`/`url_video` xử lý cả hai,
  và `tai()` (kiểm `item.url == url_video(item.id)` ở `_ytdlp.py`) vẫn đúng với dạng aid.

Không impersonate: PLATFORM_MATRIX dòng `bili` không đòi (`impersonate=chrome` chỉ ở dòng `bilitv`/
facebook). Không cookie: donor `-101` ẩn danh vẫn cào được; risk control 412/-352 đã có WBI ký sẵn
trong extractor (`_sign_wbi`, ví dụ dòng 1332-1334, 1337-1339) — yt-dlp issue #12013 "[BiliBili]
Circumvent 412 Error (Request is blocked by server) & Possible fix for no-account downloads" và #10243
"[BiliBili] Migration to new API with WBI signature" (cả hai đã đóng, đã vào bản 2026.03.17) xác nhận
đường WBI ẩn danh hoạt động — không cần đăng nhập cho các mode đã chọn.
yt-dlp được nạp lúc cần — module này import được khi chưa cài yt-dlp.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from platform_core.i18n import _ as _t

from apps.video_crawler.adapters._ytdlp import YtdlpAdapter, _TrangThai, loi_theo_ma
from apps.video_crawler.adapters.base import BaoTienDo, KenhItem, YeuCauTimKenh, tao_kenh

__all__ = ["API_TIM_KENH", "EXTRACTOR_CHO_PHEP", "TRANG_CHU", "UA", "BilibiliAdapter",
           "chuan_hoa_kenh_bilibili", "kenh_tu_user_bili", "tuy_chon", "url_kenh_bilibili"]

#: IE_NAME (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929). Không generic.
EXTRACTOR_CHO_PHEP = ("bilibili", "bilibilisearch", "bilibilispacevideo", "bilibilicollectionlist")

#: bvid thật: luôn "BV" hoa + 10 ký tự chữ/số (mẫu donor + `_TESTS` của `BiliBiliIE`, ví dụ BV13x41117TL).
_BVID = re.compile(r"BV[0-9A-Za-z]{10}")
#: aid — id số trần mà `BiliBiliSearchIE` trả ở dạng flat (xem docstring module).
_AID = re.compile(r"[0-9]{1,12}")
_MID = re.compile(r"\d{1,15}")

#: Tìm KÊNH theo tên (smoke thật 23/09): `search_type=bili_user` trên điểm cuối tìm kiếm KHÔNG ký WBI
#: vẫn trả `code: 0` + `data.result[]` (`mid`/`uname`/`fans`/`videos`/`upic`/`usign`). Bản `wbi/…` chưa ký
#: `w_rid` chỉ trả `{"v_voucher": …}`, nên dùng bản không WBI. ⚠ Không có cookie `buvid` ẩn danh ⇒ HTTP 412
#: (đúng dòng `bili` của PLATFORM_MATRIX) ⇒ phải GET trang chủ một lượt để xin cookie trước.
API_TIM_KENH = "https://api.bilibili.com/x/web-interface/search/type"
TRANG_CHU = "https://www.bilibili.com/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/140.0.0.0 Safari/537.36")
#: HTTP của risk control Bilibili (412 đo thật 22/09 + 23/09); phần còn lại coi như lỗi chung.
_HTTP_CHAN = frozenset({403, 412, 429, 461})


def url_kenh_bilibili(mid: str) -> str:
    """Trang space của một UP. `chuan_hoa_kenh_bilibili` thêm `/video` khi khách bấm cào."""
    return f"https://space.bilibili.com/{mid}"


def kenh_tu_user_bili(u: Any) -> KenhItem | None:
    """Một mục `data.result[]` của `search_type=bili_user` ⇒ KenhItem; mục lạ ⇒ None (không ném)."""
    if not isinstance(u, dict) or u.get("type") != "bili_user":
        return None
    mid = u.get("mid")
    mid = str(mid) if isinstance(mid, (int, str)) and not isinstance(mid, bool) else ""
    return tao_kenh("bilibili", mid, url_kenh_bilibili(mid), ten=u.get("uname"),
                    anh_dai_dien=u.get("upic"), so_theo_doi=u.get("fans"), so_video=u.get("videos"),
                    mo_ta=u.get("usign"))


def chuan_hoa_kenh_bilibili(s: str) -> str:
    """Kênh Bilibili -> URL `/video` của trang space. mid trần hoặc URL gốc space đều ra cùng dạng."""
    s = (s or "").strip()
    if not s:
        return s
    if _MID.fullmatch(s):
        return f"https://space.bilibili.com/{s}/video"
    low = s.lower()
    if not low.startswith("http"):
        s = "https://" + s
    base = s.split("?")[0].split("#")[0].rstrip("/")
    if re.fullmatch(r"https?://space\.bilibili\.com/\d+", base):
        return base + "/video"
    return base


def tuy_chon(thu_muc: Path | None = None, *, progress_hooks: list | None = None,
             postprocessor_hooks: list | None = None) -> dict[str, Any]:
    """Dựng tuỳ chọn yt-dlp (thuần). `thu_muc` có ⇒ tuỳ chọn tải một mục vào đó."""
    return BilibiliAdapter.tuy_chon_goc(thu_muc, progress_hooks=progress_hooks,
                                        postprocessor_hooks=postprocessor_hooks)


class BilibiliAdapter(YtdlpAdapter):
    nen_tang = "bilibili"
    allowed_extractors = EXTRACTOR_CHO_PHEP                          # spec §21
    extractor_args = {}
    ie_key_video = ("BiliBili",)
    impersonate = False                                              # PLATFORM_MATRIX dòng `bili`

    def url_video(self, id: Any) -> str:
        s = str(id)
        if _BVID.fullmatch(s):
            return f"https://www.bilibili.com/video/{s}"
        return f"https://www.bilibili.com/video/av{s}"

    def id_hop_le(self, id: Any) -> bool:
        if not isinstance(id, str) or not id:
            return False
        return _BVID.fullmatch(id) is not None or _AID.fullmatch(id) is not None

    # ------------------------------------------------------------ tìm kênh theo TÊN (ẩn danh)
    def tim_kenh(self, yeu_cau: YeuCauTimKenh, *, bao_tien_do: BaoTienDo) -> list[KenhItem]:
        """Không đi qua extractor yt-dlp (không có IE nào tìm UP) — chỉ mượn ngăn xếp mạng + cookiejar
        của `YoutubeDL.urlopen`, như `douyin_web`/`xhs_web` (tầng app không tự dựng HTTP)."""
        from yt_dlp.networking import Request
        from yt_dlp.networking.exceptions import HTTPError, TransportError

        n = max(1, int(yeu_cau.so_luong))
        opts = self._them_chung(self.tuy_chon_goc(), _TrangThai(bao_tien_do), ghi_tu_choi=False)
        q = urlencode({"search_type": "bili_user", "keyword": yeu_cau.tu_khoa.strip(), "page": 1})
        bao_tien_do(0, _t("đang tìm kênh"))
        with self._tao(opts) as ydl:
            try:
                ydl.urlopen(Request(TRANG_CHU, headers={"User-Agent": UA}))     # xin cookie buvid ẩn danh
                than = ydl.urlopen(Request(f"{API_TIM_KENH}?{q}", headers={
                    "User-Agent": UA, "Referer": TRANG_CHU,
                    "Accept": "application/json, text/plain, */*"})).read()
            except HTTPError as e:
                raise loi_theo_ma("nen_chan" if e.status in _HTTP_CHAN else "loi_khac") from None
            except TransportError:
                raise loi_theo_ma("mang") from None
        try:
            d = json.loads(than)
        except ValueError:
            raise loi_theo_ma("nen_chan") from None          # trang xác minh/captcha thay vì JSON
        if not isinstance(d, dict) or d.get("code") != 0:
            raise loi_theo_ma("nen_chan")
        data = d.get("data")
        ra: list[KenhItem] = []
        for u in ((data if isinstance(data, dict) else {}).get("result") or []):
            if len(ra) >= n:
                break
            k = kenh_tu_user_bili(u)
            if k is not None and all(k.id != x.id for x in ra):
                ra.append(k)
        bao_tien_do(100, _t("tìm thấy {n} kênh").format(n=len(ra)))
        return ra

    def url_kham_pha(self, che_do: str, dau_vao: str, n: int) -> str:
        if che_do == "tu_khoa":
            return f"bilisearch{n}:{dau_vao}"
        if che_do == "kenh":
            return chuan_hoa_kenh_bilibili(dau_vao)
        return dau_vao                                 # bo: URL bộ (ugc_season) · link: một video
