"""Proxy ảnh bìa cho "Xem trước & chọn" (SO_LOI L10).

CSP nền tảng chặn ảnh bên thứ ba (`img-src 'self' …`) — ĐÚNG, vì tải thẳng từ CDN lộ IP khách. Donor hiện ảnh bìa trong
xem trước (`H:9336`), nên app phục vụ lại ảnh qua route của chính nó, với:
- host thuộc CDN ảnh của ĐÚNG nền (allowlist dưới) + chặn IP nội bộ (`an_toan_url`, gồm phân giải DNS);
- không theo redirect, timeout 5 s, tối đa 2 MB, chỉ `image/*`;
- URL lấy từ kết quả xem trước CỦA CHÍNH người dùng (`url_cua`) — khách không gửi URL.
Việc nhỏ (< 5 s, vài trăm KB) nên chạy trong request; không phải việc dài của hàng đợi job.
"""
from __future__ import annotations

import urllib.request

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
}
TOI_DA_BYTE = 2 * 1024 * 1024
_TIMEOUT_S = 5


class AnhKhongHopLe(ValueError):
    """Không phục vụ được ảnh này (host ngoài allowlist, không phải ảnh, quá lớn, lỗi mạng)."""


class _KhongRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):        # redirect có thể trỏ ra ngoài allowlist ⇒ không theo
        return None


def _lay_mac_dinh(url: str, *, toi_da: int) -> tuple[bytes, str]:
    mo = urllib.request.build_opener(_KhongRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with mo.open(req, timeout=_TIMEOUT_S) as r:
        if getattr(r, "status", 200) != 200:
            raise AnhKhongHopLe("ảnh không tải được")
        du_lieu = r.read(toi_da + 1)
        return du_lieu, str(r.headers.get("Content-Type") or "")


def tai(url: str, *, nen_tang: str | None = None, phan_giai=None, lay=None) -> tuple[bytes, str]:
    """(bytes, content-type) của ảnh bìa, hoặc ném `AnhKhongHopLe`."""
    if nen_tang is not None:
        mien = CDN_ANH.get(nen_tang, ())
    else:
        mien = tuple(sorted({m for ds in CDN_ANH.values() for m in ds}))
    if not mien:
        raise AnhKhongHopLe("nền không có CDN ảnh")
    kw = {"ten_mien": mien}
    if phan_giai is not None:
        kw["phan_giai"] = phan_giai
    try:
        url = an_toan_url.kiem(url, **kw)
    except an_toan_url.UrlKhongAnToan as e:
        raise AnhKhongHopLe("host ảnh không được phép") from e
    try:
        du_lieu, loai = (lay or _lay_mac_dinh)(url, toi_da=TOI_DA_BYTE)
    except AnhKhongHopLe:
        raise
    except Exception as e:  # noqa: BLE001 — mọi lỗi mạng đều thành "không có ảnh", không lộ chi tiết
        raise AnhKhongHopLe("ảnh không tải được") from e
    loai = loai.split(";")[0].strip().lower()
    if not loai.startswith("image/") or loai == "image/svg+xml":     # SVG có thể mang script
        raise AnhKhongHopLe("không phải ảnh")
    if len(du_lieu) > TOI_DA_BYTE:
        raise AnhKhongHopLe("ảnh quá lớn")
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
