"""InstagramAdapter (spec §11, §18, §21) — không bao giờ chạm mạng: YoutubeDL giả tiêm qua `ydl_factory`
(dùng lại `FakeYDL`/`Nha` của `test_1903_video_crawler_youtube.py` — spec §11 chỉ một hợp đồng, không
cần bịa lại bộ giả).

Bằng chứng characterization:
- Donor `docs/migrations/video_crawler/PLATFORM_MATRIX.md` dòng `ig`: link ✅, kenh ✅ nhưng qua TRÌNH
  DUYỆT (`_ig_liet_ke_kenh`, Y:1017-1150) — không qua yt-dlp; tu_khoa/bo ❌; ảnh ⇒ "No video formats
  found" (không phải lỗi); login cookie `sessionid`/`ds_user_id` (Y:1490-1528); `chuan_hoa_user` cắt
  `?igsi=`/`?s=` (Y:205-228).
- yt-dlp `yt_dlp/extractor/instagram.py` (2026.03.17, đã cài): `InstagramIE` IE_NAME `Instagram` (:224,
  `_VALID_URL`), `_ENCODING_CHARS` (:26), id dài hơn cho bài riêng tư (:443-447); `InstagramUserIE`
  IE_NAME `instagram:user`, `_WORKING = False` (:606-610) — hỏng cứng, xác nhận bởi
  yt-dlp/yt-dlp#4394 (mở 2022, còn mở) và #17683 (báo lại 2026.08.19, đóng `not_planned`).
- `apps/video_crawler/loi.py` đã có mã `chi_la_anh` cho tín hiệu "no video formats found" — không sửa.
"""
from __future__ import annotations

import pytest
from yt_dlp.utils import DownloadError

from apps.video_crawler.adapters.base import CrawlItem, LoiCao, YeuCauCao
from apps.video_crawler.adapters.instagram import (
    EXTRACTOR_CHO_PHEP,
    InstagramAdapter,
    cat_bo_query,
)
from tests.test_1903_video_crawler_youtube import Nha


def _khong_bao(pct, msg):
    pass


def _yc(che_do, dau_vao, n=5):
    return YeuCauCao(nen_tang="instagram", che_do=che_do, dau_vao=dau_vao, so_luong=n)


# ---------------------------------------------------------------- extractor thật
def test_allowed_extractors_chi_instagram_va_ton_tai_that():
    """Tên phải là IE_NAME thật (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929)."""
    from yt_dlp.extractor import gen_extractor_classes

    ten_that = {ie.IE_NAME.lower() for ie in gen_extractor_classes()}
    ae = InstagramAdapter.tuy_chon_goc()["allowed_extractors"]
    assert ae == list(EXTRACTOR_CHO_PHEP) == ["instagram"]
    assert "generic" not in ae and "default" not in ae
    assert "instagram:user" not in ae and "instagram:tag" not in ae and "instagram:story" not in ae
    for ten in ae:
        assert ten in ten_that, ten


def test_youtubedl_that_chi_nap_extractor_instagram():
    import yt_dlp

    with yt_dlp.YoutubeDL(InstagramAdapter.tuy_chon_goc()) as y:
        ten = set(y._ies)
    assert ten == {"Instagram"}, ten


def test_instagram_user_van_dang_hong_cung():
    """Ghim bằng chứng đóng cửa `kenh`: nếu yt-dlp sửa lại `instagram:user`, phép này đỏ và phải xét lại
    phạm vi hỗ trợ (không phải chỉ có bài lẻ nữa)."""
    from yt_dlp.extractor.instagram import InstagramUserIE

    assert InstagramUserIE._WORKING is False


def test_khong_impersonate():
    assert "impersonate" not in InstagramAdapter.tuy_chon_goc()


# ---------------------------------------------------------------- id / url chuẩn
_ID_MAU_HOP_LE = (
    "aye83DjauH", "Chunk8-jurw", "BQ0eAlwhDrw", "BQ0dSaohpPW", "BQ0dTpOhuHT",
    "BQ0dT7RBFeF", "BkfuX9UB-eK", "CDUMkliABpa", "CWqAgUZgCku", "Cop84x6u7CP",
)


@pytest.mark.parametrize("vid", _ID_MAU_HOP_LE)
def test_id_hop_le_dung_id_mau_tu_extractor_tests(vid):
    """Id mẫu lấy từ `InstagramIE._TESTS` (yt_dlp/extractor/instagram.py:226-351)."""
    assert InstagramAdapter().id_hop_le(vid)


@pytest.mark.parametrize("sai", ["", "ab", "a/b", "a?b", "a#b", "a b", None, 123, "a" * 41])
def test_id_hop_le_sai(sai):
    assert not InstagramAdapter().id_hop_le(sai)


@pytest.mark.parametrize("vid", _ID_MAU_HOP_LE)
def test_url_video_khop_valid_url_extractor(vid):
    """URL dựng lại phải khớp `InstagramIE._VALID_URL` và trả về đúng id (yt_dlp/extractor/instagram.py:224)."""
    from yt_dlp.extractor.instagram import InstagramIE

    url = InstagramAdapter().url_video(vid)
    assert url == f"https://www.instagram.com/p/{vid}/"
    m = InstagramIE._match_valid_url(url)
    assert m is not None and m.group("id") == vid


