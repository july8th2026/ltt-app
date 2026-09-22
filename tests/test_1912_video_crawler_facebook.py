"""FacebookAdapter (spec §11, §18, §21) — không bao giờ chạm mạng: YoutubeDL giả được tiêm qua `ydl_factory`.

Nguồn characterization: docstring `apps/video_crawler/adapters/facebook.py` (donor `Y`, PLATFORM_MATRIX
dòng `fb`, yt-dlp `extractor/facebook.py`). Mẫu id hợp lệ/không hợp lệ lấy từ `_TESTS` của `FacebookIE`/
`FacebookReelIE` (yt-dlp 2026.03.17 đã cài).
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
import yt_dlp
from yt_dlp.extractor.facebook import FacebookIE, FacebookReelIE
from yt_dlp.utils import DownloadCancelled, DownloadError

from apps.video_crawler.adapters.base import CrawlItem, LoiCao, TepTai, YeuCauCao
from apps.video_crawler.adapters.facebook import EXTRACTOR_CHO_PHEP, FacebookAdapter


# ---------------------------------------------------------------- YoutubeDL giả (như test youtube)
class FakeYDL:
    def __init__(self, opts, *, info=None, loi=None, kich_ban=None):
        self.params = opts
        self.info = info
        self.loi = loi
        self.kich_ban = kich_ban
        self.urls: list = []
        self.thay: list = []

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
        try:
            if self.kich_ban:
                self.kich_ban(self)
        except DownloadCancelled as e:
            self.thay.append(e)
            raise
        except Exception as e:  # noqa: BLE001 — mô phỏng yt-dlp nuốt lỗi hook
            self.thay.append(e)
        return 0

    def hook(self, d):
        for h in self.params.get("progress_hooks", []):
            h(d)

    def pp_hook(self, d):
        for h in self.params.get("postprocessor_hooks", []):
            h(d)


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


def _yc(che_do, dau_vao, n=1):
    return YeuCauCao(nen_tang="facebook", che_do=che_do, dau_vao=dau_vao, so_luong=n)


# ---------------------------------------------------------------- allowed_extractors thật
def test_allowed_extractors_chi_facebook_va_ton_tai_that():
    """Tên phải là IE_NAME thật (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929)."""
    from yt_dlp.extractor import gen_extractor_classes

    ten_that = {ie.IE_NAME.lower() for ie in gen_extractor_classes()}
    ae = FacebookAdapter.tuy_chon_goc()["allowed_extractors"]
    assert ae and "generic" not in ae and "default" not in ae and "all" not in ae
    assert set(ae) == {"facebook", "facebook:reel"}
    for ten in ae:
        assert ten.replace("\\", "") in ten_that, ten


def test_khong_nhan_plugin_va_redirect_ngoai_giao_donor():
    """Ngoài GIAO donor∩yt-dlp (docstring module) — dù hai extractor này thật sự tồn tại trong yt-dlp."""
    assert "facebookpluginsvideo" not in EXTRACTOR_CHO_PHEP
    assert "facebookredirecturl" not in EXTRACTOR_CHO_PHEP


def test_youtubedl_that_chi_nap_extractor_facebook():
    """Dựng YoutubeDL thật (không mạng, curl_cffi đã cài nên impersonate không raise) — allowed_extractors
    chặn Generic/FacebookAds/FacebookPluginsVideo/FacebookRedirectURL."""
    with yt_dlp.YoutubeDL(FacebookAdapter.tuy_chon_goc()) as y:
        ten = set(y._ies)
    assert ten and "Generic" not in ten
    assert ten == {"Facebook", "FacebookReel"}, ten


def test_impersonate_bat():
    o = FacebookAdapter.tuy_chon_goc()
    assert "impersonate" in o          # Y:2126-2135 — không thì "Cannot parse data"


def test_mac_dinh_nap_yt_dlp_luc_can(monkeypatch):
    goi = []
    gia = types.ModuleType("yt_dlp")
    gia.YoutubeDL = lambda opts: goi.append(opts) or "ydl"
    monkeypatch.setitem(sys.modules, "yt_dlp", gia)
    a = FacebookAdapter()
    assert a.nen_tang == "facebook"
    assert a._tao({"x": 1}) == "ydl" and goi == [{"x": 1}]


# ---------------------------------------------------------------- id_hop_le / url_video (BLOCKER: URL sửa)
# id SỐ ẩn danh thật từ FacebookIE._TESTS (không 'skip': 'Requires logging in'), + FacebookReelIE.
_ID_HOP_LE = ["3676516585958356", "274175099429670", "10155529876156509", "359649331226507",
              "106560053808006", "6968553779868435", "270103405756416", "1195289147628387"]
# id KHÔNG hợp lệ theo id_hop_le của adapter này (dù _VALID_URL gốc của FacebookIE vẫn nhận `pfbid...`).
_ID_KHONG_HOP_LE = [
    "", None, "abc", "1234",  # <5 số
    "pfbid028xue38TBXRyNbiqBSV2LFs3QK3yopvKjupbqFoL6U9SKbx4p2SMdJjQSBvnjsHGWl",  # bài viết, cần đăng nhập
    "10153807558977570 ", " 10153807558977570", "1015380755-8977570", "12345\n",
]


@pytest.mark.parametrize("vid", _ID_HOP_LE)
def test_id_hop_le_id_so_tu_TESTS_facebook(vid):
    assert FacebookAdapter().id_hop_le(vid)


@pytest.mark.parametrize("vid", _ID_KHONG_HOP_LE)
def test_id_khong_hop_le(vid):
    assert not FacebookAdapter().id_hop_le(vid)


@pytest.mark.parametrize("vid", _ID_HOP_LE)
def test_url_video_khop_valid_url_facebookie_that(vid):
    """url_video phải là URL mà chính `FacebookIE` (yt-dlp thật) coi là hợp lệ — bằng chứng docstring
    module: `_TESTS` có `watch/?v=647537299265662` KHÔNG `skip`, và `FacebookReelIE._real_extract`
    (`:982-984`) tự dựng lại `watch/?v=<id>` cho reel."""
    a = FacebookAdapter()
    url = a.url_video(vid)
    assert url == f"https://www.facebook.com/watch/?v={vid}"
    assert FacebookIE.suitable(url)


def test_url_video_khong_phai_dang_reel():
    """FacebookReelIE không khớp `watch/?v=` — chủ ý: mọi id (video hay reel) đều quy về MỘT dạng chính
    tắc `watch/?v=<id>` (chính yt-dlp cũng làm vậy khi xử lý reel, xem docstring module)."""
    a = FacebookAdapter()
    assert not FacebookReelIE.suitable(a.url_video("1195289147628387"))


# ---------------------------------------------------------------- url_kham_pha / chế độ
def test_url_kham_pha_link_di_thang_khong_doi():
    a = FacebookAdapter()
    url = "https://www.facebook.com/radiokicksfm/videos/3676516585958356/"
    assert a.url_kham_pha("link", url, 1) == url


@pytest.mark.parametrize("che_do", ["tu_khoa", "kenh", "bo"])
def test_url_kham_pha_che_do_khac_chua_ho_tro(che_do):
    """Facebook: chỉ 'link' — search/collection donor không có; kênh cần Playwright+login (docstring)."""
    a = FacebookAdapter()
    with pytest.raises(NotImplementedError):
        a.url_kham_pha(che_do, "x", 5)


# ---------------------------------------------------------------- khám phá (link: một mục, không playlist)
def test_kham_pha_link_tra_mot_muc():
    url = "https://www.facebook.com/watch/?v=647537299265662"
    nha = Nha(info={"id": "647537299265662", "title": "T", "uploader": "U", "duration": 12.7})
    ra = FacebookAdapter(nha).kham_pha(_yc("link", url), bao_tien_do=_khong_bao)
    y = nha.tao[0]
    assert y.urls == [(url, False)]
    assert y.params["noplaylist"] is True
    assert y.params["extract_flat"] == "in_playlist"
    assert ra == [CrawlItem(nen_tang="facebook", id="647537299265662",
                             url="https://www.facebook.com/watch/?v=647537299265662",
                             tieu_de="T", tac_gia="U", thoi_luong_s=12, anh_bia="")]


def test_kham_pha_link_id_khong_hop_le_bi_bo():
    """id trích ra không phải dạng số hợp lệ (vd bài viết pfbid không đăng nhập ra được) ⇒ khám phá rỗng,
    không ném lỗi (đối xứng với youtube `_kham_pha_bo_muc_khong_id_va_cat_n`)."""
    url = "https://www.facebook.com/attn/posts/pfbid0j1Czf2gGDVqeQ8KiMLFm3pWN8GxsQmeRrVhimWDzMuKQoR8r4b1knNsejELmUgyhl"
    nha = Nha(info={"id": "pfbid0j1Czf2gGDVqeQ8KiMLFm3pWN8GxsQmeRrVhimWDzMuKQoR8r4b1knNsejELmUgyhl"})
    ra = FacebookAdapter(nha).kham_pha(_yc("link", url), bao_tien_do=_khong_bao)
    assert ra == []


def test_kham_pha_download_error_duoc_phan_loai():
    nha = Nha(loi=DownloadError("ERROR: [facebook] 123: Cannot parse data"))
    with pytest.raises(LoiCao):
        FacebookAdapter(nha).kham_pha(_yc("link", "https://www.facebook.com/watch/?v=123456"),
                                       bao_tien_do=_khong_bao)


# ---------------------------------------------------------------- tải
_ITEM = CrawlItem("facebook", "647537299265662", "https://www.facebook.com/watch/?v=647537299265662",
                   tieu_de='Mèo: "con"/<to>?*|')


def _ghi(p: Path, n=10) -> Path:
    p.write_bytes(b"x" * n)
    return p


def test_tai_dung_impersonate_va_tra_tep(tmp_path):
    that = tmp_path / "647537299265662.mp4"

    def kb(y):
        _ghi(that, 42)
        y.pp_hook({"status": "finished", "postprocessor": "MoveFiles", "info_dict": {"filepath": str(that)}})

    nha = Nha(kich_ban=kb)
    tep = FacebookAdapter(nha).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert tep == TepTai(duong_dan=that, kich_thuoc=42, ten_hien_thi="Mèo con to [647537299265662].mp4")
    y = nha.tao[0]
    assert y.urls == [(["https://www.facebook.com/watch/?v=647537299265662"], True)]
    assert "impersonate" in y.params


def test_tai_download_error_duoc_phan_loai(tmp_path):
    nha = Nha(loi=DownloadError("ERROR: [facebook] 647537299265662: Cannot parse data"))
    with pytest.raises(LoiCao):
        FacebookAdapter(nha).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)


@pytest.mark.parametrize("item", [
    CrawlItem("facebook", "647537299265662", "https://www.facebook.com/reel/647537299265662"),
    CrawlItem("facebook", "647537299265662", "https://www.facebook.com/somepage/videos/647537299265662/"),
    CrawlItem("facebook", "647537299265662", "http://www.facebook.com/watch/?v=647537299265662"),
    CrawlItem("facebook", "647537299265662", "https://www.facebook.com/watch/?v=647537299265662&extra=1"),
    CrawlItem("facebook", "pfbidABC123", "https://www.facebook.com/watch/?v=pfbidABC123"),
    CrawlItem("facebook", "1234", "https://www.facebook.com/watch/?v=1234"),
])
def test_tai_tu_choi_url_khong_chuan(tmp_path, item):
    nha = Nha()
    with pytest.raises(LoiCao) as e:
        FacebookAdapter(nha).tai(item, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro" and e.value.tam_thoi is False
    assert nha.tao == []          # không dựng YoutubeDL, không chạm mạng
