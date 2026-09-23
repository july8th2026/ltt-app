"""video_crawler — chặn SSRF cho URL người dùng đưa vào yt-dlp (spec §21).

Port `_url_an_toan` (D:\\Viral\\resources\\app-src\\tai_ytdlp.py:1608-1626, chỉ đọc):
chỉ http(s), host không rỗng, không `localhost`, IP literal không loopback/private/reserved/link-local.

LTT siết thêm hai lớp donor KHÔNG có:
  1. host phải bằng hoặc là subdomain của một `ten_mien` cho phép (allowlist theo nền đã chọn) —
     chặn cả tên miền giả dạng hậu tố (`notyoutube.com` không phải subdomain của `youtube.com`).
  2. phân giải DNS của host và chặn nếu BẤT KỲ IP trả về là nội bộ (donor để tên miền đi thẳng,
     lọt DNS rebinding trỏ về 127.0.0.1). Phân giải được TIÊM (`phan_giai`) để test không đọc mạng thật.

`theo_chuyen_huong` (lane W4-L12, `docs/migrations/video_crawler/THIET_KE_PHIEN_VA_KENH.md` §3.2 P2):
theo chuyển hướng HTTP CÓ KIỂM cho link rút gọn (`v.douyin.com`, `xhslink.com`, `v.kuaishou.com`,
`b23.tv`, `vt.tiktok.com`/`vm.tiktok.com`, …) — MỖI bước (kể cả URL gốc) đi qua lại đúng `kiem()` ở
trên với CÙNG allowlist `ten_mien` của nền đã chọn, nên một bước chuyển hướng ra ngoài tên miền của
nền đó (hoặc ra IP nội bộ, kể cả qua DNS rebinding ở bước SAU) bị chặn giống hệt URL gốc. Tối đa
`toi_da_buoc` bước; vòng lặp chuyển hướng cũng bị chặn. Không tải thân trang (`HEAD`/`GET` trần vài
KB), không gửi cookie, hạn giờ ngắn — hàm mở URL (`mo`) được TIÊM để test không đọc mạng thật.
"""
from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request

from platform_core.i18n import _ as _t


class UrlKhongAnToan(ValueError):
    """URL không an toàn để cào (SSRF: scheme/host/IP nội bộ/ngoài allowlist)."""


def _phan_giai_mac_dinh(host: str) -> list[str]:
    return [str(info[4][0]) for info in socket.getaddrinfo(host, None)]


