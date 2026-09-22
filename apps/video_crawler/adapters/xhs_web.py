"""API web Xiaohongshu (edith) cho `tu_khoa` + `kenh` — yt-dlp không có extractor search/user cho nền này.

Nguồn (không chép mã — chỉ điểm cuối, tham số, mã lỗi):
- `ReaJason/xhs` (MIT, SHA f4b62d9f8e4078e631fc6e4ec8e430bc711ee9f0) `xhs/core.py`:
  POST `/api/sns/web/v1/search/notes` {keyword, page, page_size, search_id, sort, note_type} (VIDEO = 1);
  GET `/api/sns/web/v1/user_posted` {num, cursor, user_id, image_scenes}. `xhs/exception.py`: 300012 IP bị chặn,
  300015 ký sai, -100 hết phiên; HTTP 461/471 = captcha. Thư viện này ký web API bằng trình duyệt
  (`example/basic_usage.py`: Playwright gọi `window._webmsxyw`) ⇒ KHÔNG dùng để ký.
- Ký `x-s`/`x-t`/`x-s-common` (+ `x-rap-param` cho tìm kiếm): gói PyPI `xhshow==0.2.0` (`Cloxl/xhshow`, MIT,
  phụ thuộc `pycryptodome` BSD) — thuần Python, không trình duyệt, không mạng. Nạp lúc cần (chỉ worker gọi).

Đường ra HTTP: qua `YoutubeDL.urlopen` (bộ mạng của yt-dlp, cùng cookiejar nạp từ cookies.txt tạm của job) —
tầng app không tự dựng HTTP (`tests/test_1006_rao_kien_truc.py`).
Thông điệp lỗi: lấy nguyên câu của `loi.py` theo mã (không msgid mới, không lộ URL/cookie).
"""
from __future__ import annotations

import json
from typing import Any, Protocol

from apps.video_crawler.adapters.base import LoiCao
from apps.video_crawler.loi import _BANG, _KHAC

API = "https://edith.xiaohongshu.com"
URI_TIM = "/api/sns/web/v1/search/notes"
URI_KENH = "/api/sns/web/v1/user_posted"
TRANG_CHU = "https://www.xiaohongshu.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

#: Cookie phiên đem ký (`xhshow` README: a1 bắt buộc cho x-s; x-s-common đọc cả bộ).
COOKIE_KY = ("a1", "web_session", "webId", "gid", "id_token", "websectiga", "sec_poison_id", "xsecappid")
#: Thiếu một trong các cookie này ⇒ chưa đăng nhập (tìm/kênh đòi phiên — donor COOKIE_AUTH).
COOKIE_BAT_BUOC = ("a1", "web_session")

#: Mã `code` JSON ⇒ mã LoiCao. 300017/-104: tài khoản/thiết bị bị hạn chế; 300012: IP; 300015: ký bị từ chối.
MA_CHAN = frozenset({300012, 300015, 300017, -104})
MA_HET_PHIEN = frozenset({-100, -101})   # -101: không có thông tin đăng nhập (smoke thật 22/09)
HTTP_CHAN = frozenset({461, 471})


class Ky(Protocol):
    def ky(self, method: str, url: str, cookies: dict, *, params: dict | None = None,
           payload: dict | None = None) -> dict: ...

    def url_get(self, url: str, params: dict) -> str: ...

    def search_id(self) -> str: ...


class KyXhshow:
    """Bộ ký mặc định trên `xhshow` (MIT). Nạp lười: web process không cần gói này."""

    def __init__(self) -> None:
        from xhshow import Xhshow
        self._c = Xhshow()

    def ky(self, method: str, url: str, cookies: dict, *, params: dict | None = None,
           payload: dict | None = None) -> dict:
        if method == "GET":
            return dict(self._c.sign_headers_get(uri=url, cookies=cookies, params=params))
        return dict(self._c.sign_headers_post(uri=url, cookies=cookies, payload=payload, x_rap=True))

    def url_get(self, url: str, params: dict) -> str:
        """URL GET mã hoá ĐÚNG như chuỗi đã ký (`xhshow.utils.url_utils.build_url` — không phải `urlencode`)."""
        return str(self._c.build_url(url, params))

    def search_id(self) -> str:
        return str(self._c.get_search_id())


def loi(ma: str) -> LoiCao:
    """LoiCao với đúng câu + cờ tạm thời của `loi.py` cho `ma` (loi_khac ⇒ câu chung, tạm thời)."""
    for m, _tin_hieu, tam_thoi, cau in _BANG:
        if m == ma:
            return LoiCao(ma, cau, tam_thoi=tam_thoi)
    return LoiCao("loi_khac", _KHAC, tam_thoi=True)


