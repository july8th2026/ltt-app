"""Tìm kiếm web cho agent LTTCODE qua SearXNG riêng của công ty (P06).

SearXNG chạy trong WSL2 trên chính máy chủ, chỉ nghe `127.0.0.1`
(`tools/lttcode_searxng/` ở kho này dựng nó). Nền tảng là cửa duy nhất: xác thực
bằng khoá thiết bị, giới hạn lượt, chuẩn hoá kết quả. Chủ dự án chốt 17/09:
**miễn phí**, 20 lượt/phút và 300 lượt/ngày mỗi khoá — vừa chống lạm dụng, vừa
giữ IP máy chủ khỏi bị các công cụ tìm kiếm chặn.

⛔ Không ghi câu truy vấn vào log: đó là dữ liệu của người dùng. Chỉ ghi tên
engine không trả lời (để vận hành biết engine nào đang bị CAPTCHA).
"""
from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from typing import Any

import httpx

log = logging.getLogger(__name__)

SEARXNG_URL_MAC_DINH = "http://127.0.0.1:8888"
BIEN_URL = "LTT_LTTCODE_SEARXNG_URL"
TIMEOUT_S = 15.0
TOI_DA_NGUON = 8
DO_DAI_SNIPPET = 500
DO_DAI_TRUY_VAN = 400

_transport: httpx.AsyncBaseTransport | None = None


def dat_transport(transport: httpx.AsyncBaseTransport | None) -> None:
    """Chỉ cho test: thay SearXNG thật bằng `httpx.MockTransport`."""
    global _transport
    _transport = transport


def chuan_hoa(du_lieu: Any, *, toi_da: int) -> list[dict]:
    """JSON của SearXNG (`/search?format=json`) → `sources[]` cho plugin DSH."""
    ket_qua = du_lieu.get("results") if isinstance(du_lieu, dict) else None
    if not isinstance(ket_qua, list):
        return []
    nguon: list[dict] = []
    for r in ket_qua:
        if not isinstance(r, dict):
            continue
        url = r.get("url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            continue
        muc: dict = {"url": url}
        if isinstance(r.get("title"), str) and r["title"].strip():
            muc["title"] = r["title"].strip()[:300]
        if isinstance(r.get("content"), str) and r["content"].strip():
            muc["snippet"] = r["content"].strip()[:DO_DAI_SNIPPET]
        if isinstance(r.get("publishedDate"), str) and r["publishedDate"]:
            muc["published_at"] = r["publishedDate"]
        nguon.append(muc)
        if len(nguon) >= min(max(toi_da, 1), TOI_DA_NGUON):
            break
    return nguon


class GioiHanKhoa:
    """Hai cửa sổ trượt trong tiến trình (phút, ngày) theo khoá. Lượt bị từ chối không tính."""

    def __init__(self, moi_phut: int, moi_ngay: int) -> None:
        self.moi_phut, self.moi_ngay = moi_phut, moi_ngay
        self._lan: dict[str, deque[float]] = {}
        self._khoa = threading.Lock()

    def cho_phep(self, khoa: str, *, now: float | None = None) -> bool:
        t = time.monotonic() if now is None else now
        with self._khoa:
            q = self._lan.setdefault(khoa, deque())
            while q and t - q[0] > 86_400:
                q.popleft()
            trong_phut = sum(1 for x in q if t - x <= 60)
            if trong_phut >= self.moi_phut or len(q) >= self.moi_ngay:
                return False
            q.append(t)
            return True

    def xoa(self) -> None:
        with self._khoa:
            self._lan.clear()


GIOI_HAN = GioiHanKhoa(moi_phut=20, moi_ngay=300)


async def goi_searxng(truy_van: str) -> dict | None:
    """Một lượt hỏi SearXNG. `None` khi nó không trả lời được — người gọi báo 503."""
    goc = os.environ.get(BIEN_URL, SEARXNG_URL_MAC_DINH).rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_S, transport=_transport) as client:
            r = await client.get(f"{goc}/search", params={
                "q": truy_van, "format": "json", "categories": "general", "safesearch": "0"})
    except httpx.HTTPError as e:
        log.warning("lttcode search: SearXNG unreachable: %s", type(e).__name__)
        return None
    if r.status_code != 200:
        log.warning("lttcode search: SearXNG answered HTTP %s", r.status_code)
        return None
    try:
        du_lieu = r.json()
    except ValueError:
        log.warning("lttcode search: SearXNG answered a non-JSON body")
        return None
    if not isinstance(du_lieu, dict):
        return None
    hong = du_lieu.get("unresponsive_engines")
    if isinstance(hong, list) and hong:
        ten = ", ".join(f"{e[0]}({e[1]})" for e in hong if isinstance(e, list) and len(e) >= 2)
        log.warning("lttcode search: unresponsive engines: %s", ten)
    return du_lieu