def _la_ip_noi_bo(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_private or ip.is_reserved or ip.is_link_local


def _thuoc_ten_mien(host: str, ten_mien: tuple) -> bool:
    host = host.lower()
    for dom in ten_mien:
        dom = dom.lower()
        if host == dom or host.endswith("." + dom):
            return True
    return False


def kiem(url: str, *, ten_mien: tuple, phan_giai=_phan_giai_mac_dinh) -> str:
    """Trả `url` (đã strip) nếu an toàn; ném `UrlKhongAnToan` nếu không."""
    goc = (url or "").strip()
    try:
        p = urllib.parse.urlparse(goc)
    except Exception as exc:
        raise UrlKhongAnToan(_t("URL không hợp lệ: {url!r}").format(url=goc)) from exc

    if p.scheme not in ("http", "https"):
        raise UrlKhongAnToan(_t("scheme không cho phép: {scheme!r}").format(scheme=p.scheme))

    host = (p.hostname or "").lower()
    if not host or host == "localhost":
        raise UrlKhongAnToan(_t("host rỗng hoặc localhost"))

    # Donor: IP literal ở chính host bị chặn nếu nội bộ (tên miền → ValueError, bỏ qua ở đây).
    try:
        ip_host = ipaddress.ip_address(host)
    except ValueError:
        ip_host = None
    if ip_host is not None and _la_ip_noi_bo(host):
        raise UrlKhongAnToan(_t("IP nội bộ bị chặn: {host}").format(host=host))

    # LTT #1: host phải thuộc allowlist tên miền của nền đã chọn.
    if not _thuoc_ten_mien(host, ten_mien):
        raise UrlKhongAnToan(_t("tên miền không thuộc allowlist: {host}").format(host=host))

    # LTT #2: phân giải DNS, chặn DNS rebinding về nội bộ.
    try:
        ips = phan_giai(host)
    except Exception as exc:
        raise UrlKhongAnToan(_t("không phân giải được host: {host}").format(host=host)) from exc
    if not ips:
        raise UrlKhongAnToan(_t("không phân giải được host: {host}").format(host=host))
    for ip_str in ips:
        if _la_ip_noi_bo(ip_str):
            raise UrlKhongAnToan(_t("tên miền phân giải ra IP nội bộ: {ip}").format(ip=ip_str))

    return goc


#: Mã HTTP redirect theo `mo()` — donor/yt-dlp coi 3xx này là "chuyển hướng" (RFC 7231 §6.4 + 308).
_MA_CHUYEN_HUONG = frozenset({301, 302, 303, 307, 308})

_TOI_DA_BUOC_MAC_DINH = 3
_TRAN_BYTES_MAC_DINH = 4096
_HAN_GIAY_MAC_DINH = 5.0
_TAC_NHAN = "LTTStudios-video-crawler-link-resolver/1"


class _KhongTuChuyenHuong(urllib.request.HTTPRedirectHandler):
    """Chặn `urllib` tự theo redirect — `theo_chuyen_huong` tự kiểm (`kiem()`) từng bước một."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102 (chữ ký của thư viện)
        return None


def _mo_mac_dinh(url: str, *, han_giay: float, tran_bytes: int) -> tuple[int, str | None]:
    """Mở `url` thật: `HEAD` trước (không thân trang); rơi về `GET` + `Range` (trần `tran_bytes`) nếu
    nền chặn `HEAD` (405/501 — một số CDN link rút gọn chỉ nhận `GET`). Không cookiejar ⇒ không gửi
    cookie. Không tự theo redirect (`_KhongTuChuyenHuong`) — trả `(status, Location)` cho từng bước."""
    opener = urllib.request.build_opener(_KhongTuChuyenHuong)
    for phuong_thuc in ("HEAD", "GET"):
        tieu_de = {"User-Agent": _TAC_NHAN}
        if phuong_thuc == "GET":
            tieu_de["Range"] = f"bytes=0-{max(tran_bytes, 1) - 1}"
        req = urllib.request.Request(url, method=phuong_thuc, headers=tieu_de)
        try:
            with opener.open(req, timeout=han_giay) as resp:
                if phuong_thuc == "GET":
                    resp.read(tran_bytes)
                return resp.status, resp.headers.get("Location")
        except urllib.error.HTTPError as exc:
            if exc.code in _MA_CHUYEN_HUONG:
                return exc.code, exc.headers.get("Location")
            if phuong_thuc == "HEAD" and exc.code in (405, 501):
                continue  # nền không nhận HEAD ⇒ rơi về GET
            raise
    raise UrlKhongAnToan(_t("không mở được URL: {url}").format(url=url))  # không tới được (405 cả hai)


def theo_chuyen_huong(url: str, *, ten_mien: tuple, phan_giai=_phan_giai_mac_dinh, mo=None,
                       toi_da_buoc: int = _TOI_DA_BUOC_MAC_DINH, han_giay: float = _HAN_GIAY_MAC_DINH,
                       tran_bytes: int = _TRAN_BYTES_MAC_DINH) -> str:
    """Theo chuyển hướng HTTP CÓ KIỂM cho link rút gọn; trả URL cuối cùng (đã qua `kiem()`).

    MỖI bước — kể cả `url` gốc — đi qua `kiem(bước, ten_mien=ten_mien, phan_giai=phan_giai)`: chuyển
    hướng ra ngoài allowlist `ten_mien` của nền đã chọn, hoặc ra IP nội bộ (trực tiếp hoặc qua DNS
    rebinding ở bước SAU), bị chặn giống hệt URL gốc. Tối đa `toi_da_buoc` lần chuyển hướng (mặc định
    3) và bắt vòng lặp chuyển hướng (URL đã đi qua). `mo` (mặc định `_mo_mac_dinh`, gọi mạng thật)
    được TIÊM để test không đọc mạng — chữ ký `mo(url, *, han_giay, tran_bytes) -> (status, location)`.

    Ném `UrlKhongAnToan` với thông điệp CHUNG (không lộ URL/IP đích, không lộ chi tiết DNS) khi link
    không giải được — chi tiết thật nằm ở exception gốc (`__cause__`) cho log nội bộ, KHÔNG cho khách."""
    mo = mo or _mo_mac_dinh
    try:
        hien = kiem(url, ten_mien=ten_mien, phan_giai=phan_giai)
        da_qua = {hien}
        buoc = 0
        while True:
            trang_thai, vi_tri = mo(hien, han_giay=han_giay, tran_bytes=tran_bytes)
            if trang_thai not in _MA_CHUYEN_HUONG or not vi_tri:
                return hien                          # điểm cuối: không còn chuyển hướng
            # `buoc` đếm CHUYỂN HƯỚNG THẬT (Location nhận được), không đếm lượt `mo()` xác nhận điểm
            # cuối — nếu không, đủ `toi_da_buoc` chuyển hướng hợp lệ sẽ luôn bị chặn nhầm vì hết lượt
            # trước khi có cơ hội xác nhận đích cuối cùng không chuyển hướng tiếp (off-by-one).
            buoc += 1
            if buoc > toi_da_buoc:
                raise UrlKhongAnToan(_t("quá nhiều bước chuyển hướng (tối đa {n})").format(n=toi_da_buoc))
            tiep = kiem(urllib.parse.urljoin(hien, vi_tri), ten_mien=ten_mien, phan_giai=phan_giai)
            if tiep in da_qua:
                raise UrlKhongAnToan(_t("vòng lặp chuyển hướng"))
            da_qua.add(tiep)
            hien = tiep
    except UrlKhongAnToan as exc:
        raise UrlKhongAnToan(
            _t("Không giải được link rút gọn — chuyển hướng không an toàn hoặc trỏ ra ngoài nền đã chọn.")
        ) from exc
    except Exception as exc:
        raise UrlKhongAnToan(_t("Không giải được link rút gọn.")) from exc
