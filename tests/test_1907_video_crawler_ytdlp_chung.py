"""Nền yt-dlp dùng chung của các adapter (`adapters/_ytdlp.py`) — spec §11, §18, §21. Không chạm mạng.

Nguồn yt-dlp 2026.03.17 đã đối chiếu:
- `match_filter` chữ ký `(info_dict, *, incomplete) -> Optional[str]`: YoutubeDL.py:453-463; gọi ở `_match_entry`
  :1586-1596 — mục phẳng của playlist với incomplete=True (:2121), mục đã chọn định dạng với incomplete=False (:3307).
- `live_status` ∈ {is_live, is_upcoming, post_live, was_live, not_live}; `is_live`/`was_live` suy ra: :2755-2772.
- `max_filesize`: HttpFD chỉ `to_screen("File is larger than max-filesize ...")` rồi `return False`
  (downloader/http.py:219-227) — không exception; `to_screen` đi vào `logger.debug` khi có logger (:992-996).
"""
from __future__ import annotations

import re
import threading
import time
from pathlib import Path

import pytest
import yt_dlp
from yt_dlp.utils import DownloadCancelled

from apps.video_crawler.adapters import _ytdlp
from apps.video_crawler.adapters._ytdlp import YtdlpAdapter
from apps.video_crawler.adapters.base import CrawlItem, LoiCao, YeuCauCao
from apps.video_crawler.adapters.youtube import YoutubeAdapter


class FakeYDL:
    def __init__(self, opts, *, info=None, kich_ban=None):
        self.params = opts
        self.info = info
        self.kich_ban = kich_ban
        self.urls: list = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=True):
        self.urls.append((url, download))
        if self.kich_ban:
            self.kich_ban(self)
        return self.info

    def download(self, urls):
        self.urls.append((list(urls), True))
        try:
            if self.kich_ban:
                self.kich_ban(self)
        except DownloadCancelled:
            raise
        except Exception:  # noqa: BLE001 — yt-dlp nuốt lỗi hook
            pass
        return 0

    def hook(self, d):
        for h in self.params.get("progress_hooks", []):
            h(d)


class Nha:
    def __init__(self, **kw):
        self.kw = kw
        self.tao: list[FakeYDL] = []

    def __call__(self, opts):
        y = FakeYDL(opts, **self.kw)
        self.tao.append(y)
        return y


class NenGia(YtdlpAdapter):
    """Lớp con tối thiểu — đúng những gì làn bilibili/TikTok/Facebook phải cấp."""
    nen_tang = "gia"
    allowed_extractors = ("gia",)
    extractor_args = {"gia": {"k": ["v"]}}
    ie_key_video = ("Gia",)

    def url_video(self, id: str) -> str:
        return f"https://gia.test/v/{id}"

    def id_hop_le(self, id) -> bool:
        return isinstance(id, str) and re.fullmatch(r"[0-9]{5}", id) is not None

    def url_kham_pha(self, che_do: str, dau_vao: str, n: int) -> str:
        return f"giasearch{n}:{dau_vao}" if che_do == "tu_khoa" else dau_vao


class NenGiaGiaLap(NenGia):
    impersonate = True


_ITEM = CrawlItem("gia", "12345", "https://gia.test/v/12345", tieu_de="T")


def _khong_bao(p, m):
    pass


def _ghi(p: Path) -> Path:
    p.write_bytes(b"x" * 10)
    return p


@pytest.fixture
def nhip_nhanh(monkeypatch):
    monkeypatch.setattr(_ytdlp, "CHU_KY_NHIP", 0.05)


def _khong_con_nhip():
    return not [t for t in threading.enumerate() if t.name == _ytdlp.TEN_LUONG_NHIP]


# ---------------------------------------------------------------- lớp con cấp gì
def test_tuy_chon_lay_tu_lop_con(tmp_path):
    o = NenGia.tuy_chon_goc(tmp_path)
    assert o["allowed_extractors"] == ["gia"]
    assert o["extractor_args"] == {"gia": {"k": ["v"]}}
    assert o["ignoreerrors"] is False
    assert "impersonate" not in o
    assert o["outtmpl"] == str(tmp_path / "%(id)s.%(ext)s") and o["noplaylist"] is True


