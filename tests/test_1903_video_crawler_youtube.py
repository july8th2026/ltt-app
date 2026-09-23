"""YoutubeAdapter (spec §11, §18, §21) — không bao giờ chạm mạng: YoutubeDL giả được tiêm qua `ydl_factory`.

Nguồn characterization (donor `D:\\Viral\\resources\\app-src\\tai_ytdlp.py`, ký hiệu Y):
- `chuan_hoa_kenh_youtube` + `_YT_TABS`: Y:228-252.
- tuỳ chọn: Y:1237-1249 (`_CHUOI_FORMAT`), Y:2019-2031, Y:2081-2083 (player_client), Y:2090-2095 (sleep).
- tìm kiếm `ytsearch<n>:<kw>`: Y:2169; tên tệp `%(title).80B [%(id)s]`: Y:2168; `an_toan`: Y:194-198.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
import yt_dlp
from yt_dlp.utils import DownloadCancelled, DownloadError

from apps.video_crawler.adapters.base import CrawlItem, LoiCao, TepTai, YeuCauCao
from apps.video_crawler.adapters.youtube import YoutubeAdapter, chuan_hoa_kenh_youtube, tuy_chon


# ---------------------------------------------------------------- YoutubeDL giả
class FakeYDL:
    """Bắt chước bề mặt YoutubeDL mà adapter dùng. `kich_ban(ydl)` chạy trong download().

    Như yt-dlp thật (YoutubeDL.py:1699, 1717-1721, 3629-3631): chỉ DownloadCancelled được ném lại;
    exception khác từ hook bị nuốt (report_error) — nên huỷ phải đi bằng lớp con DownloadCancelled.
    """

    def __init__(self, opts, *, info=None, loi=None, kich_ban=None):
        self.params = opts
        self.info = info
        self.loi = loi
        self.kich_ban = kich_ban
        self.urls: list = []
        self.thay: list = []   # exception thấy được từ hook

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
    return YeuCauCao(nen_tang="youtube", che_do=che_do, dau_vao=dau_vao, so_luong=n)


# ---------------------------------------------------------------- chuẩn hoá kênh
@pytest.mark.parametrize("vao", [
    "@abc", "abc", "https://www.youtube.com/@abc", "https://www.youtube.com/@abc/?si=x#top",
    "www.youtube.com/@abc",
])
def test_chuan_hoa_kenh_ve_tab_videos(vao):
    assert chuan_hoa_kenh_youtube(vao) == "https://www.youtube.com/@abc/videos"


@pytest.mark.parametrize("vao,ra", [
    ("https://www.youtube.com/@abc/shorts", "https://www.youtube.com/@abc/shorts"),
    ("https://www.youtube.com/@abc/streams?x=1", "https://www.youtube.com/@abc/streams"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ"),
    ("", ""),
])
def test_chuan_hoa_kenh_giu_tab_va_link_video(vao, ra):
    assert chuan_hoa_kenh_youtube(vao) == ra


# ---------------------------------------------------------------- tuỳ chọn
def test_tuy_chon_port_donor():
    o = tuy_chon()
    assert o["format"] == (
        "bv*[vcodec!*=hev][vcodec!*=hvc][vcodec!*=h265][vcodec!*=vvc][vcodec!*=bytevc]+ba"
        "/b[vcodec!*=hev][vcodec!*=hvc][vcodec!*=h265][vcodec!*=vvc][vcodec!*=bytevc]"
        "/bv*[vcodec~='^(avc1|h264)']+ba[ext=m4a]/b[vcodec~='^(avc1|h264)']/bv*+ba/b[vcodec!=none]"
    )
    assert o["format_sort"] == ["res", "br"]
    assert o["merge_output_format"] == "mp4"
    assert o["retries"] == 3
    assert o["concurrent_fragment_downloads"] == 4
    assert o["enable_file_urls"] is False
    assert o["extractor_args"] == {"youtube": {"player_client": ["web_embedded", "default"]}}
    assert o["sleep_interval_requests"] == 1.0
    assert o["quiet"] and o["no_warnings"] and o["noprogress"]


@pytest.mark.parametrize("khoa", [
    "nocheckcertificate", "cookiefile", "cookiesfrombrowser", "remote_components",
    "download_archive", "exec", "exec_cmd", "netrc", "usenetrc",
])
def test_tuy_chon_khong_co_khoa_cam(khoa):
    assert khoa not in tuy_chon()
    assert khoa not in tuy_chon(thu_muc=Path("x"))


def test_tuy_chon_khong_tai_khong_dat_outtmpl():
    assert "outtmpl" not in tuy_chon()


def test_tuy_chon_tai_dat_outtmpl_va_noplaylist(tmp_path):
    o = tuy_chon(thu_muc=tmp_path)
    assert o["outtmpl"] == str(tmp_path / "%(id)s.%(ext)s")
    assert o["noplaylist"] is True


def test_allowed_extractors_chi_youtube_va_ton_tai_that():
    """Tên phải là IE_NAME thật (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929)."""
    from yt_dlp.extractor import gen_extractor_classes

    ten_that = {ie.IE_NAME.lower() for ie in gen_extractor_classes()}
    ae = tuy_chon()["allowed_extractors"]
    assert ae and "generic" not in ae and "default" not in ae and "all" not in ae
    for ten in ae:
        assert ten.replace("\\", "") in ten_that, ten


def test_youtubedl_that_chi_nap_extractor_youtube():
    """Dựng YoutubeDL thật (không mạng) — kiểm allowed_extractors đúng là chặn generic."""
    with yt_dlp.YoutubeDL(tuy_chon()) as y:
        ten = set(y._ies)
    assert ten and "Generic" not in ten
    assert all(k.startswith("Youtube") for k in ten), ten


# ---------------------------------------------------------------- khám phá
def test_mac_dinh_nap_youtubedl_luc_can(monkeypatch):
    goi = []
    gia = types.ModuleType("yt_dlp")
    gia.YoutubeDL = lambda opts: goi.append(opts) or "ydl"
    monkeypatch.setitem(sys.modules, "yt_dlp", gia)
    a = YoutubeAdapter()
    assert a.nen_tang == "youtube"
    assert a._tao({"x": 1}) == "ydl" and goi == [{"x": 1}]


def _info(entries):
    return {"_type": "playlist", "entries": entries}


def test_kham_pha_tu_khoa_dung_ytsearch():
    nha = Nha(info=_info([{"id": "a1xxxxxxxxx"}]))
    YoutubeAdapter(nha).kham_pha(_yc("tu_khoa", "meo con", 7), bao_tien_do=_khong_bao)
    y = nha.tao[0]
    assert y.urls == [("ytsearch7:meo con", False)]
    assert y.params["extract_flat"] == "in_playlist"
    assert y.params["skip_download"] is True
    assert y.params["playlistend"] == 7


def test_kham_pha_kenh_chuan_hoa_va_playlistend():
    nha = Nha(info=_info([]))
    YoutubeAdapter(nha).kham_pha(_yc("kenh", "@abc", 3), bao_tien_do=_khong_bao)
    y = nha.tao[0]
    assert y.urls == [("https://www.youtube.com/@abc/videos", False)]
    assert y.params["playlistend"] == 3


def test_kham_pha_bo_dung_url_playlist():
    url = "https://www.youtube.com/playlist?list=PL123"
    nha = Nha(info=_info([]))
    YoutubeAdapter(nha).kham_pha(_yc("bo", url, 4), bao_tien_do=_khong_bao)
    y = nha.tao[0]
    assert y.urls == [(url, False)]
    assert y.params["playlistend"] == 4


def test_kham_pha_link_tra_mot_muc():
    url = "https://www.youtube.com/watch?v=vid1xxxxxxx"
    nha = Nha(info={"id": "vid1xxxxxxx", "title": "T", "uploader": "U", "duration": 12.7})
    ra = YoutubeAdapter(nha).kham_pha(_yc("link", url, 5), bao_tien_do=_khong_bao)
    assert nha.tao[0].urls == [(url, False)]
    assert nha.tao[0].params["noplaylist"] is True
    assert ra == [CrawlItem(nen_tang="youtube", id="vid1xxxxxxx", url="https://www.youtube.com/watch?v=vid1xxxxxxx",
                            tieu_de="T", tac_gia="U", thoi_luong_s=12, anh_bia="")]


def test_kham_pha_anh_xa_muc():
    nha = Nha(info=_info([
        {"id": "aaaaaaaaaaa", "title": "A", "channel": "Kenh", "uploader": "U", "duration": 61,
         "thumbnail": "https://i.ytimg.com/a.jpg"},
        {"id": "bbbbbbbbbbb", "title": "B", "uploader": "U2", "duration": None,
         "thumbnails": [{"url": "https://t/1.jpg"}, {"url": "https://t/2.jpg"}]},
    ]))
    ra = YoutubeAdapter(nha).kham_pha(_yc("tu_khoa", "x", 5), bao_tien_do=_khong_bao)
    assert ra == [
        CrawlItem("youtube", "aaaaaaaaaaa", "https://www.youtube.com/watch?v=aaaaaaaaaaa", "A", "Kenh", 61,
                  "https://i.ytimg.com/a.jpg"),
        CrawlItem("youtube", "bbbbbbbbbbb", "https://www.youtube.com/watch?v=bbbbbbbbbbb", "B", "U2", None,
                  "https://t/2.jpg"),
    ]


def test_kham_pha_bo_muc_khong_id_va_cat_n():
    nha = Nha(info=_info([None, {"title": "khong id"}, {"id": "ngan"}, {"id": "1" * 11}, {"id": "2" * 11},
                          {"id": "3" * 11}]))
    ra = YoutubeAdapter(nha).kham_pha(_yc("kenh", "@abc", 2), bao_tien_do=_khong_bao)
    assert [m.id for m in ra] == ["1" * 11, "2" * 11]   # id sai dạng bị bỏ ở khâu khám phá


def test_kham_pha_download_error_duoc_phan_loai():
    nha = Nha(loi=DownloadError("ERROR: [youtube] x: Sign in to confirm you're not a bot"))
    with pytest.raises(LoiCao) as e:
        YoutubeAdapter(nha).kham_pha(_yc("tu_khoa", "x"), bao_tien_do=_khong_bao)
    assert e.value.ma == "yt_bot" and e.value.tam_thoi is True


# ---------------------------------------------------------------- tải
_ITEM = CrawlItem("youtube", "vid1xxxxxxx", "https://www.youtube.com/watch?v=vid1xxxxxxx", tieu_de='Mèo: "con"/<to>?*|')


def _ghi(p: Path, n=10) -> Path:
    p.write_bytes(b"x" * n)
    return p


def test_tai_bao_tien_do_theo_byte_va_ghep(tmp_path):
    def kb(y):
        y.hook({"status": "downloading", "downloaded_bytes": 0, "total_bytes": 200})
        y.hook({"status": "downloading", "downloaded_bytes": 100, "total_bytes": 200})
        y.hook({"status": "downloading", "downloaded_bytes": 30, "total_bytes_estimate": 40})
        y.hook({"status": "downloading", "downloaded_bytes": 5})       # thiếu tổng ⇒ % gần nhất
        y.pp_hook({"status": "started", "postprocessor": "Merger", "info_dict": {}})
        _ghi(tmp_path / "vid1xxxxxxx.mp4")

    nha = Nha(kich_ban=kb)
    bao = []
    YoutubeAdapter(nha).tai(_ITEM, tmp_path, bao_tien_do=lambda p, m: bao.append((p, m)))
    assert [p for p, _ in bao] == [0, 50, 75, 75, 99]   # mọi lần hook đều báo, không bóp ở đây
    assert bao[-1] == (99, "đang ghép")
    y = nha.tao[0]
    assert y.urls == [(["https://www.youtube.com/watch?v=vid1xxxxxxx"], True)]
    assert y.params["outtmpl"] == str(tmp_path / "%(id)s.%(ext)s")


def test_tai_tra_tep_tu_hook_va_ten_hien_thi_sach(tmp_path):
    that = tmp_path / "vid1xxxxxxx.mp4"

    def kb(y):
        _ghi(tmp_path / "vid1xxxxxxx.f137.mp4", 3)
        _ghi(that, 42)
        y.pp_hook({"status": "finished", "postprocessor": "MoveFiles", "info_dict": {"filepath": str(that)}})

    tep = YoutubeAdapter(Nha(kich_ban=kb)).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert tep == TepTai(duong_dan=that, kich_thuoc=42, ten_hien_thi="Mèo con to [vid1xxxxxxx].mp4")


def test_tai_tim_tep_trong_thu_muc_bo_tep_trung_gian(tmp_path):
    def kb(y):
        _ghi(tmp_path / "vid1xxxxxxx.f137.mp4")
        _ghi(tmp_path / "vid1xxxxxxx.mp4.part")
        _ghi(tmp_path / "vid1xxxxxxx.mkv", 7)

    tep = YoutubeAdapter(Nha(kich_ban=kb)).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert tep.duong_dan == tmp_path / "vid1xxxxxxx.mkv" and tep.kich_thuoc == 7


def test_tai_ten_cat_80_ky_tu_va_ky_tu_dieu_khien(tmp_path):
    v2 = "v2xxxxxxxxx"
    item = CrawlItem("youtube", v2, f"https://www.youtube.com/watch?v={v2}", tieu_de="a\tb\x01" + "x" * 100)
    tep = YoutubeAdapter(Nha(kich_ban=lambda y: _ghi(tmp_path / f"{v2}.mp4"))).tai(
        item, tmp_path, bao_tien_do=_khong_bao)
    ten = tep.ten_hien_thi
    assert ten.endswith(f" [{v2}].mp4") and "\t" not in ten and "\x01" not in ten
    assert len(ten[: -len(f" [{v2}].mp4")]) <= 80


def test_tai_khong_thay_tep(tmp_path):
    with pytest.raises(LoiCao) as e:
        YoutubeAdapter(Nha()).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "khong_thay_tep" and e.value.tam_thoi is True


def test_tai_download_error_duoc_phan_loai(tmp_path):
    nha = Nha(loi=DownloadError("ERROR: [youtube] vid1xxxxxxx: Private video. Sign in if you've been granted access"))
    with pytest.raises(LoiCao) as e:
        YoutubeAdapter(nha).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "rieng_tu" and e.value.tam_thoi is False


class HuyViec(Exception):
    pass


def test_tai_huy_lan_truyen_dung_ngoai_le_goc(tmp_path):
    """BLOCKER review: yt-dlp nuốt mọi exception hook trừ DownloadCancelled/CookieLoadError
    (yt_dlp 2026.03.17 `YoutubeDL.py:1699` chỉ ném lại hai loại đó; `:1717-1721` exception khác chỉ
    ném lại khi ignoreerrors tắt; `:3629-3631` lỗi post hook bị report_error; `:3648-3652`
    `__download_wrapper` ném lại DownloadCancelled). Hook phải đổi sang lớp con DownloadCancelled,
    rồi adapter ném lại ĐÚNG ngoại lệ gốc của bao_tien_do.
    """
    goc = HuyViec("khach huy")

    def bao(p, m):
        raise goc

    def kb(y):
        y.hook({"status": "downloading", "downloaded_bytes": 1, "total_bytes": 2})
        _ghi(tmp_path / "vid1xxxxxxx.mp4")

    nha = Nha(kich_ban=kb)
    with pytest.raises(HuyViec) as e:
        YoutubeAdapter(nha).tai(_ITEM, tmp_path, bao_tien_do=bao)
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
        YoutubeAdapter(nha).tai(_ITEM, tmp_path, bao_tien_do=bao)
    assert e.value is goc and isinstance(nha.tao[0].thay[0], DownloadCancelled)


def test_tuy_chon_ignoreerrors_tuong_minh_false(tmp_path):
    """spec §18: yt-dlp nuốt exception hook khi ignoreerrors bật — phải đặt False TƯỜNG MINH."""
    for o in (tuy_chon(), tuy_chon(thu_muc=tmp_path)):
        assert "ignoreerrors" in o and o["ignoreerrors"] is False


# ---------------------------------------------------------------- URL chuẩn (BLOCKER: URL bị sửa)
def test_url_video_va_id_hop_le():
    a = YoutubeAdapter()
    assert a.url_video("dQw4w9WgXcQ") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert a.id_hop_le("dQw4w9WgXcQ") and a.id_hop_le("a-b_c-d_e-f")
    for sai in ("", "ngan", "dQw4w9WgXcQx", "dQw4w9WgXc!", "dQw4w9WgXc&", "dQw4w9WgXc" + chr(10), None):
        assert not a.id_hop_le(sai), sai


@pytest.mark.parametrize("item", [
    CrawlItem("youtube", "vid1xxxxxxx", "https://www.youtube.com/playlist?list=PL123"),
    CrawlItem("youtube", "vid1xxxxxxx", "https://www.youtube.com/@kenh/videos"),
    CrawlItem("youtube", "vid1xxxxxxx", "https://www.youtube.com/watch?v=vid1xxxxxxx&list=PL123"),
    CrawlItem("youtube", "vid1xxxxxxx", "http://www.youtube.com/watch?v=vid1xxxxxxx"),
    CrawlItem("youtube", "vid1xxxxxxx", "https://www.youtube.com/watch?v=khacxxxxxxx"),
    CrawlItem("youtube", "x&list=PL12", "https://www.youtube.com/watch?v=x&list=PL12"),
])
def test_tai_tu_choi_url_khong_chuan(tmp_path, item):
    nha = Nha()
    with pytest.raises(LoiCao) as e:
        YoutubeAdapter(nha).tai(item, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro" and e.value.tam_thoi is False
    assert nha.tao == []          # không dựng YoutubeDL, không chạm mạng
