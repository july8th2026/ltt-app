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
    """Nền chỉ bật khi có adapter + test giả + smoke mạng thật (SO_LOI.md, 22/09). Thứ tự registry giữ nguyên.
    rednote: yt-dlp chưa hỗ trợ (yt-dlp/yt-dlp#16519). kuaishou, honggo: không có extractor."""
    ids = [n.id for n in nen_tang.cac_nen_bat()]
    assert ids == ["douyin", "bilibili_tv", "bilibili", "xiaohongshu", "weibo", "tiktok", "youtube",
                   "facebook", "instagram", "twitter"]


# Chế độ theo GIAO donor ∩ extractor yt-dlp thật (báo cáo từng làn); chế độ cần phiên theo smoke thật 22/09.
_CHE_DO = {
    "youtube": ({"tu_khoa", "link", "kenh", "bo"}, set()),
    "tiktok": ({"tu_khoa", "link", "kenh", "bo"}, {"tu_khoa"}),        # donor Y:1541-1544
    "facebook": ({"link"}, set()),
    "twitter": ({"link"}, set()),
    "weibo": ({"link", "kenh"}, set()),
    "bilibili_tv": ({"link"}, set()),
    "bilibili": ({"tu_khoa", "link", "kenh", "bo"}, {"tu_khoa", "link", "kenh", "bo"}),   # smoke: HTTP 412 ẩn danh
    "instagram": ({"link"}, {"link"}),                                  # smoke: "login required"
    # W1 (22/09): tìm + kênh qua client web; smoke ẩn danh: Douyin 2483 "cần đăng nhập", XHS -101.
    "douyin": ({"tu_khoa", "link", "kenh"}, {"tu_khoa", "link", "kenh"}),
    "xiaohongshu": ({"tu_khoa", "link", "kenh"}, {"tu_khoa", "kenh"}),
}


@pytest.mark.parametrize("nen", sorted(_CHE_DO))
def test_che_do_moi_nen_dung_bang_chung(nen):
    n = nen_tang.lay(nen)
    che_do, can_phien = _CHE_DO[nen]
    assert n.che_do == frozenset(che_do)
    assert n.che_do_can_dang_nhap == frozenset(can_phien)
    assert n.che_do_can_dang_nhap <= n.che_do
    if n.che_do_can_dang_nhap:
        assert n.cookie_dang_nhap, "nền cần phiên phải khai tên cookie xác thực"


@pytest.mark.parametrize("nen", [n.id for n in nen_tang.cac_nen_bat()])
def test_moi_nen_bat_co_adapter_that(nen):
    from apps.video_crawler import adapters
    ad = adapters.tao(nen)
    assert ad.nen_tang == nen


def test_tiktok_khong_gui_cookie_khi_tai():
    """Donor Y:1734-1741: cookie đăng nhập làm TikTok trả 403 khi TẢI."""
    from apps.video_crawler import adapters
    assert adapters.tao("tiktok").cookie_khi_tai is False


def test_nen_chua_bat_hoac_la_bi_tu_choi_co_ten():
    with pytest.raises(nen_tang.NenKhongHopLe):
        nen_tang.lay_nen_bat("kuaishou")
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


# ── function parity, không bug parity: donor so chuỗi con trên CẢ URL (regex `_LINK_DOM`) ──────────
# ⇒ `netflix.com` khớp `x\.com` thành Twitter, `evil.io/?u=youtube.com` thành YouTube. LTT so theo HOSTNAME.

@pytest.mark.parametrize("url,nen", [
    ("https://netflix.com/title/1", None),
    ("https://evil.io/?u=youtube.com", None),
    ("https://www.youtube.com.evil.io/watch?v=1", None),
    ("v.douyin.com/iABCdef/", "douyin"),                  # không scheme vẫn nhận
    ("youtube.com/@abc", "youtube"),
])
def test_nhan_dien_theo_hostname_khong_theo_chuoi_con(url, nen):
    assert nen_tang.nhan_dien(url) == nen