def test_impersonate_bat_theo_co_lop_con():
    from yt_dlp.networking.impersonate import ImpersonateTarget

    assert isinstance(NenGiaGiaLap.tuy_chon_goc()["impersonate"], ImpersonateTarget)


def test_lop_goc_chua_cai_dat_thi_bao_ro():
    with pytest.raises(NotImplementedError):
        YtdlpAdapter().url_video("x")


def test_kham_pha_dung_url_builder_va_url_chuan_cua_lop_con():
    nha = Nha(info={"entries": [{"id": "11111", "ie_key": "Gia"}, {"id": "22222", "ie_key": "GiaTab"},
                                {"id": "abc"}, {"id": "33333", "title": "B"}]})
    ra = NenGia(nha).kham_pha(YeuCauCao("gia", "tu_khoa", "meo", 5), bao_tien_do=_khong_bao)
    assert nha.tao[0].urls == [("giasearch5:meo", False)]
    assert ra == [CrawlItem("gia", "11111", "https://gia.test/v/11111"),
                  CrawlItem("gia", "33333", "https://gia.test/v/33333", tieu_de="B")]


def test_tai_tai_dung_url_chuan(tmp_path):
    nha = Nha(kich_ban=lambda y: _ghi(tmp_path / "12345.mp4"))
    tep = NenGia(nha).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert nha.tao[0].urls == [(["https://gia.test/v/12345"], True)]
    assert tep.ten_hien_thi == "T [12345].mp4"


def test_tai_tu_choi_url_lech_url_chuan(tmp_path):
    nha = Nha()
    with pytest.raises(LoiCao) as e:
        NenGia(nha).tai(CrawlItem("gia", "12345", "https://gia.test/list/9"), tmp_path, bao_tien_do=_khong_bao)
    assert (e.value.ma, e.value.tam_thoi) == ("url_khong_ho_tro", False) and nha.tao == []


# ---------------------------------------------------------------- nhịp tim (MAJOR 3)
def test_hook_bao_moi_lan_ke_ca_khong_biet_tong(tmp_path):
    def kb(y):
        y.hook({"status": "downloading", "downloaded_bytes": 40, "total_bytes": 100})
        y.hook({"status": "downloading", "downloaded_bytes": 41})
        y.hook({"status": "downloading"})
        y.hook({"status": "downloading", "downloaded_bytes": 41, "total_bytes": 100})
        _ghi(tmp_path / "12345.mp4")

    bao = []
    NenGia(Nha(kich_ban=kb)).tai(_ITEM, tmp_path, bao_tien_do=lambda p, m: bao.append(p))
    assert bao == [40, 40, 40, 41]


def test_nhip_tim_trong_download_dai(tmp_path, nhip_nhanh):
    def kb(y):
        y.hook({"status": "downloading", "downloaded_bytes": 30, "total_bytes": 100})
        time.sleep(0.4)                 # trích xuất / ghép ffmpeg: không hook nào
        _ghi(tmp_path / "12345.mp4")

    bao = []
    NenGia(Nha(kich_ban=kb)).tai(_ITEM, tmp_path, bao_tien_do=lambda p, m: bao.append((p, m)))
    nhip = [b for b in bao if b[1] == "đang xử lý"]
    assert len(nhip) >= 3 and all(p == 30 for p, _ in nhip)
    assert _khong_con_nhip()
    n = len(bao)
    time.sleep(0.2)
    assert len(bao) == n                # luồng đã dừng + join trong finally


def test_nhip_tim_trong_kham_pha(nhip_nhanh):
    bao = []
    nha = Nha(info={"entries": []}, kich_ban=lambda y: time.sleep(0.3))
    NenGia(nha).kham_pha(YeuCauCao("gia", "tu_khoa", "x", 3), bao_tien_do=lambda p, m: bao.append((p, m)))
    assert len([b for b in bao if b[1] == "đang xử lý"]) >= 2
    assert _khong_con_nhip()


