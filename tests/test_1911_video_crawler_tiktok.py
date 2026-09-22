"""TikTokAdapter (spec §11, §18, §21) — không bao giờ chạm mạng: YoutubeDL giả tiêm qua `ydl_factory`.

Nguồn characterization:
- yt-dlp 2026.03.17 `yt_dlp/extractor/tiktok.py`: `TikTokIE._VALID_URL`/`_TESTS` (:698, :701-…),
  `TikTokBaseIE._create_url` (:105-107 — URL chuẩn nội bộ yt-dlp dùng khi build entry từ id, placeholder
  `@_` khi không biết handle), `TikTokUserIE` (`IE_NAME='tiktok:user'`, `_VALID_URL` :999-1000),
  `TikTokCollectionIE` (`IE_NAME='tiktok:collection'`, `_VALID_URL` :1294-1295), `TikTokVMIE`
  (`IE_NAME='vm.tiktok'`, `_VALID_URL` :1492), `TikTokTagIE` (`IE_NAME='tiktok:tag'`, `_VALID_URL` :1266-1267).
  `_parse_aweme_video_web`/`_parse_aweme_video_app` đặt `http_headers={'Referer': webpage_url}` trên info
  của định dạng (:660) — bản này đã tự vá lỗi thiếu Referer donor gặp ở bản yt-dlp cũ hơn (Y:2053-2054).
- Donor `D:\\Viral\\resources\\app-src\\tai_ytdlp.py` (Y): `chuan_hoa_kenh_tiktok`/`chuan_hoa_link_tiktok`
  Y:382-405; search TikTok = trang hashtag `/tag/<kw>` cần cookie đăng nhập, Y:1541-1544; tải search trực
  tiếp KHÔNG hỗ trợ, Y:2181-2184; KHÔNG tự nhét cookie khi tải (gây 403), Y:1734-1741; ảnh slideshow không
  có video, Y:2387-2490.
"""
from __future__ import annotations

import re
import sys
import types

import pytest
import yt_dlp
from yt_dlp.utils import DownloadError

from apps.video_crawler.adapters.base import CrawlItem, LoiCao, YeuCauCao
from apps.video_crawler.adapters.tiktok import TikTokAdapter, chuan_hoa_kenh_tiktok, url_hashtag_tiktok


# ---------------------------------------------------------------- YoutubeDL giả (mẫu test_1903)
class FakeYDL:
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
    return YeuCauCao(nen_tang="tiktok", che_do=che_do, dau_vao=dau_vao, so_luong=n)


def _info(entries):
    return {"_type": "playlist", "entries": entries}


# ---------------------------------------------------------------- chuẩn hoá kênh / hashtag
@pytest.mark.parametrize("vao", [
    "@abc", "abc", "https://www.tiktok.com/@abc", "https://www.tiktok.com/@abc?lang=en",
    "www.tiktok.com/@abc",
])
def test_chuan_hoa_kenh_ve_url_chuan(vao):
    assert chuan_hoa_kenh_tiktok(vao) == "https://www.tiktok.com/@abc"


def test_chuan_hoa_kenh_rong():
    assert chuan_hoa_kenh_tiktok("") == ""
    assert chuan_hoa_kenh_tiktok(None) == ""


@pytest.mark.parametrize("kw,ra", [
    ("meo con", "meocon"),
    ("#meo con", "meocon"),
    ("#tag  ", "tag"),
])
def test_url_hashtag_bo_thang_va_bo_dau(kw, ra):
    assert url_hashtag_tiktok(kw) == f"https://www.tiktok.com/tag/{ra}"


def test_url_hashtag_khong_bo_dau_cach_dau_dong_truoc_dau_thang():
    """Port ĐÚNG thứ tự donor `kw.lstrip('#').replace(' ', '').strip()` (Y:1735): khoảng trắng ĐỨNG
    TRƯỚC '#' không bị `lstrip` (nó chỉ cắt '#' ở đầu chuỗi) — '#' còn sót lại bị url-quote."""
    assert url_hashtag_tiktok("  #tag  ") == "https://www.tiktok.com/tag/%23tag"


# ---------------------------------------------------------------- allowed_extractors (BLOCKER: tên giả)
def test_allowed_extractors_chi_tiktok_va_ton_tai_that():
    """Tên phải là IE_NAME thật (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929)."""
    from yt_dlp.extractor import gen_extractor_classes

    ten_that = {ie.IE_NAME.lower() for ie in gen_extractor_classes()}
    ae = TikTokAdapter.tuy_chon_goc()["allowed_extractors"]
    assert ae and "generic" not in ae and "default" not in ae and "all" not in ae
    for ten in ae:
        assert ten.replace("\\", "") in ten_that, ten


