"""
video_crawler — chặn SSRF cho URL người dùng đưa vào yt-dlp.

Characterization donor `_url_an_toan` (D:\\Viral\\resources\\app-src\\tai_ytdlp.py:1608-1626):
chỉ http(s), host không rỗng, không `localhost`, IP literal không loopback/private/reserved/link-local.

LTT siết thêm (spec §21): host phải thuộc tên miền của nền đã chọn, và tên miền phân giải ra IP
nội bộ cũng bị chặn (donor để tên miền đi thẳng — DNS rebinding tới 127.0.0.1 lọt qua).
Phân giải DNS được TIÊM để test không đọc mạng thật.
"""
from __future__ import annotations

import pytest

from apps.video_crawler import an_toan_url
from apps.video_crawler.an_toan_url import UrlKhongAnToan

_YT = ("youtube.com", "youtu.be")


def _dns_cong_khai(host):
    return ["142.250.66.78"]


@pytest.mark.parametrize("url", [
    "file:///C:/Windows/win.ini",
    "ftp://youtube.com/x",
    "http://localhost/x",
    "http://127.0.0.1/x",
    "http://192.168.1.10/x",
    "http://10.0.0.1/x",
    "http://169.254.169.254/latest/meta-data",
    "http://[::1]/x",
    "https:///nohost",
    "",
])
def test_donor_chan_scheme_va_ip_noi_bo(url):
    with pytest.raises(UrlKhongAnToan):
        an_toan_url.kiem(url, ten_mien=_YT, phan_giai=_dns_cong_khai)


def test_url_youtube_cong_khai_duoc_qua():
    u = an_toan_url.kiem("https://www.youtube.com/watch?v=abc", ten_mien=_YT, phan_giai=_dns_cong_khai)
    assert u == "https://www.youtube.com/watch?v=abc"


def test_ten_mien_ngoai_nen_bi_chan():
    with pytest.raises(UrlKhongAnToan):
        an_toan_url.kiem("https://evil.example/youtube.com", ten_mien=_YT, phan_giai=_dns_cong_khai)


def test_ten_mien_gia_dang_hau_to_bi_chan():
    with pytest.raises(UrlKhongAnToan):
        an_toan_url.kiem("https://notyoutube.com/watch?v=1", ten_mien=_YT, phan_giai=_dns_cong_khai)


def test_ten_mien_phan_giai_ra_ip_noi_bo_bi_chan():
    with pytest.raises(UrlKhongAnToan):
        an_toan_url.kiem("https://www.youtube.com/watch?v=1", ten_mien=_YT,
                         phan_giai=lambda h: ["127.0.0.1"])


def test_khong_phan_giai_duoc_bi_chan():
    def _loi(host):
        raise OSError("no dns")
    with pytest.raises(UrlKhongAnToan):
        an_toan_url.kiem("https://www.youtube.com/watch?v=1", ten_mien=_YT, phan_giai=_loi)
