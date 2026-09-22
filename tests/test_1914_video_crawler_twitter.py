"""TwitterAdapter (spec §11, §18, §21) — chỉ chế độ "link" (một tweet). Không chạm mạng:
YoutubeDL giả được tiêm qua `ydl_factory`, như `tests/test_1903_video_crawler_youtube.py`.

Bằng chứng nguồn (yt-dlp 2026.03.17 đã cài, site-packages):
- Extractor Twitter/X đăng ký: `extractor/_extractors.py:2234-2240` — đúng 6 lớp
  `TwitterAmplifyIE, TwitterBroadcastIE, TwitterCardIE, TwitterIE, TwitterShortenerIE, TwitterSpacesIE`.
  Không có lớp nào liệt kê timeline người dùng (channel) ⇒ GIAO với donor (PLATFORM_MATRIX `tw` cột
  "channel" ✅ backend) là RỖNG ⇒ "kenh" không được hỗ trợ ở adapter này.
- `TwitterIE._VALID_URL` (`extractor/twitter.py:270`) khớp `.../status/<id_so>`, `i/web/status/<id_so>`,
  `i/status/<id_so>` (nhánh `[^/]+/status`, `[^/]+`="i") và cả domain `x.com` (`_BASE_REGEX` dòng 38:
  `(?:twitter|x)\\.com`).
- `TwitterIE._real_extract` (`extractor/twitter.py:1268-1346`) trích video/amplify tweet chuẩn TRỰC TIẾP
  trong lớp này (nhánh `amplify` gọi `_extract_formats_from_vmap_url` ngay tại chỗ) — không cần
  `TwitterAmplifyIE` (lớp đó chỉ khớp domain riêng `amp.twimg.com/v/<uuid>`, ngoài phạm vi "link" tweet).
- Donor `tai_ytdlp.py:2126-2135`: chỉ `impersonate=chrome` cho `fb`/`bili`/`bilitv` — KHÔNG cho `tw`.
- Donor PLATFORM_MATRIX dòng `tw`: search ❌, link ✅ (backend), "Theo bộ" ❌ ⇒ chỉ "link" còn lại.
"""
from __future__ import annotations

import re

import pytest
from yt_dlp.extractor.twitter import TwitterIE

from apps.video_crawler.adapters.base import CrawlItem, LoiCao, YeuCauCao
from apps.video_crawler.adapters.twitter import EXTRACTOR_CHO_PHEP, TwitterAdapter


class FakeYDL:
    """Bắt chước bề mặt YoutubeDL mà adapter dùng (như `test_1903`)."""

    def __init__(self, opts, *, info=None, loi=None):
        self.params = opts
        self.info = info
        self.loi = loi
        self.urls: list = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=True):
        self.urls.append((url, download))
        if self.loi:
            raise self.loi
        return self.info

    def download(self, urls):
        self.urls.append((list(urls), True))
        if self.loi:
            raise self.loi
        return 0


class Nha:
    def __init__(self, **kw):
        self.kw = kw
        self.tao: list[FakeYDL] = []

    def __call__(self, opts):
        y = FakeYDL(opts, **self.kw)
        self.tao.append(y)
        return y


def _khong_bao(pct, msg):
    pass


def _yc(che_do, dau_vao, n=5):
    return YeuCauCao(nen_tang="twitter", che_do=che_do, dau_vao=dau_vao, so_luong=n)


# ---------------------------------------------------------------- allowed_extractors thật
def test_allowed_extractors_ton_tai_that_va_khong_generic():
    from yt_dlp.extractor import gen_extractor_classes

    ten_that = {ie.IE_NAME.lower() for ie in gen_extractor_classes()}
    ae = TwitterAdapter.tuy_chon_goc()["allowed_extractors"]
    assert ae == list(EXTRACTOR_CHO_PHEP)
    assert ae and "generic" not in ae and "default" not in ae and "all" not in ae
    for ten in ae:
        assert ten in ten_that, ten


def test_allowed_extractors_chi_gom_twitter_khong_card_broadcast_spaces():
    """Đối chứng: card/broadcast/spaces/shortener/amplify KHÔNG được liệt — chỉ tweet video chuẩn."""
    assert EXTRACTOR_CHO_PHEP == ("twitter",)
    for bi_loai in ("twitter:card", "twitter:broadcast", "twitter:spaces",
                    "twitter:shortener", "twitter:amplify"):
        assert bi_loai not in EXTRACTOR_CHO_PHEP


def test_youtubedl_that_chi_nap_extractor_twitter():
    """Dựng YoutubeDL thật (không mạng) — allowed_extractors=("twitter",) chỉ nạp đúng TwitterIE."""
    import yt_dlp

    with yt_dlp.YoutubeDL(TwitterAdapter.tuy_chon_goc()) as y:
        ten = set(y._ies)
    assert ten == {"Twitter"}


def test_impersonate_tat_khac_facebook_bilibilitv():
    """Donor chỉ impersonate=chrome cho fb/bili/bilitv (Y:2126-2135) — KHÔNG cho tw."""
    assert TwitterAdapter.impersonate is False
    assert "impersonate" not in TwitterAdapter.tuy_chon_goc()