def test_youtubedl_that_chi_nap_extractor_tiktok():
    """Dựng YoutubeDL thật (không mạng) — allowed_extractors chỉ nạp lớp TikTok*, chặn generic."""
    with yt_dlp.YoutubeDL(TikTokAdapter.tuy_chon_goc()) as y:
        ten = set(y._ies)
    assert ten and "Generic" not in ten
    assert all(k.startswith("TikTok") for k in ten), ten


def test_mac_dinh_nap_yt_dlp_luc_can(monkeypatch):
    goi = []
    gia = types.ModuleType("yt_dlp")
    gia.YoutubeDL = lambda opts: goi.append(opts) or "ydl"
    monkeypatch.setitem(sys.modules, "yt_dlp", gia)
    a = TikTokAdapter()
    assert a.nen_tang == "tiktok"
    assert a._tao({"x": 1}) == "ydl" and goi == [{"x": 1}]


# ---------------------------------------------------------------- id / URL chuẩn (BLOCKER: URL bị sửa)
# id mẫu lấy từ `TikTokIE._TESTS` (tiktok.py:702, :731, :761, :811).
_ID_THAT = ["6748451240264420610", "6742501081818877190", "6984138651336838402", "7059698374567611694"]


@pytest.mark.parametrize("vid", _ID_THAT)
def test_id_hop_le_dung_voi_id_that(vid):
    assert TikTokAdapter().id_hop_le(vid)


@pytest.mark.parametrize("sai", ["", "abc123", "6748451240264420610x", "MS4wLjABAAAA", "12 34",
                                 "12\n34", None, 123])
def test_id_hop_le_sai(sai):
    assert not TikTokAdapter().id_hop_le(sai), sai


def test_url_video_khop_valid_url_extractor_va_id_placeholder():
    from yt_dlp.extractor.tiktok import TikTokIE

    a = TikTokAdapter()
    for vid in _ID_THAT:
        url = a.url_video(vid)
        assert url == f"https://www.tiktok.com/@_/video/{vid}"           # TikTokBaseIE._create_url (:105-107)
        m = re.fullmatch(TikTokIE._VALID_URL, url)
        assert m is not None and m.group("id") == vid


# ---------------------------------------------------------------- url_kham_pha từng chế độ
def test_url_kham_pha_link_giu_nguyen():
    a = TikTokAdapter()
    for url in ("https://www.tiktok.com/@nguoidung/video/6748451240264420610",
                "https://vm.tiktok.com/ZTR45GpSF/"):
        assert a.url_kham_pha("link", url, 1) == url


def test_url_kham_pha_kenh_chuan_hoa():
    a = TikTokAdapter()
    assert a.url_kham_pha("kenh", "@abc", 3) == "https://www.tiktok.com/@abc"


def test_url_kham_pha_bo_giu_nguyen_url_collection():
    a = TikTokAdapter()
    url = "https://www.tiktok.com/@imanoreotwe/collection/count-test-7371330159376370462"
    assert a.url_kham_pha("bo", url, 5) == url


def test_url_kham_pha_tu_khoa_dung_trang_hashtag():
    a = TikTokAdapter()
    assert a.url_kham_pha("tu_khoa", "meo con", 5) == "https://www.tiktok.com/tag/meocon"


# ---------------------------------------------------------------- khám phá (kham_pha -> CrawlItem)
def test_kham_pha_tu_khoa_dung_tag():
    nha = Nha(info=_info([{"id": "6748451240264420610"}]))
    TikTokAdapter(nha).kham_pha(_yc("tu_khoa", "meo con", 7), bao_tien_do=_khong_bao)
    y = nha.tao[0]
    assert y.urls == [("https://www.tiktok.com/tag/meocon", False)]
    assert y.params["extract_flat"] == "in_playlist"
    assert y.params["skip_download"] is True
    assert y.params["playlistend"] == 7


def test_kham_pha_kenh_chuan_hoa_va_playlistend():
    nha = Nha(info=_info([]))
    TikTokAdapter(nha).kham_pha(_yc("kenh", "@abc", 3), bao_tien_do=_khong_bao)
    y = nha.tao[0]
    assert y.urls == [("https://www.tiktok.com/@abc", False)]
    assert y.params["playlistend"] == 3


