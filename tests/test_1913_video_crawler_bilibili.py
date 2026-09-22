"""BilibiliAdapter (spec §11, §18, §21) — không bao giờ chạm mạng: YoutubeDL giả tiêm qua `ydl_factory`.

Nguồn sự thật:
- donor `docs/migrations/video_crawler/PLATFORM_MATRIX.md` dòng `bili`: search/link/channel/collection
  (`ugc_season`) đều có qua MediaCrawler (KHÔNG đọc mã MediaCrawler — chỉ dùng bảng đã tổng hợp);
  `-101` ẩn danh vẫn cào được; dedup `aid`+`bvid`.
- yt-dlp 2026.03.17 đã cài, `site-packages/yt_dlp/extractor/bilibili.py`: `BiliBiliIE` (:307 video),
  `BiliBiliSearchIE` (:1817-1870, `_SEARCH_KEY='bilisearch'`), `BilibiliSpaceVideoIE` (:1270-1370 kênh),
  `BilibiliCollectionListIE` (:1423-1483, API `seasons_archives_list` = `ugc_season` donor).
- Search flat: `BiliBiliSearchIE._search_results` (:1870) chỉ trả
  `url_result(video['arcurl'], 'BiliBili', str(video['aid']))` → với `extract_flat="in_playlist"`
  (bắt buộc ở `_ytdlp.py.kham_pha`), `YoutubeDL.py:1888-1909` KHÔNG resolve tiếp nên entry.id là aid
  số, không phải bvid. `BiliBiliIE._VALID_URL` (:307) nhận cả prefix `av` nên `url_video` dựng lại
  đúng URL cho cả hai dạng id.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
import yt_dlp
from yt_dlp.utils import DownloadCancelled, DownloadError

from apps.video_crawler.adapters.base import CrawlItem, LoiCao, TepTai, YeuCauCao
from apps.video_crawler.adapters.bilibili import BilibiliAdapter, chuan_hoa_kenh_bilibili, tuy_chon


# ---------------------------------------------------------------- YoutubeDL giả (giống YouTube lane)
class FakeYDL:
    """Bắt chước bề mặt YoutubeDL mà adapter dùng. `kich_ban(ydl)` chạy trong download().

    Như yt-dlp thật (YoutubeDL.py:1699, 1717-1721, 3629-3631): chỉ DownloadCancelled được ném lại;
    exception khác từ hook bị nuốt — nên huỷ phải đi bằng lớp con DownloadCancelled.
    """

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
    """Factory ghi lại mọi YoutubeDL đã tạo."""

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
    return YeuCauCao(nen_tang="bilibili", che_do=che_do, dau_vao=dau_vao, so_luong=n)


# ---------------------------------------------------------------- chuẩn hoá kênh
@pytest.mark.parametrize("vao,ra", [
    ("3985676", "https://space.bilibili.com/3985676/video"),
    ("https://space.bilibili.com/3985676", "https://space.bilibili.com/3985676/video"),
    ("https://space.bilibili.com/3985676/video", "https://space.bilibili.com/3985676/video"),
    ("https://space.bilibili.com/3985676/video?spm_id=1", "https://space.bilibili.com/3985676/video"),
    ("space.bilibili.com/3985676", "https://space.bilibili.com/3985676/video"),
    ("", ""),
])
def test_chuan_hoa_kenh_bilibili(vao, ra):
    assert chuan_hoa_kenh_bilibili(vao) == ra


# ---------------------------------------------------------------- tuỳ chọn
def test_tuy_chon_khong_impersonate_va_khong_extractor_args_la():
    assert BilibiliAdapter.impersonate is False


@pytest.mark.parametrize("khoa", [
    "nocheckcertificate", "cookiefile", "cookiesfrombrowser", "remote_components",
    "download_archive", "exec", "exec_cmd", "netrc", "usenetrc",
])
def test_tuy_chon_khong_co_khoa_cam(khoa):
    assert khoa not in tuy_chon()
    assert khoa not in tuy_chon(thu_muc=Path("x"))


def test_tuy_chon_ignoreerrors_tuong_minh_false():
    for o in (tuy_chon(), tuy_chon(thu_muc=Path("x"))):
        assert "ignoreerrors" in o and o["ignoreerrors"] is False


def test_allowed_extractors_chi_bilibili_va_ton_tai_that():
    """Tên phải là IE_NAME thật (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929)."""
    from yt_dlp.extractor import gen_extractor_classes

    ten_that = {ie.IE_NAME.lower() for ie in gen_extractor_classes()}
    ae = tuy_chon()["allowed_extractors"]
    assert ae and "generic" not in ae and "default" not in ae and "all" not in ae
    for ten in ae:
        assert ten.replace("\\", "") in ten_that, ten
    # Đúng bốn extractor thật khớp GIAO donor ∩ yt-dlp (video/search/channel/collection).
    assert set(ae) == {"bilibili", "bilibilisearch", "bilibilispacevideo", "bilibilicollectionlist"}


def test_youtubedl_that_chi_nap_extractor_bilibili():
    """Dựng YoutubeDL thật (không mạng) — kiểm allowed_extractors đúng là chặn generic."""
    with yt_dlp.YoutubeDL(tuy_chon()) as y:
        ten = set(y._ies)
    assert ten and "Generic" not in ten
    assert all(k.lower().startswith("bilibili") for k in ten), ten


# ---------------------------------------------------------------- khám phá
def test_mac_dinh_nap_youtubedl_luc_can(monkeypatch):
    goi = []
    gia = types.ModuleType("yt_dlp")
    gia.YoutubeDL = lambda opts: goi.append(opts) or "ydl"
    monkeypatch.setitem(sys.modules, "yt_dlp", gia)
    a = BilibiliAdapter()
    assert a.nen_tang == "bilibili"
    assert a._tao({"x": 1}) == "ydl" and goi == [{"x": 1}]


def _info(entries):
    return {"_type": "playlist", "entries": entries}


def test_kham_pha_tu_khoa_dung_bilisearch():
    nha = Nha(info=_info([{"id": "254238063", "title": "T", "uploader": "U"}]))
    ra = BilibiliAdapter(nha).kham_pha(_yc("tu_khoa", "meo con", 7), bao_tien_do=_khong_bao)
    y = nha.tao[0]
    assert y.urls == [("bilisearch7:meo con", False)]
    assert y.params["extract_flat"] == "in_playlist"
    assert y.params["skip_download"] is True
    assert y.params["playlistend"] == 7
    assert ra == [CrawlItem("bilibili", "254238063", "https://www.bilibili.com/video/av254238063", "T", "U")]


def test_kham_pha_kenh_chuan_hoa_va_playlistend():
    nha = Nha(info=_info([]))
    BilibiliAdapter(nha).kham_pha(_yc("kenh", "3985676", 3), bao_tien_do=_khong_bao)
    y = nha.tao[0]
    assert y.urls == [("https://space.bilibili.com/3985676/video", False)]
    assert y.params["playlistend"] == 3


def test_kham_pha_bo_dung_url_bo_nguyen_van():
    url = "https://space.bilibili.com/2142762/lists/3662502?type=season"
    nha = Nha(info=_info([]))
    BilibiliAdapter(nha).kham_pha(_yc("bo", url, 4), bao_tien_do=_khong_bao)
    y = nha.tao[0]
    assert y.urls == [(url, False)]
    assert y.params["playlistend"] == 4


def test_kham_pha_link_tra_mot_muc():
    url = "https://www.bilibili.com/video/BV13x41117TL"
    nha = Nha(info={"id": "BV13x41117TL", "title": "T", "uploader": "U", "duration": 554.1})
    ra = BilibiliAdapter(nha).kham_pha(_yc("link", url, 5), bao_tien_do=_khong_bao)
    assert nha.tao[0].urls == [(url, False)]
    assert nha.tao[0].params["noplaylist"] is True
    assert ra == [CrawlItem(nen_tang="bilibili", id="BV13x41117TL",
                            url="https://www.bilibili.com/video/BV13x41117TL",
                            tieu_de="T", tac_gia="U", thoi_luong_s=554, anh_bia="")]


def test_kham_pha_anh_xa_muc_bvid_va_aid():
    nha = Nha(info=_info([
        {"id": "BV1bK411W797", "title": "A", "channel": "Kenh", "uploader": "U", "duration": 61,
         "thumbnail": "https://i0.hdslb.com/a.jpg"},
        {"id": "254238063", "title": "B", "uploader": "U2", "duration": None,
         "thumbnails": [{"url": "https://t/1.jpg"}, {"url": "https://t/2.jpg"}]},
    ]))
    ra = BilibiliAdapter(nha).kham_pha(_yc("tu_khoa", "x", 5), bao_tien_do=_khong_bao)
    assert ra == [
        CrawlItem("bilibili", "BV1bK411W797", "https://www.bilibili.com/video/BV1bK411W797", "A", "Kenh", 61,
                  "https://i0.hdslb.com/a.jpg"),
        CrawlItem("bilibili", "254238063", "https://www.bilibili.com/video/av254238063", "B", "U2", None,
                  "https://t/2.jpg"),
    ]


def test_kham_pha_bo_muc_khong_id_va_cat_n():
    nha = Nha(info=_info([None, {"title": "khong id"}, {"id": "ab"}, {"id": "BV1xxxxxxxxx"},
                          {"id": "BV2xxxxxxxxx"}, {"id": "BV3xxxxxxxxx"}]))
    ra = BilibiliAdapter(nha).kham_pha(_yc("kenh", "3985676", 2), bao_tien_do=_khong_bao)
    assert [m.id for m in ra] == ["BV1xxxxxxxxx", "BV2xxxxxxxxx"]


def test_kham_pha_download_error_duoc_phan_loai():
    nha = Nha(loi=DownloadError("ERROR: [BiliBili] BV1xxxxxxxxx: This video is unavailable"))
    with pytest.raises(LoiCao) as e:
        BilibiliAdapter(nha).kham_pha(_yc("tu_khoa", "x"), bao_tien_do=_khong_bao)
    assert e.value.ma == "khong_ton_tai" and e.value.tam_thoi is False


# ---------------------------------------------------------------- tải
_ITEM = CrawlItem("bilibili", "BV13x41117TL", "https://www.bilibili.com/video/BV13x41117TL",
                  tieu_de='Mèo: "con"/<to>?*|')


def _ghi(p: Path, n=10) -> Path:
    p.write_bytes(b"x" * n)
    return p


def test_tai_bao_tien_do_theo_byte_va_ghep(tmp_path):
    def kb(y):
        y.hook({"status": "downloading", "downloaded_bytes": 0, "total_bytes": 200})
        y.hook({"status": "downloading", "downloaded_bytes": 100, "total_bytes": 200})
        y.hook({"status": "downloading", "downloaded_bytes": 30, "total_bytes_estimate": 40})
        y.hook({"status": "downloading", "downloaded_bytes": 5})
        y.pp_hook({"status": "started", "postprocessor": "Merger", "info_dict": {}})
        _ghi(tmp_path / "BV13x41117TL.mp4")

    nha = Nha(kich_ban=kb)
    bao = []
    BilibiliAdapter(nha).tai(_ITEM, tmp_path, bao_tien_do=lambda p, m: bao.append((p, m)))
    assert [p for p, _ in bao] == [0, 50, 75, 75, 99]
    assert bao[-1] == (99, "đang ghép")
    y = nha.tao[0]
    assert y.urls == [(["https://www.bilibili.com/video/BV13x41117TL"], True)]
    assert y.params["outtmpl"] == str(tmp_path / "%(id)s.%(ext)s")


def test_tai_tra_tep_tu_hook_va_ten_hien_thi_sach(tmp_path):
    that = tmp_path / "BV13x41117TL.mp4"

    def kb(y):
        _ghi(tmp_path / "BV13x41117TL.f137.mp4", 3)
        _ghi(that, 42)
        y.pp_hook({"status": "finished", "postprocessor": "MoveFiles", "info_dict": {"filepath": str(that)}})

    tep = BilibiliAdapter(Nha(kich_ban=kb)).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert tep == TepTai(duong_dan=that, kich_thuoc=42, ten_hien_thi="Mèo con to [BV13x41117TL].mp4")


def test_tai_tim_tep_trong_thu_muc_bo_tep_trung_gian(tmp_path):
    def kb(y):
        _ghi(tmp_path / "BV13x41117TL.f137.mp4")
        _ghi(tmp_path / "BV13x41117TL.mp4.part")
        _ghi(tmp_path / "BV13x41117TL.mkv", 7)

    tep = BilibiliAdapter(Nha(kich_ban=kb)).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert tep.duong_dan == tmp_path / "BV13x41117TL.mkv" and tep.kich_thuoc == 7


def test_tai_khong_thay_tep(tmp_path):
    with pytest.raises(LoiCao) as e:
        BilibiliAdapter(Nha()).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "khong_thay_tep" and e.value.tam_thoi is True


def test_tai_download_error_duoc_phan_loai(tmp_path):
    nha = Nha(loi=DownloadError("ERROR: [BiliBili] BV13x41117TL: Private video. Sign in if you've been granted access"))
    with pytest.raises(LoiCao) as e:
        BilibiliAdapter(nha).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "rieng_tu" and e.value.tam_thoi is False


class HuyViec(Exception):
    pass


def test_tai_huy_lan_truyen_dung_ngoai_le_goc(tmp_path):
    goc = HuyViec("khach huy")

    def bao(p, m):
        raise goc

    def kb(y):
        y.hook({"status": "downloading", "downloaded_bytes": 1, "total_bytes": 2})
        _ghi(tmp_path / "BV13x41117TL.mp4")

    nha = Nha(kich_ban=kb)
    with pytest.raises(HuyViec) as e:
        BilibiliAdapter(nha).tai(_ITEM, tmp_path, bao_tien_do=bao)
    assert e.value is goc
    assert len(nha.tao[0].thay) == 1 and isinstance(nha.tao[0].thay[0], DownloadCancelled)


def test_tai_huy_trong_hook_ghep(tmp_path):
    goc = HuyViec("huy khi ghep")

    def bao(p, m):
        if p == 99:
            raise goc

    def kb(y):
        y.pp_hook({"status": "started", "postprocessor": "Merger", "info_dict": {}})

    nha = Nha(kich_ban=kb)
    with pytest.raises(HuyViec) as e:
        BilibiliAdapter(nha).tai(_ITEM, tmp_path, bao_tien_do=bao)
    assert e.value is goc and isinstance(nha.tao[0].thay[0], DownloadCancelled)


# ---------------------------------------------------------------- URL chuẩn (BLOCKER: URL bị sửa)
def test_url_video_va_id_hop_le_bvid_va_aid():
    a = BilibiliAdapter()
    assert a.url_video("BV13x41117TL") == "https://www.bilibili.com/video/BV13x41117TL"
    assert a.url_video("254238063") == "https://www.bilibili.com/video/av254238063"
    assert a.id_hop_le("BV13x41117TL") and a.id_hop_le("254238063") and a.id_hop_le("1")
    for sai in ("", "BV13x41117T", "BV13x41117TLx", "av254238063", "bv13x41117tl",
                "254238063x", "1" * 13, None):
        assert not a.id_hop_le(sai), sai


@pytest.mark.parametrize("item", [
    CrawlItem("bilibili", "BV13x41117TL", "https://space.bilibili.com/2142762/lists/3662502?type=season"),
    CrawlItem("bilibili", "BV13x41117TL", "https://space.bilibili.com/3985676/video"),
    CrawlItem("bilibili", "BV13x41117TL", "https://www.bilibili.com/video/BV13x41117TL?p=2"),
    CrawlItem("bilibili", "BV13x41117TL", "http://www.bilibili.com/video/BV13x41117TL"),
    CrawlItem("bilibili", "BV13x41117TL", "https://www.bilibili.com/video/BVkhackhackhac"),
    CrawlItem("bilibili", "254238063", "https://www.bilibili.com/video/av254238064"),
    CrawlItem("bilibili", "ab", "https://www.bilibili.com/video/BVab"),
])
def test_tai_tu_choi_url_khong_chuan(tmp_path, item):
    nha = Nha()
    with pytest.raises(LoiCao) as e:
        BilibiliAdapter(nha).tai(item, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro" and e.value.tam_thoi is False
    assert nha.tao == []