# ---------------------------------------------------------------- id_hop_le / url_video
def test_id_hop_le_chi_nhan_chuoi_so():
    a = TwitterAdapter()
    for dung in ("1", "643211870443208704", "852077943283097602", "1695424220702888009"):
        assert a.id_hop_le(dung), dung
    for sai in ("", "abc", "123abc", "-123", "1.5", "12 3", "12\n", None, 123, "643211870443208704/"):
        assert not a.id_hop_le(sai), sai


def test_url_video_dung_dang_chuan_va_khop_valid_url_extractor():
    a = TwitterAdapter()
    url = a.url_video("852077943283097602")
    assert url == "https://x.com/i/status/852077943283097602"
    assert re.fullmatch(TwitterIE._VALID_URL, url) is not None


def test_url_video_id_tu_test_that_cua_extractor_khop_valid_url():
    """Id mẫu lấy từ `TwitterIE._TESTS` — id thật của extractor, không phải id trong URL mẫu."""
    id_that = next(t["info_dict"]["id"] for t in TwitterIE._TESTS if isinstance(t.get("info_dict"), dict))
    a = TwitterAdapter()
    assert a.id_hop_le(id_that)
    assert re.fullmatch(TwitterIE._VALID_URL, a.url_video(id_that)) is not None


# ---------------------------------------------------------------- url_kham_pha
def test_url_kham_pha_link_tra_nguyen_dau_vao():
    a = TwitterAdapter()
    url = "https://x.com/i/status/852077943283097602"
    assert a.url_kham_pha("link", url, 1) == url


@pytest.mark.parametrize("che_do", ["tu_khoa", "kenh", "bo"])
def test_url_kham_pha_che_do_khong_ho_tro_bao_ro(che_do):
    """Chỉ "link" được hỗ trợ — registry phải chặn trước, nhưng adapter tự vệ nếu bị gọi sai."""
    with pytest.raises(NotImplementedError):
        TwitterAdapter().url_kham_pha(che_do, "x", 5)


# ---------------------------------------------------------------- khám phá (link, một mục)
def test_kham_pha_link_tra_mot_muc():
    url = "https://x.com/i/status/852077943283097602"
    nha = Nha(info={"id": "852077943283097602", "title": "T", "uploader": "U", "duration": 12.7})
    ra = TwitterAdapter(nha).kham_pha(_yc("link", url, 5), bao_tien_do=_khong_bao)
    assert nha.tao[0].urls == [(url, False)]
    assert nha.tao[0].params["noplaylist"] is True
    assert ra == [CrawlItem(nen_tang="twitter", id="852077943283097602",
                            url="https://x.com/i/status/852077943283097602",
                            tieu_de="T", tac_gia="U", thoi_luong_s=12, anh_bia="")]


def test_kham_pha_link_id_khong_hop_le_bi_bo():
    url = "https://x.com/i/status/khong-phai-so"
    nha = Nha(info={"id": "khong-phai-so", "title": "T"})
    ra = TwitterAdapter(nha).kham_pha(_yc("link", url, 1), bao_tien_do=_khong_bao)
    assert ra == []


# ---------------------------------------------------------------- tải
_ITEM = CrawlItem("twitter", "852077943283097602", "https://x.com/i/status/852077943283097602", tieu_de="T")


def _ghi(p, n=10):
    p.write_bytes(b"x" * n)
    return p


def test_tai_dung_url_chuan(tmp_path):
    nha = Nha()

    def factory(opts):
        y = FakeYDL(opts)
        nha.tao.append(y)
        _ghi(tmp_path / "852077943283097602.mp4")
        return y

    tep = TwitterAdapter(factory).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert nha.tao[0].urls == [(["https://x.com/i/status/852077943283097602"], True)]
    assert tep.ten_hien_thi == "T [852077943283097602].mp4"


@pytest.mark.parametrize("item", [
    CrawlItem("twitter", "852077943283097602", "https://twitter.com/user/status/852077943283097602"),
    CrawlItem("twitter", "852077943283097602", "https://x.com/i/status/852077943283097602?s=20"),
    CrawlItem("twitter", "852077943283097602", "http://x.com/i/status/852077943283097602"),
    CrawlItem("twitter", "852077943283097602", "https://x.com/i/status/khac0000000000001"),
    CrawlItem("twitter", "khong-so", "https://x.com/i/status/khong-so"),
])
def test_tai_tu_choi_url_khong_chuan(tmp_path, item):
    nha = Nha()
    with pytest.raises(LoiCao) as e:
        TwitterAdapter(nha).tai(item, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro" and e.value.tam_thoi is False
    assert nha.tao == []          # không dựng YoutubeDL, không chạm mạng


def test_id_la_id_tweet_khong_phai_id_media():
    """Smoke thật 22/09: TwitterIE trả `id` = id MEDIA (717462543795523584), `display_id` = id TWEET
    (719944021058060289). Dùng id media dựng `x.com/i/status/<id>` ⇒ tải hỏng. Mục phải mang id tweet."""
    from apps.video_crawler.adapters.twitter import TwitterAdapter
    ad = TwitterAdapter()
    item = ad._sang_item({"id": "717462543795523584", "display_id": "719944021058060289", "title": "T",
                          "webpage_url": "https://twitter.com/captainamerica/status/719944021058060289"})
    assert item.id == "719944021058060289"
    assert item.url == "https://x.com/i/status/719944021058060289"
