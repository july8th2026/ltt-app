"""Adapter Kuaishou (spec §11, §18, §19, §21) — KHÔNG qua yt-dlp (yt-dlp không có extractor Kuaishou).

Chế độ: `link` (`kuaishou.com/short-video/<photoId>`), `kenh` (`kuaishou.com/profile/<userId>`), `tu_khoa`.
HTTP thật ở `kuaishou_web.py`; đây là logic thuần (test tiêm web giả).

Bằng chứng (KHÔNG đọc/chép MediaCrawler — NON-COMMERCIAL; KHÔNG đọc KS-Downloader — GPLv3;
`Johnserf-Seed/f2` không có app kuaishou — `f2/apps/` chỉ bark/douyin/tiktok/twitter/weibo):
- `markbang/wgetx-skill` (MIT, 0e864328) `skills/wgetx/scripts/kuaishou/`: trang chi tiết render SSR
  `window.__APOLLO_STATE__` chứa `VisionVideoDetailPhoto:<id>` {caption, duration (ms), coverUrl, photoUrl}
  và `VisionVideoDetailAuthor:<uid>` {name}; GET thuần, không cần đăng nhập. Tìm kiếm/kênh ở đó đi
  TRÌNH DUYỆT (Playwright chặn bắt GraphQL) — tức GraphQL gọi thẳng không ổn định khi ẩn danh.
- `sonderlau/KuaiShouVideoDownload` (MIT, 8f1941a0) `utils/GraphQLWrapper.py`: POST `/graphql`
  `visionProfilePhotoList(pcursor, userId, page="profile")` ⇒ `{result, pcursor, feeds[{author, photo}]}`;
  `API/get_all_videos.json`: `result=1` là thành công, `photoUrl` = mp4 trực tiếp trên `v*.kwaicdn.com`,
  ảnh bìa `*.kwimgs.com`, `duration` là mili-giây (chuỗi). Hết trang: `pcursor == "no_more"`.
- `visionSearchPhoto(keyword, pcursor, searchSessionId, page="search")`: tên operation theo brief điều phối;
  truy vấn GraphQL ở đây TỰ VIẾT, chỉ chọn trường cần (chưa kiểm trên mạng thật — xem smoke).
- Donor (chỉ đọc) `web_app.py:1105-1112`: request tự động chưa đăng nhập bị CAPTCHA
  `captcha.zt.kuaishou.com/...ANTICRAWL_DEFAULT` ⇒ `kenh`/`tu_khoa` đòi phiên (chặn trước khi gọi mạng);
  `W:17788-17790` cookie phiên `passToken`/`kuaishou.server.web_st`.

Tải: URL mp4 KHÔNG lấy từ CrawlItem (khách/kết quả gửi) — `tai()` dựng lại URL trang từ id, đọc `photoUrl`
MỚI (URL CDN có hạn), kiểm allowlist `CDN_VIDEO` + chặn IP nội bộ (`an_toan_url.kiem`) cho URL đầu và
mọi đích chuyển hướng.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from platform_core.i18n import _ as _t

from apps.video_crawler import an_toan_url
from apps.video_crawler.adapters import kuaishou_web
from apps.video_crawler.adapters._ytdlp import (
    _TU_CHOI,
    MAX_FILESIZE_MAC_DINH,
    THOI_LUONG_TOI_DA_MAC_DINH,
    ten_sach,
)
from apps.video_crawler.adapters.base import BaoTienDo, CrawlItem, LoiCao, TepTai, YeuCauCao
from apps.video_crawler.loi import phan_loai

__all__ = ["CDN_VIDEO", "KuaishouAdapter", "doc_apollo"]

#: CDN video/ảnh Kuaishou (mẫu thật: `v1/v2.kwaicdn.com`, `tx2/ali2.a.kwimgs.com` — sonderlau
#: `API/get_all_videos.json`; `*.yximgs.com` là miền ảnh/video khác của Kuaishou).
CDN_VIDEO = ("kwaicdn.com", "kwimgs.com", "yximgs.com")

_GOC = "https://www.kuaishou.com"
#: photoId/userId quan sát được: `3xruk6a5qw3n6xq`, `3x984ye63jkct29` (15 ký tự chữ-số). Nới vừa đủ,
#: vẫn là tập con của `base.ID_AN_TOAN` (khoá storage).
_ID = re.compile(r"[0-9A-Za-z_-]{6,64}")
_URL_VIDEO = re.compile(r"(?:https?://)?(?:www\.)?kuaishou\.com/short-video/([0-9A-Za-z_-]{6,64})(?:[?#].*)?")
_URL_KENH = re.compile(r"(?:https?://)?(?:www\.)?kuaishou\.com/profile/([0-9A-Za-z_-]{6,64})(?:[?#].*)?")
_DAU_APOLLO = "window.__APOLLO_STATE__"
_DAU_CAPTCHA = ("captcha.zt.kuaishou.com", "anticrawl", "captcha")
_DAU_DANG_NHAP = ("login", "未登录", "请登录")
_HET = "no_more"
_TRANG_TOI_DA = 10

_TRUONG_FEED = "feeds { author { id name } photo { id duration caption coverUrl photoUrl } }"
_Q_KENH = (
    "query visionProfilePhotoList($pcursor: String, $userId: String, $page: String, $webPageArea: String) {"
    " visionProfilePhotoList(pcursor: $pcursor, userId: $userId, page: $page, webPageArea: $webPageArea) {"
    f" result pcursor {_TRUONG_FEED} }} }}"
)
_Q_TIM = (
    "query visionSearchPhoto($keyword: String, $pcursor: String, $searchSessionId: String, $page: String,"
    " $webPageArea: String) { visionSearchPhoto(keyword: $keyword, pcursor: $pcursor,"
    " searchSessionId: $searchSessionId, page: $page, webPageArea: $webPageArea) {"
    f" result pcursor searchSessionId {_TRUONG_FEED} }} }}"
)


def doc_apollo(html: str) -> dict | None:
    """`window.__APOLLO_STATE__={...}` trong trang SSR ⇒ dict; không có/không đọc được ⇒ None."""
    i = (html or "").find(_DAU_APOLLO)
    if i < 0:
        return None
    j = html.find("{", i)
    if j < 0:
        return None
    try:
        return json.JSONDecoder().raw_decode(html, j)[0]
    except ValueError:
        pass
    # Apollo đôi khi tuần tự hoá `undefined` (JS) — không phải JSON. Cắt tới cuối khối script rồi thay.
    k = html.find("</script>", j)
    doan = html[j:k if k > 0 else len(html)]
    doan = re.sub(r"([:\[,]\s*)undefined(?=\s*[,}\]])", r"\1null", doan)
    try:
        return json.JSONDecoder().raw_decode(doan)[0]
    except ValueError:
        return None


def _loi(tin_hieu: str) -> LoiCao:
    """Tái dùng bảng phân loại chung (`loi.py`) — cùng mã, cùng câu báo khách."""
    return phan_loai(tin_hieu)


def _nen_chan() -> LoiCao:
    return _loi("http error 412")


def _can_dang_nhap() -> LoiCao:
    return _loi("login required")


def _khong_ho_tro() -> LoiCao:
    return _loi("unsupported url")


def _ms_sang_s(v: Any) -> int | None:
    try:
        ms = float(v)
    except (TypeError, ValueError):
        return None
    return int(ms // 1000) if ms > 0 else None


def _chuoi_cookie(tep: str | None) -> str:
    """cookies.txt (Netscape) ⇒ header Cookie, CHỈ cookie của miền kuaishou.com."""
    if not tep:
        return ""
    cap = []
    for dong in Path(tep).read_text(encoding="utf-8").splitlines():
        if not dong or (dong.startswith("#") and not dong.startswith("#HttpOnly_")):
            continue
        phan = dong.split("\t")
        if len(phan) != 7:
            continue
        mien = phan[0].removeprefix("#HttpOnly_").lstrip(".").lower()
        if mien == "kuaishou.com" or mien.endswith(".kuaishou.com"):
            cap.append(f"{phan[5]}={phan[6]}")
    return "; ".join(cap)


class KuaishouAdapter:
    nen_tang = "kuaishou"

    def __init__(self, web: Any = None, *, max_filesize: int = MAX_FILESIZE_MAC_DINH,
                 thoi_luong_toi_da_s: int = THOI_LUONG_TOI_DA_MAC_DINH, phan_giai=None, nghi_s: float = 1.0):
        self._web = web if web is not None else kuaishou_web.KuaishouWeb()
        self.max_filesize = int(max_filesize)
        self.thoi_luong_toi_da_s = int(thoi_luong_toi_da_s)
        self._phan_giai = phan_giai
        self._nghi_s = float(nghi_s)
        #: cookies.txt TẠM của chủ job (jobs._phien đặt). None ⇒ ẩn danh.
        self.tep_cookie: str | None = None

    # ------------------------------------------------------------ id / URL
    def id_hop_le(self, id: Any) -> bool:
        return isinstance(id, str) and _ID.fullmatch(id) is not None

    def url_video(self, id: str) -> str:
        return f"{_GOC}/short-video/{id}"

    # ------------------------------------------------------------ gọi mạng (phân loại lỗi)
    def _goi(self, ham, *a, **kw):
        try:
            return ham(*a, **kw)
        except kuaishou_web.LoiHttp as e:
            if e.status == 404:
                raise _loi("http error 404") from None
            if 300 <= e.status < 400 or e.status in (403, 412, 429, 461):
                raise _nen_chan() from None
            raise _loi("") from None
        except (TimeoutError, OSError) as e:          # URLError là OSError
            raise _loi("timed out") from e

    def _chi_tiet(self, pid: str) -> dict:
        """Trang SSR của video `pid` ⇒ bản ghi `VisionVideoDetailPhoto` (+ `_tac_gia`)."""
        html = self._goi(self._web.lay_trang, self.url_video(pid), cookie=_chuoi_cookie(self.tep_cookie))
        st = doc_apollo(html)
        if st is None:
            raise _nen_chan()                         # captcha / trang rỗng: không có dữ liệu SSR
        kh = st.get("defaultClient") or {}
        anh = kh.get(f"VisionVideoDetailPhoto:{pid}")
        if not isinstance(anh, dict):
            # Server đã chạy truy vấn chi tiết (có khoá visionVideoDetail… trong ROOT_QUERY) mà không có video
            # ⇒ đã gỡ. Không có truy vấn nào (smoke thật 22/09: chỉ kconf/visionConfig) ⇒ bị chặn, không đoán "gỡ".
            goc = kh.get("ROOT_QUERY") or {}
            if any(str(k).startswith("visionVideoDetail") for k in goc):
                raise _loi("http error 404")
            raise _nen_chan()
        tac_gia = next((v.get("name") for k, v in kh.items()
                        if k.startswith("VisionVideoDetailAuthor:") and isinstance(v, dict)), "")
        return {**anh, "_tac_gia": str(tac_gia or "")}

    def _item(self, pid: str, anh: dict, tac_gia: str) -> CrawlItem:
        return CrawlItem(nen_tang=self.nen_tang, id=pid, url=self.url_video(pid),
                         tieu_de=str(anh.get("caption") or ""), tac_gia=tac_gia,
                         thoi_luong_s=_ms_sang_s(anh.get("duration")), anh_bia=str(anh.get("coverUrl") or ""))

    def _la_video(self, anh: dict) -> bool:
        return bool(anh.get("photoUrl")) and _ms_sang_s(anh.get("duration")) is not None

    def _qua_dai(self, anh: dict) -> bool:
        s = _ms_sang_s(anh.get("duration"))
        return s is not None and s > self.thoi_luong_toi_da_s

    # ------------------------------------------------------------ GraphQL
    def _graphql(self, ten_op: str, query: str, bien: dict, referer: str, cookie: str) -> dict:
        tho = self._goi(self._web.goi_graphql, {"operationName": ten_op, "variables": bien, "query": query},
                        cookie=cookie, referer=referer)
        try:
            js = json.loads(tho)
        except ValueError:
            js = None
        khoi = ((js or {}).get("data") or {}).get(ten_op) if isinstance(js, dict) else None
        if isinstance(khoi, dict) and khoi.get("result") == 1:
            return khoi
        low = (tho or "").lower()
        if any(d in low for d in _DAU_DANG_NHAP) and not any(d in low for d in _DAU_CAPTCHA):
            raise _can_dang_nhap()
        raise _nen_chan()

    def _danh_sach(self, ten_op: str, query: str, bien: dict, referer: str, n: int,
                   bao_tien_do: BaoTienDo) -> list[CrawlItem]:
        cookie = _chuoi_cookie(self.tep_cookie)
        ra: list[CrawlItem] = []
        da: set[str] = set()
        for trang in range(_TRANG_TOI_DA):
            if trang:
                time.sleep(self._nghi_s)
            khoi = self._graphql(ten_op, query, bien, referer, cookie)
            for f in khoi.get("feeds") or []:
                anh = (f or {}).get("photo") or {}
                pid = str(anh.get("id") or "")
                if len(ra) >= n or pid in da or not self.id_hop_le(pid):
                    continue
                if not self._la_video(anh) or self._qua_dai(anh):
                    continue
                da.add(pid)
                ra.append(self._item(pid, anh, str(((f or {}).get("author") or {}).get("name") or "")))
            bao_tien_do(min(95, len(ra) * 100 // max(n, 1)), _t("đang tìm video"))
            pc = str(khoi.get("pcursor") or "")
            if len(ra) >= n or not pc or pc == _HET or not khoi.get("feeds"):
                break
            bien = {**bien, "pcursor": pc}
            if "searchSessionId" in bien:
                bien["searchSessionId"] = str(khoi.get("searchSessionId") or bien["searchSessionId"])
        return ra

    # ------------------------------------------------------------ hợp đồng
    def kham_pha(self, yeu_cau: YeuCauCao, *, bao_tien_do: BaoTienDo) -> list[CrawlItem]:
        che_do, vao, n = yeu_cau.che_do, (yeu_cau.dau_vao or "").strip(), int(yeu_cau.so_luong)
        if che_do == "link":
            m = _URL_VIDEO.fullmatch(vao)
            if m is None:
                raise _khong_ho_tro()
            bao_tien_do(0, _t("đang tìm video"))
            anh = self._chi_tiet(m.group(1))
            if not self._la_video(anh):
                raise _loi("no video formats found")
            ra = [] if self._qua_dai(anh) else [self._item(m.group(1), anh, anh["_tac_gia"])]
        elif che_do == "kenh":
            m = _URL_KENH.fullmatch(vao)
            uid = m.group(1) if m else (vao if self.id_hop_le(vao) else None)
            if uid is None:
                raise _khong_ho_tro()
            if not self.tep_cookie:
                raise _can_dang_nhap()
            bao_tien_do(0, _t("đang tìm video"))
            ra = self._danh_sach("visionProfilePhotoList", _Q_KENH,
                                 {"userId": uid, "pcursor": "", "page": "profile"},
                                 f"{_GOC}/profile/{uid}", n, bao_tien_do)
        elif che_do == "tu_khoa":
            if not vao:
                raise _khong_ho_tro()
            if not self.tep_cookie:
                raise _can_dang_nhap()
            bao_tien_do(0, _t("đang tìm video"))
            ra = self._danh_sach("visionSearchPhoto", _Q_TIM,
                                 {"keyword": vao, "pcursor": "", "page": "search", "searchSessionId": ""},
                                 f"{_GOC}/search/video", n, bao_tien_do)
        else:
            raise _khong_ho_tro()
        bao_tien_do(100, _t("tìm thấy {n} video").format(n=len(ra)))
        return ra

    def _kiem_cdn(self, url: str) -> str:
        kw = {"ten_mien": CDN_VIDEO}
        if self._phan_giai is not None:
            kw["phan_giai"] = self._phan_giai
        try:
            return an_toan_url.kiem(url, **kw)
        except an_toan_url.UrlKhongAnToan:
            raise LoiCao("cdn_khong_cho_phep", _loi("").thong_diep, tam_thoi=False) from None

    def tai(self, item: CrawlItem, thu_muc: Path, *, bao_tien_do: BaoTienDo) -> TepTai:
        if not self.id_hop_le(item.id) or item.url != self.url_video(item.id):
            raise _khong_ho_tro()
        anh = self._chi_tiet(item.id)
        if not self._la_video(anh):
            raise _loi("no video formats found")
        if self._qua_dai(anh):
            raise LoiCao("qua_dai", _t(_TU_CHOI["qua_dai"]), tam_thoi=False)
        dich = Path(thu_muc) / f"{item.id}.mp4"

        def moi_khoi(xong: int, tong: int | None) -> None:
            pct = max(0, min(98, xong * 100 // tong)) if tong else 0
            bao_tien_do(pct, _t("đang tải"))

        try:
            kich_thuoc = self._goi(self._web.tai_luong, str(anh["photoUrl"]), dich, toi_da=self.max_filesize,
                                   kiem_url=self._kiem_cdn, moi_khoi=moi_khoi)
        except kuaishou_web.QuaLon:
            dich.unlink(missing_ok=True)
            raise LoiCao("qua_lon", _t(_TU_CHOI["qua_lon"]), tam_thoi=False) from None
        ten = ten_sach(item.tieu_de or str(anh.get("caption") or "")) or item.id
        return TepTai(duong_dan=dich, kich_thuoc=int(kich_thuoc), ten_hien_thi=f"{ten} [{item.id}].mp4")
