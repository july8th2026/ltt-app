"""Proxy ảnh bìa cho "Xem trước & chọn" (SO_LOI L10).

CSP nền tảng chặn ảnh bên thứ ba (`img-src 'self' …`) — ĐÚNG, vì tải thẳng từ CDN lộ IP khách. Donor hiện ảnh bìa trong
xem trước (`H:9336`), nên app phục vụ lại ảnh qua route của chính nó, với:
- host thuộc CDN ảnh của ĐÚNG nền (allowlist dưới) + chặn IP nội bộ (`an_toan_url`, gồm phân giải DNS);
- không theo redirect, timeout 5 s, tối đa 2 MB, chỉ `image/*`;
- URL lấy từ kết quả xem trước CỦA CHÍNH người dùng (`url_cua`) — khách không gửi URL.
Việc nhỏ (< 5 s, vài trăm KB) nên chạy trong request; không phải việc dài của hàng đợi job.
"""
from __future__ import annotations

import threading
import time
import urllib.request
from collections import OrderedDict

from platform_core.i18n import _ as _t

from apps.video_crawler import an_toan_url

#: CDN ảnh bìa theo nền (hậu tố tên miền). Thêm nền mới ⇒ thêm dòng (test_1919 chốt mọi nền bật đều có).
CDN_ANH: dict[str, tuple[str, ...]] = {
    "youtube": ("ytimg.com", "ggpht.com"),
    "tiktok": ("tiktokcdn.com", "tiktokcdn-us.com", "tiktokcdn-eu.com", "ibyteimg.com", "muscdn.com"),
    "douyin": ("douyinpic.com", "douyinstatic.com", "pstatp.com", "byteimg.com"),
    "bilibili": ("hdslb.com", "biliimg.com"),
    "bilibili_tv": ("bstarstatic.com", "hdslb.com", "biliintl.com"),
    "xiaohongshu": ("xhscdn.com", "xhscdn.net"),
    "weibo": ("sinaimg.cn",),
    "facebook": ("fbcdn.net",),
    "instagram": ("cdninstagram.com", "fbcdn.net"),
    "twitter": ("twimg.com",),
    "kuaishou": ("kwimgs.com", "yximgs.com", "kwaicdn.com"),
}
TOI_DA_BYTE = 2 * 1024 * 1024
_TIMEOUT_S = 5
#: Review lần 2: một trang xem trước = tới 20 ảnh ⇒ route đồng bộ vắt kiệt threadpool nếu CDN chậm.
#: Giới hạn số lượt tải đồng thời (toàn tiến trình), hạn TỔNG mỗi ảnh, và bộ nhớ đệm để hiển thị lại không tải lại.
_SO_LUONG_DONG_THOI = threading.BoundedSemaphore(4)
_HAN_TONG_S = 6.0
#: Khoá đệm = (nền, URL): đệm theo URL thôi thì ảnh đã duyệt cho nền A trả ra cho yêu cầu mang nền B (lách allowlist).
_DEM: OrderedDict[tuple[str, str], tuple[float, bytes, str]] = OrderedDict()
_DEM_KHOA = threading.Lock()
_DEM_TOI_DA = 256
_DEM_TUOI_S = 3600.0


def xoa_dem() -> None:
    with _DEM_KHOA:
        _DEM.clear()


class AnhKhongHopLe(ValueError):
    """Không phục vụ được ảnh này (host ngoài allowlist, không phải ảnh, quá lớn, lỗi mạng)."""


class _KhongRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):        # redirect có thể trỏ ra ngoài allowlist ⇒ không theo
        return None


def _lay_mac_dinh(url: str, *, toi_da: int) -> tuple[bytes, str]:
    mo = urllib.request.build_opener(_KhongRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    han = time.monotonic() + _HAN_TONG_S
    with mo.open(req, timeout=_TIMEOUT_S) as r:
        if getattr(r, "status", 200) != 200:
            raise AnhKhongHopLe(_t("ảnh không tải được"))
        khoi, co = [], 0
        while co <= toi_da:                              # đọc từng khối để giữ hạn TỔNG, không chỉ hạn mỗi lượt đọc
            if time.monotonic() > han:
                raise AnhKhongHopLe(_t("ảnh tải quá chậm"))
            b = r.read(64 * 1024)
            if not b:
                break
            khoi.append(b)
            co += len(b)
        return b"".join(khoi), str(r.headers.get("Content-Type") or "")


def tai(url: str, *, nen_tang: str | None = None, phan_giai=None, lay=None,
        cho_s: float = 2.0) -> tuple[bytes, str]:
    """(bytes, content-type) của ảnh bìa, hoặc ném `AnhKhongHopLe`. Có đệm + giới hạn đồng thời."""
    khoa = (nen_tang or "*", url)
    with _DEM_KHOA:
        hit = _DEM.get(khoa)
        if hit and time.monotonic() - hit[0] < _DEM_TUOI_S:
            _DEM.move_to_end(khoa)
            return hit[1], hit[2]
    if not _SO_LUONG_DONG_THOI.acquire(timeout=cho_s):
        raise AnhKhongHopLe(_t("đang bận"))
    try:
        du_lieu, loai = _tai_that(url, nen_tang=nen_tang, phan_giai=phan_giai, lay=lay)
    finally:
        _SO_LUONG_DONG_THOI.release()
    with _DEM_KHOA:
        _DEM[khoa] = (time.monotonic(), du_lieu, loai)
        while len(_DEM) > _DEM_TOI_DA:
            _DEM.popitem(last=False)
    return du_lieu, loai


def _tai_that(url: str, *, nen_tang: str | None, phan_giai, lay) -> tuple[bytes, str]:
    if nen_tang is not None:
        mien = CDN_ANH.get(nen_tang, ())
    else:
        mien = tuple(sorted({m for ds in CDN_ANH.values() for m in ds}))
    if not mien:
        raise AnhKhongHopLe(_t("nền không có CDN ảnh"))
    kw = {"ten_mien": mien}
    if phan_giai is not None:
        kw["phan_giai"] = phan_giai
    try:
        url = an_toan_url.kiem(url, **kw)
    except an_toan_url.UrlKhongAnToan as e:
        raise AnhKhongHopLe(_t("host ảnh không được phép")) from e
    try:
        du_lieu, loai = (lay or _lay_mac_dinh)(url, toi_da=TOI_DA_BYTE)
    except AnhKhongHopLe:
        raise
    except Exception as e:  # noqa: BLE001 — mọi lỗi mạng đều thành "không có ảnh", không lộ chi tiết
        raise AnhKhongHopLe(_t("ảnh không tải được")) from e
    loai = loai.split(";")[0].strip().lower()
    if not loai.startswith("image/") or loai == "image/svg+xml":     # SVG có thể mang script
        raise AnhKhongHopLe(_t("không phải ảnh"))
    if len(du_lieu) > TOI_DA_BYTE:
        raise AnhKhongHopLe(_t("ảnh quá lớn"))
    return du_lieu, loai


def url_cua(db, *, owner_id: str, job_id: str, chi_so: int) -> tuple[str, str] | None:
    """(nền, URL ảnh bìa) của mục `chi_so` trong kết quả xem trước CỦA CHÍNH `owner_id`, hoặc None."""
    from apps.video_crawler import features
    job = features.job_cua(db, owner_id, job_id, job_type=features.JOB_KHAM_PHA)
    if job is None:
        return None
    muc = (job.result or {}).get("muc") or []
    if not 0 <= chi_so < len(muc):
        return None
    url = str(muc[chi_so].get("anh_bia") or "")
    return (str((job.params or {}).get("nen_tang") or ""), url) if url else None
