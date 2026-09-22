"""video_crawler — chặn SSRF cho URL người dùng đưa vào yt-dlp (spec §21).

Port `_url_an_toan` (D:\\Viral\\resources\\app-src\\tai_ytdlp.py:1608-1626, chỉ đọc):
chỉ http(s), host không rỗng, không `localhost`, IP literal không loopback/private/reserved/link-local.

LTT siết thêm hai lớp donor KHÔNG có:
  1. host phải bằng hoặc là subdomain của một `ten_mien` cho phép (allowlist theo nền đã chọn) —
     chặn cả tên miền giả dạng hậu tố (`notyoutube.com` không phải subdomain của `youtube.com`).
  2. phân giải DNS của host và chặn nếu BẤT KỲ IP trả về là nội bộ (donor để tên miền đi thẳng,
     lọt DNS rebinding trỏ về 127.0.0.1). Phân giải được TIÊM (`phan_giai`) để test không đọc mạng thật.
"""
from __future__ import annotations

import ipaddress
import socket
import urllib.parse

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