def cookie_phien(cookiejar: Any) -> dict[str, str]:
    """Cookie của *.xiaohongshu.com trong cookiejar (yt-dlp nạp từ cookies.txt tạm)."""
    ra: dict[str, str] = {}
    for c in cookiejar or ():
        mien = str(getattr(c, "domain", "") or "").lstrip(".").lower()
        if (mien == "xiaohongshu.com" or mien.endswith(".xiaohongshu.com")) and c.name in COOKIE_KY and c.value:
            ra[c.name] = str(c.value)
    return ra


def kiem_phien(cookies: dict[str, str]) -> None:
    if any(not cookies.get(k) for k in COOKIE_BAT_BUOC):
        raise loi("can_dang_nhap")


def _giai_ma(than: bytes) -> dict:
    try:
        d = json.loads(than.decode("utf-8", "replace"))
    except ValueError:
        raise loi("loi_khac") from None
    if not isinstance(d, dict):
        raise loi("loi_khac")
    code = d.get("code")
    if d.get("success") is True and isinstance(d.get("data"), dict):
        return d["data"]
    if code in MA_CHAN:
        raise loi("nen_chan")
    if code in MA_HET_PHIEN:
        raise loi("can_dang_nhap")
    raise loi("loi_khac")


def goi(ydl: Any, ky: Ky, cookies: dict[str, str], method: str, uri: str, *,
        params: dict | None = None, payload: dict | None = None) -> dict:
    """Một lượt gọi API đã ký ⇒ `data` (dict). Mọi hỏng ⇒ LoiCao đã phân loại."""
    from yt_dlp.networking import Request
    from yt_dlp.networking.exceptions import HTTPError, TransportError

    url = API + uri
    h = {"User-Agent": UA, "Origin": TRANG_CHU, "Referer": TRANG_CHU + "/",
         "Accept": "application/json, text/plain, */*"}
    h.update(ky.ky(method, url, cookies, params=params, payload=payload))
    if method == "GET":
        req = Request(ky.url_get(url, params or {}), headers=h, method="GET")
    else:
        h["Content-Type"] = "application/json;charset=UTF-8"
        than = json.dumps(payload or {}, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        req = Request(url, data=than, headers=h, method="POST")
    try:
        r = ydl.urlopen(req)
        du_lieu = r.read()
    except HTTPError as e:
        raise loi("nen_chan" if e.status in HTTP_CHAN else "loi_khac") from None
    except TransportError:
        raise loi("mang") from None
    return _giai_ma(du_lieu)


def payload_tim(tu_khoa: str, trang: int, search_id: str, page_size: int = 20) -> dict:
    return {"keyword": tu_khoa, "page": trang, "page_size": page_size, "search_id": search_id,
            "sort": "general", "note_type": 1}


def params_kenh(user_id: str, cursor: str, xsec_token: str = "") -> dict:
    p = {"num": 30, "cursor": cursor, "user_id": user_id, "image_scenes": "FD_WM_WEBP"}
    if xsec_token:
        p.update(xsec_token=xsec_token, xsec_source="pc_note")
    return p


def _chu(v: Any) -> str:
    return v if isinstance(v, str) else ""


def note_tim(muc: Any) -> dict | None:
    """Mục kết quả tìm ⇒ {id, token, loai, tieu_de, tac_gia, anh_bia} (None nếu không phải note)."""
    if not isinstance(muc, dict) or muc.get("model_type") != "note" or not isinstance(muc.get("note_card"), dict):
        return None
    card = muc["note_card"]
    return _chuan(_chu(muc.get("id")), _chu(muc.get("xsec_token")) or _chu(card.get("xsec_token")), card)


def note_kenh(muc: Any) -> dict | None:
    if not isinstance(muc, dict):
        return None
    return _chuan(_chu(muc.get("note_id")), _chu(muc.get("xsec_token")), muc)


def _chuan(note: str, token: str, card: dict) -> dict:
    u, c = card.get("user"), card.get("cover")
    user: dict = u if isinstance(u, dict) else {}
    cover: dict = c if isinstance(c, dict) else {}
    return {"id": note, "token": token, "loai": _chu(card.get("type")),
            "tieu_de": _chu(card.get("display_title")) or _chu(card.get("title")),
            "tac_gia": _chu(user.get("nickname")) or _chu(user.get("nick_name")) or _chu(user.get("user_id")),
            "anh_bia": _chu(cover.get("url_default")) or _chu(cover.get("url"))}