def test_kham_pha_bo_dung_url_collection():
    url = "https://www.tiktok.com/@imanoreotwe/collection/count-test-7371330159376370462"
    nha = Nha(info=_info([]))
    TikTokAdapter(nha).kham_pha(_yc("bo", url, 4), bao_tien_do=_khong_bao)
    y = nha.tao[0]
    assert y.urls == [(url, False)]
    assert y.params["playlistend"] == 4


def test_kham_pha_link_tra_mot_muc():
    url = "https://www.tiktok.com/@nguoidung/video/6748451240264420610"
    nha = Nha(info={"id": "6748451240264420610", "title": "T", "uploader": "U", "duration": 12.7})
    ra = TikTokAdapter(nha).kham_pha(_yc("link", url, 5), bao_tien_do=_khong_bao)
    assert nha.tao[0].urls == [(url, False)]
    assert nha.tao[0].params["noplaylist"] is True
    assert ra == [CrawlItem(nen_tang="tiktok", id="6748451240264420610",
                            url="https://www.tiktok.com/@_/video/6748451240264420610",
                            tieu_de="T", tac_gia="U", thoi_luong_s=12, anh_bia="")]


def test_kham_pha_anh_xa_muc():
    nha = Nha(info=_info([
        {"id": "6748451240264420610", "title": "A", "channel": "Kenh", "uploader": "U", "duration": 61,
         "thumbnail": "https://p16.tiktokcdn.com/a.jpg"},
        {"id": "6742501081818877190", "title": "B", "uploader": "U2", "duration": None,
         "thumbnails": [{"url": "https://t/1.jpg"}, {"url": "https://t/2.jpg"}]},
    ]))
    ra = TikTokAdapter(nha).kham_pha(_yc("tu_khoa", "x", 5), bao_tien_do=_khong_bao)
    assert ra == [
        CrawlItem("tiktok", "6748451240264420610", "https://www.tiktok.com/@_/video/6748451240264420610",
                  "A", "Kenh", 61, "https://p16.tiktokcdn.com/a.jpg"),
        CrawlItem("tiktok", "6742501081818877190", "https://www.tiktok.com/@_/video/6742501081818877190",
                  "B", "U2", None, "https://t/2.jpg"),
    ]


def test_kham_pha_bo_muc_khong_id_va_cat_n():
    nha = Nha(info=_info([None, {"title": "khong id"}, {"id": "abc"}, {"id": _ID_THAT[0]}, {"id": _ID_THAT[1]},
                          {"id": _ID_THAT[2]}]))
    ra = TikTokAdapter(nha).kham_pha(_yc("kenh", "@abc", 2), bao_tien_do=_khong_bao)
    assert [m.id for m in ra] == [_ID_THAT[0], _ID_THAT[1]]   # id sai dạng bị bỏ ở khâu khám phá


def test_kham_pha_download_error_duoc_phan_loai():
    nha = Nha(loi=DownloadError("ERROR: [TikTok] x: Unsupported URL"))
    with pytest.raises(LoiCao) as e:
        TikTokAdapter(nha).kham_pha(_yc("link", "x"), bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro" and e.value.tam_thoi is False


# ---------------------------------------------------------------- tải: từ chối URL không chuẩn
@pytest.mark.parametrize("item", [
    CrawlItem("tiktok", "6748451240264420610", "https://www.tiktok.com/@ai_do/video/6748451240264420610"),
    CrawlItem("tiktok", "6748451240264420610", "https://www.tiktok.com/@_/video/6748451240264420610?lang=en"),
    CrawlItem("tiktok", "6748451240264420610", "http://www.tiktok.com/@_/video/6748451240264420610"),
    CrawlItem("tiktok", "6748451240264420610", "https://www.tiktok.com/@_/video/6742501081818877190"),
    CrawlItem("tiktok", "6748451240264420610", "https://www.tiktok.com/@abc/collection/x-6748451240264420610"),
    CrawlItem("tiktok", "khong_phai_so", "https://www.tiktok.com/@_/video/khong_phai_so"),
])
def test_tai_tu_choi_url_khong_chuan(tmp_path, item):
    nha = Nha()
    with pytest.raises(LoiCao) as e:
        TikTokAdapter(nha).tai(item, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro" and e.value.tam_thoi is False
    assert nha.tao == []          # không dựng YoutubeDL, không chạm mạng