class HuyViec(Exception):
    pass


def test_nhip_tim_nem_huy_thi_giu_va_nem_lai_goc(tmp_path, nhip_nhanh):
    goc = HuyViec("khach huy")

    def bao(p, m):
        if m == "đang xử lý":
            raise goc

    def kb(y):
        time.sleep(0.3)                 # không hook nào: huỷ chỉ lộ ra sau khi yt-dlp trả về
        _ghi(tmp_path / "12345.mp4")

    with pytest.raises(HuyViec) as e:
        NenGia(Nha(kich_ban=kb)).tai(_ITEM, tmp_path, bao_tien_do=bao)
    assert e.value is goc and _khong_con_nhip()


def test_nhip_tim_huy_roi_hook_ke_tiep_ngat_download(tmp_path, nhip_nhanh):
    goc = HuyViec("khach huy")
    sau_huy = []

    def bao(p, m):
        if m == "đang xử lý":
            raise goc

    def kb(y):
        time.sleep(0.2)
        try:
            y.hook({"status": "downloading", "downloaded_bytes": 1, "total_bytes": 2})
        except DownloadCancelled:
            sau_huy.append(True)
            raise

    with pytest.raises(HuyViec) as e:
        NenGia(Nha(kich_ban=kb)).tai(_ITEM, tmp_path, bao_tien_do=bao)
    assert e.value is goc and sau_huy == [True]


def test_nhip_tim_huy_trong_kham_pha(nhip_nhanh):
    goc = HuyViec("huy")

    def bao(p, m):
        if m == "đang xử lý":
            raise goc

    nha = Nha(info={"entries": []}, kich_ban=lambda y: time.sleep(0.3))
    with pytest.raises(HuyViec) as e:
        NenGia(nha).kham_pha(YeuCauCao("gia", "tu_khoa", "x", 3), bao_tien_do=bao)
    assert e.value is goc


