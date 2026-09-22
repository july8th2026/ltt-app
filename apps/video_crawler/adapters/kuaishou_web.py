"""Tầng HTTP của adapter Kuaishou — nơi DUY NHẤT app này tự dựng HTTP tới kuaishou.com / CDN Kuaishou.

yt-dlp không có extractor Kuaishou (kiểm `yt_dlp/extractor/_extractors.py` bản đã cài) ⇒ adapter tự gọi:
- GET trang SSR `https://www.kuaishou.com/short-video/<photoId>` (không theo chuyển hướng — 3xx ⇒ `LoiHttp`);
- POST GraphQL `https://www.kuaishou.com/graphql` (không theo chuyển hướng);
- GET luồng mp4 trên CDN, THEO chuyển hướng nhưng MỖI đích mới đi qua `kiem_url` (allowlist CDN + chặn IP
  nội bộ — `an_toan_url.kiem`), ghi theo khối, trần dung lượng, báo từng khối (để huỷ hợp tác).

Không phải nhà cung cấp AI, không khoá API. Chỉ thư viện chuẩn (`urllib`) — không thêm phụ thuộc.
Mọi logic (dựng URL, phân loại lỗi, lọc) ở `kuaishou.py`; tệp này chỉ vận chuyển byte — test thay `_mo`.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

GRAPHQL = "https://www.kuaishou.com/graphql"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/140.0.0.0 Safari/537.36")
TIMEOUT_S = 30
KHOI = 256 * 1024
TOI_DA_TRANG = 8 * 1024 * 1024        # trang SSR / JSON GraphQL — chặn phản hồi phình vô hạn


class LoiHttp(Exception):
    """Phản hồi HTTP không phải 200 (kể cả 3xx vì không theo chuyển hướng)."""

    def __init__(self, status: int):
        super().__init__(f"http error {status}")
        self.status = int(status)


class QuaLon(Exception):
    """Tệp vượt trần dung lượng (theo Content-Length hoặc khi đang đọc luồng)."""


class _KhongChuyenHuong(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None                                   # urllib ném HTTPError(3xx) ⇒ LoiHttp


class _ChuyenHuongCoKiem(urllib.request.HTTPRedirectHandler):
    """Theo chuyển hướng, nhưng đích mới phải qua `kiem` (ném ⇒ dừng)."""

    def __init__(self, kiem: Callable[[str], str]):
        super().__init__()
        self._kiem = kiem

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self._kiem(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _headers(cookie: str = "", referer: str = "") -> dict[str, str]:
    h = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}
    if cookie:
        h["Cookie"] = cookie
    if referer:
        h["Referer"] = referer
    return h


class KuaishouWeb:
    """Vận chuyển HTTP thật. Adapter nhận một đối tượng cùng giao diện (test tiêm bản giả)."""

    def __init__(self, timeout_s: float = TIMEOUT_S):
        self.timeout_s = timeout_s

    def _mo(self, req: urllib.request.Request, *, theo_chuyen_huong: bool,
            kiem_url: Callable[[str], str] | None = None):
        h = _ChuyenHuongCoKiem(kiem_url or (lambda u: u)) if theo_chuyen_huong else _KhongChuyenHuong()
        return urllib.request.build_opener(h).open(req, timeout=self.timeout_s)

    def _doc(self, req: urllib.request.Request) -> str:
        try:
            with self._mo(req, theo_chuyen_huong=False) as r:
                status = getattr(r, "status", 200)
                if status != 200:
                    raise LoiHttp(status)
                du_lieu = r.read(TOI_DA_TRANG + 1)
        except urllib.error.HTTPError as e:
            raise LoiHttp(e.code) from None
        return du_lieu[:TOI_DA_TRANG].decode("utf-8", errors="replace")

    def lay_trang(self, url: str, *, cookie: str = "") -> str:
        h = _headers(cookie)
        h["Accept"] = "text/html,application/xhtml+xml"
        return self._doc(urllib.request.Request(url, headers=h))

    def goi_graphql(self, body: dict, *, cookie: str = "", referer: str = "") -> str:
        h = _headers(cookie, referer)
        h.update({"Content-Type": "application/json", "Accept": "*/*", "Origin": "https://www.kuaishou.com"})
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        return self._doc(urllib.request.Request(GRAPHQL, data=data, headers=h, method="POST"))

    def tai_luong(self, url: str, dich: Path, *, toi_da: int, kiem_url: Callable[[str], str],
                  moi_khoi: Callable[[int, int | None], None]) -> int:
        """Tải `url` vào `dich`. `moi_khoi(đã_ghi, tổng|None)` sau mỗi khối (ném ⇒ huỷ). Hỏng ⇒ xoá tệp dở."""
        kiem_url(url)
        dich = Path(dich)
        req = urllib.request.Request(url, headers=_headers(referer="https://www.kuaishou.com/"))
        xong = 0
        try:
            with self._mo(req, theo_chuyen_huong=True, kiem_url=kiem_url) as r:
                status = getattr(r, "status", 200)
                if status != 200:
                    raise LoiHttp(status)
                cl = (r.headers or {}).get("Content-Length")
                tong = int(cl) if cl and str(cl).isdigit() else None
                if tong is not None and tong > toi_da:
                    raise QuaLon()
                with open(dich, "wb") as f:
                    while True:
                        khoi = r.read(KHOI)
                        if not khoi:
                            break
                        xong += len(khoi)
                        if xong > toi_da:
                            raise QuaLon()
                        f.write(khoi)
                        moi_khoi(xong, tong)
        except urllib.error.HTTPError as e:
            dich.unlink(missing_ok=True)
            raise LoiHttp(e.code) from None
        except BaseException:
            dich.unlink(missing_ok=True)
            raise
        return xong
