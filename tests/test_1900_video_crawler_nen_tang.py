"""
video_crawler — registry nền tảng + nhận diện link (characterization theo donor Viral @ 368f8be).

Nguồn hành vi (chỉ đọc):
  _LINK_DOM / _doanTuLink   D:\\Viral\\resources\\app-src\\web\\index.html:16748-16798

Mỗi ca dưới đây là HÀNH VI DONOR, không phải hành vi "vì mã mới làm thế". Tên chế độ đổi sang tiếng Việt
theo registry LTT: search→tu_khoa, detail→link, creator→kenh, chase→bo.
"""
from __future__ import annotations

import pytest

from apps.video_crawler import nen_tang


# ── registry: một nguồn chân lý ─────────────────────────────────────────────

def test_registry_co_youtube_bat_voi_du_bon_che_do():
    yt = nen_tang.lay("youtube")
    assert yt.bat is True
    assert yt.che_do == frozenset({"tu_khoa", "link", "kenh", "bo"})
    assert yt.can_dang_nhap is False
    assert yt.xem_truoc is True


def test_chi_nen_da_bat_moi_duoc_liet_ke_cho_giao_dien():
    ids = [n.id for n in nen_tang.cac_nen_bat()]
    assert ids == ["youtube"]            # release 1: chỉ nền có adapter + test


def test_nen_chua_bat_hoac_la_bi_tu_choi_co_ten():
    with pytest.raises(nen_tang.NenKhongHopLe):
        nen_tang.lay_nen_bat("douyin")
    with pytest.raises(nen_tang.NenKhongHopLe):
        nen_tang.lay_nen_bat("khong_co")


# ── nhận diện nền theo domain (_LINK_DOM H:16748) ──────────────────────────

@pytest.mark.parametrize("url,nen", [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
    ("https://youtu.be/dQw4w9WgXcQ", "youtube"),
    ("https://m.youtube.com/@abc", "youtube"),
    ("https://www.douyin.com/video/7300000000000000000", "douyin"),
    ("https://v.douyin.com/iABCdef/", "douyin"),
    ("https://www.bilibili.tv/en/video/2041234567", "bilibili_tv"),
    ("https://www.bilibili.com/video/BV1xx411c7mD", "bilibili"),
    ("https://b23.tv/abcd123", "bilibili"),
    ("https://www.tiktok.com/@u/video/1", "tiktok"),
    ("https://fb.watch/abc/", "facebook"),
    ("https://x.com/u/status/1", "twitter"),
    ("https://example.com/video/1", None),
])
def test_nhan_dien_nen_theo_ten_mien(url, nen):
    assert nen_tang.nhan_dien(url) == nen


# ── đoán chế độ từ link (_doanTuLink H:16763-16798) ────────────────────────

@pytest.mark.parametrize("url,che_do", [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "link"),
    ("https://youtu.be/dQw4w9WgXcQ", "link"),
    ("https://www.youtube.com/shorts/abcDEF123", "link"),
    ("https://www.youtube.com/playlist?list=PL123", "bo"),
    ("https://www.youtube.com/watch?v=abc&list=PL123", "bo"),     # list= xét TRƯỚC dạng bài lẻ
    # Donor KHÔNG nhận `search_query=` (regex chỉ có [?&]q= / [?&]keyword=) ⇒ không đoán được chế độ.
    ("https://www.youtube.com/results?search_query=meo", ""),
    ("https://www.youtube.com/@ten/videos", "kenh"),               # tab kênh, không phải 1 video
    ("https://www.youtube.com/@ten", "kenh"),
    ("https://www.youtube.com/channel/UC123", "kenh"),
    ("https://www.douyin.com/search/meo?modal_id=7300000000000000000", "link"),  # modal_id thắng /search/
    ("https://www.douyin.com/search/meo", "tu_khoa"),
    ("https://www.facebook.com/TenTrang/videos", "kenh"),
    ("https://www.facebook.com/TenTrang", "kenh"),                 # fb còn lại ⇒ kênh
    ("https://www.tiktok.com/explore", ""),                         # /explore cần ≥ 6 ký tự id
    ("https://www.bilibili.tv/en/video/2041234567", "link"),        # bilitv ép link
])
def test_doan_che_do_tu_link(url, che_do):
    assert nen_tang.doan_tu_link(url).che_do == che_do


def test_doan_tu_link_nen_la_tra_none():
    assert nen_tang.doan_tu_link("https://example.com/watch?v=1") is None
    assert nen_tang.doan_tu_link("   ") is None