def test_hook_nhieu_luong_duoc_khoa(tmp_path, nhip_nhanh):
    """concurrent_fragment_downloads gọi hook từ nhiều luồng — bao_tien_do không bao giờ chạy chồng."""
    dang, dinh = [0], [0]
    kh = threading.Lock()

    def bao(p, m):
        with kh:
            dang[0] += 1
            dinh[0] = max(dinh[0], dang[0])
        time.sleep(0.002)
        with kh:
            dang[0] -= 1

    def kb(y):
        def chay(k):
            for i in range(15):
                y.hook({"status": "downloading", "downloaded_bytes": i + k, "total_bytes": 100})
        ts = [threading.Thread(target=chay, args=(k,)) for k in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        _ghi(tmp_path / "12345.mp4")

    NenGia(Nha(kich_ban=kb)).tai(_ITEM, tmp_path, bao_tien_do=bao)
    assert dinh[0] == 1


# ---------------------------------------------------------------- lọc trực tiếp / quá dài (MAJOR 3b)
@pytest.mark.parametrize("info,ma", [
    ({"id": "1", "is_live": True}, "khong_ho_tro_truc_tiep"),
    ({"id": "1", "live_status": "is_live"}, "khong_ho_tro_truc_tiep"),
    ({"id": "1", "live_status": "is_upcoming"}, "khong_ho_tro_truc_tiep"),
    ({"id": "1", "live_status": "post_live"}, "khong_ho_tro_truc_tiep"),
    ({"id": "1", "duration": 3 * 3600 + 1}, "qua_dai"),
    ({"id": "1", "filesize_approx": 4 * 1024 ** 3 + 1}, "qua_lon"),
    ({"id": "1", "filesize": 4 * 1024 ** 3 + 1}, "qua_lon"),
])
def test_ly_do_tu_choi(info, ma):
    assert NenGia().ly_do_tu_choi(info) == ma


@pytest.mark.parametrize("info", [
    {"id": "1"}, {"id": "1", "live_status": "was_live", "was_live": True, "duration": 600},
    {"id": "1", "live_status": "not_live", "is_live": False, "duration": 3 * 3600},
    {"id": "1", "duration": None, "filesize": None},
])
def test_ly_do_tu_choi_cho_qua(info):
    assert NenGia().ly_do_tu_choi(info) is None


def test_gioi_han_la_tham_so_constructor():
    a = NenGia(thoi_luong_toi_da_s=60, max_filesize=100)
    assert a.ly_do_tu_choi({"duration": 61}) == "qua_dai"
    assert a.ly_do_tu_choi({"filesize": 101}) == "qua_lon"
    assert a.ly_do_tu_choi({"duration": 60, "filesize": 100}) is None


def test_match_filter_chay_duoc_trong_youtubedl_that():
    """Chữ ký phải đúng như YoutubeDL._match_entry gọi (:1593) — dựng YoutubeDL thật, không mạng."""
    opts = {**YoutubeAdapter.tuy_chon_goc(), "match_filter": YoutubeAdapter().bo_loc()}
    with yt_dlp.YoutubeDL(opts) as y:
        assert y._match_entry({"id": "a", "title": "t", "live_status": "is_upcoming"}, incomplete=True)
        assert y._match_entry({"id": "a", "title": "t", "duration": 99999}, incomplete=True)
        assert y._match_entry({"id": "a", "title": "t", "duration": 60}, incomplete=True) is None


@pytest.mark.parametrize("info,ma", [
    ({"id": "12345", "live_status": "is_live"}, "khong_ho_tro_truc_tiep"),
    ({"id": "12345", "duration": 99999}, "qua_dai"),
    ({"id": "12345", "filesize_approx": 5 * 1024 ** 3}, "qua_lon"),
])
def test_tai_muc_bi_loc_thanh_loi_cao(tmp_path, info, ma):
    """yt-dlp bỏ mục bị lọc trong im lặng (_match_entry trả lý do, process_info return) — không được 'thành công'."""
    def kb(y):
        assert y.params["match_filter"](info, incomplete=False) is not None

    with pytest.raises(LoiCao) as e:
        NenGia(Nha(kich_ban=kb)).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert (e.value.ma, e.value.tam_thoi) == (ma, False)


def test_kham_pha_bo_muc_truc_tiep_va_qua_dai():
    nha = Nha(info={"entries": [{"id": "11111", "live_status": "is_live"}, {"id": "22222", "duration": 99999},
                                {"id": "33333", "duration": 30}]})
    ra = NenGia(nha).kham_pha(YeuCauCao("gia", "tu_khoa", "x", 5), bao_tien_do=_khong_bao)
    assert [m.id for m in ra] == ["33333"]
    assert callable(nha.tao[0].params["match_filter"])


# ---------------------------------------------------------------- dung lượng (MAJOR 6)
def test_max_filesize_mac_dinh_4gib_va_tuy_bien(tmp_path):
    nha = Nha(kich_ban=lambda y: _ghi(tmp_path / "12345.mp4"))
    NenGia(nha).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    NenGia(nha, max_filesize=123).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert [y.params["max_filesize"] for y in nha.tao] == [4 * 1024 ** 3, 123]
    assert all(y.params["ignoreerrors"] is False for y in nha.tao)


def test_httpfd_bo_qua_vi_qua_lon_thanh_loi_cao(tmp_path):
    def kb(y):
        y.params["logger"].debug(
            "\r[download] File is larger than max-filesize (5000 bytes > 4000 bytes). Aborting.")

    with pytest.raises(LoiCao) as e:
        NenGia(Nha(kich_ban=kb)).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert (e.value.ma, e.value.tam_thoi) == ("qua_lon", False)


def test_tep_cuoi_vuot_gioi_han_thanh_loi_cao(tmp_path):
    """Tải phân mảnh (DASH/HLS) không kiểm max_filesize — kiểm lại trên tệp cuối."""
    with pytest.raises(LoiCao) as e:
        NenGia(Nha(kich_ban=lambda y: _ghi(tmp_path / "12345.mp4")), max_filesize=5).tai(
            _ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "qua_lon" and not (tmp_path / "12345.mp4").exists()
