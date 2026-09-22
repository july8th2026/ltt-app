"""Phân loại lỗi yt-dlp của video_crawler (spec §19).

Ca characterization lấy từ donor:
- `D:\\Viral\\resources\\app-src\\web_app.py`:4926-4927 (yt_bot: "Sign in to confirm" / "not a bot"),
  4930-4931 (yt_403: "unable to download video data" / fragment + 403),
  4939-4940 ("Unsupported URL"), 4960-4963 (chi_la_anh: "No video formats found").
- `cutclipshort/adapters/downloader.py`:299-303 ("private"/"sign in" ⇒ riêng tư, "age" ⇒ giới hạn tuổi).
"""
from __future__ import annotations

import pytest

from apps.video_crawler.adapters.base import LoiCao
from apps.video_crawler.loi import phan_loai

CA = [
    # (thông điệp yt-dlp, mã, tam_thoi)
    ("ERROR: [youtube] abc: Sign in to confirm you're not a bot. Use --cookies-from-browser", "yt_bot", True),
    ("ERROR: [youtube] abc: Please confirm you are not a bot", "yt_bot", True),
    ("ERROR: unable to download video data: HTTP Error 403: Forbidden", "yt_403", True),
    ("ERROR: fragment 3 not found, HTTP Error 403", "yt_403", True),
    ("ERROR: HTTP Error 403: Forbidden", "yt_403", True),
    ("ERROR: Unsupported URL: https://example.com/x", "url_khong_ho_tro", False),
    ("ERROR: No suitable extractor (Generic) found for URL https://x.test", "url_khong_ho_tro", False),
    ("ERROR: [youtube] abc: No video formats found!", "chi_la_anh", False),
    ("ERROR: [youtube] abc: Private video. Sign in if you've been granted access to this video", "rieng_tu", False),
    ("ERROR: [youtube] abc: Join this channel to get access to members-only content like this video", "rieng_tu", False),
    ("ERROR: [youtube] abc: Sign in to confirm your age. This video may be inappropriate for some users.",
     "gioi_han_tuoi", False),
    ("ERROR: [youtube] abc: This video is age-restricted", "gioi_han_tuoi", False),
    ("ERROR: [youtube] abc: Video unavailable", "khong_ton_tai", False),
    ("ERROR: [youtube] abc: This video has been removed by the uploader", "khong_ton_tai", False),
    ("ERROR: HTTP Error 404: Not Found", "khong_ton_tai", False),
    ("ERROR: Unable to download webpage: The read operation timed out", "mang", True),
    ("ERROR: [WinError 10054] An existing connection was forcibly closed (connection reset)", "mang", True),
    ("ERROR: Unable to download webpage: <urlopen error [Errno 11001] getaddrinfo failed>", "mang", True),
    ("ERROR: something entirely new happened", "loi_khac", True),
    ("", "loi_khac", True),
]


@pytest.mark.parametrize("thong_diep,ma,tam_thoi", CA)
def test_phan_loai(thong_diep, ma, tam_thoi):
    loi = phan_loai(thong_diep)
    assert isinstance(loi, LoiCao)
    assert (loi.ma, loi.tam_thoi) == (ma, tam_thoi)


def test_bot_check_khong_bi_nham_la_rieng_tu():
    """Donor downloader.py:300 gộp "sign in" vào riêng tư — nhưng câu bot-check cũng có "Sign in"."""
    assert phan_loai("Sign in to confirm you're not a bot").ma == "yt_bot"


def test_tu_age_trong_webpage_khong_phai_gioi_han_tuoi():
    """Donor downloader.py:302 dùng `"age" in err` trần — "webpage"/"message" chứa "age". LTT siết lại."""
    assert phan_loai("ERROR: Unable to download webpage: something odd").ma != "gioi_han_tuoi"


def test_thong_diep_khach_khong_lo_url_hay_cookie():
    tho = "ERROR: Unsupported URL: https://secret.test/x?token=abc cookie=SID=xyz"
    loi = phan_loai(tho)
    assert loi.thong_diep and "http" not in loi.thong_diep
    assert "token" not in loi.thong_diep and "SID" not in loi.thong_diep
    for thong_diep, _, _ in CA:
        assert "http" not in phan_loai(thong_diep).thong_diep