# ---------------------------------------------------------------- cắt query rác
@pytest.mark.parametrize("vao,ra", [
    ("https://www.instagram.com/reel/Chunk8-jurw/?igsi=abc123", "https://www.instagram.com/reel/Chunk8-jurw/"),
    ("https://www.instagram.com/p/BkfuX9UB-eK/?s=09", "https://www.instagram.com/p/BkfuX9UB-eK/"),
    ("https://www.instagram.com/p/BkfuX9UB-eK/#comments", "https://www.instagram.com/p/BkfuX9UB-eK/"),
    ("https://www.instagram.com/p/BkfuX9UB-eK/", "https://www.instagram.com/p/BkfuX9UB-eK/"),
    ("", ""),
])
def test_cat_bo_query(vao, ra):
    assert cat_bo_query(vao) == ra


def test_url_kham_pha_link_cat_query():
    url = "https://www.instagram.com/reel/Chunk8-jurw/?igsi=xyz"
    assert InstagramAdapter().url_kham_pha("link", url, 1) == "https://www.instagram.com/reel/Chunk8-jurw/"


# ---------------------------------------------------------------- khám phá
def test_kham_pha_link_tra_mot_muc():
    url_vao = "https://www.instagram.com/reel/Chunk8-jurw/?igsi=xyz"
    url_sach = "https://www.instagram.com/reel/Chunk8-jurw/"
    nha = Nha(info={"id": "Chunk8-jurw", "title": "T", "channel": "instagram", "duration": 5.016})
    ra = InstagramAdapter(nha).kham_pha(_yc("link", url_vao, 5), bao_tien_do=_khong_bao)
    y = nha.tao[0]
    assert y.urls == [(url_sach, False)]
    assert y.params["noplaylist"] is True
    assert ra == [CrawlItem(nen_tang="instagram", id="Chunk8-jurw",
                            url="https://www.instagram.com/p/Chunk8-jurw/",
                            tieu_de="T", tac_gia="instagram", thoi_luong_s=5, anh_bia="")]


def test_kham_pha_bo_muc_id_khong_hop_le():
    nha = Nha(info={"id": "a/b", "title": "x"})
    ra = InstagramAdapter(nha).kham_pha(_yc("link", "https://www.instagram.com/p/a%2Fb/", 1),
                                        bao_tien_do=_khong_bao)
    assert ra == []


def test_kham_pha_anh_khong_phai_loi_cung():
    """PLATFORM_MATRIX `ig`: bài chỉ ảnh ⇒ yt-dlp ném "No video formats found!" — mã `chi_la_anh`,
    tam_thoi=False (đã có sẵn trong `loi.py`, spec §19)."""
    nha = Nha(loi=DownloadError("ERROR: [Instagram] aye83DjauH: No video formats found!"))
    with pytest.raises(LoiCao) as e:
        InstagramAdapter(nha).kham_pha(_yc("link", "https://www.instagram.com/p/aye83DjauH/"),
                                       bao_tien_do=_khong_bao)
    assert e.value.ma == "chi_la_anh" and e.value.tam_thoi is False


# ---------------------------------------------------------------- tải
_ITEM = CrawlItem("instagram", "Chunk8-jurw", "https://www.instagram.com/p/Chunk8-jurw/", tieu_de="T")


@pytest.mark.parametrize("item", [
    CrawlItem("instagram", "Chunk8-jurw", "https://www.instagram.com/p/Chunk8-jurw"),        # thiếu "/"
    CrawlItem("instagram", "Chunk8-jurw", "https://www.instagram.com/reel/Chunk8-jurw/"),     # id đúng, url khác
    CrawlItem("instagram", "Chunk8-jurw", "https://www.instagram.com/p/khac-id-xxxx/"),
    CrawlItem("instagram", "Chunk8-jurw", "http://www.instagram.com/p/Chunk8-jurw/"),          # http, không https
    CrawlItem("instagram", "Chunk8-jurw", "https://www.instagram.com/"),                        # trang chủ/kênh
    CrawlItem("instagram", "a/b", "https://www.instagram.com/p/a/b/"),                          # id sai dạng
])
def test_tai_tu_choi_url_khong_chuan(tmp_path, item):
    nha = Nha()
    with pytest.raises(LoiCao) as e:
        InstagramAdapter(nha).tai(item, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro" and e.value.tam_thoi is False
    assert nha.tao == []          # không dựng YoutubeDL, không chạm mạng


def test_tai_url_chuan_duoc_chap_nhan(tmp_path):
    def kb(y):
        (tmp_path / "Chunk8-jurw.mp4").write_bytes(b"x" * 5)
        y.pp_hook({"status": "finished", "postprocessor": "MoveFiles",
                   "info_dict": {"filepath": str(tmp_path / "Chunk8-jurw.mp4")}})

    nha = Nha(kich_ban=kb)
    tep = InstagramAdapter(nha).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert tep.kich_thuoc == 5
    assert nha.tao[0].urls == [(["https://www.instagram.com/p/Chunk8-jurw/"], True)]
