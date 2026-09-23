"""WeiboAdapter (spec §11, §18, §21) — không bao giờ chạm mạng: YoutubeDL giả được tiêm qua `ydl_factory`.

Nguồn:
- Donor: `docs/migrations/video_crawler/PLATFORM_MATRIX.md:30` (wb **ẩn** CSS `H:242`; search/link/channel `❓`,
  collection `❌`; backend chỉ `tim_anh` (ảnh) qua MediaCrawler — donor KHÔNG dùng yt-dlp cho weibo, không đọc/chép
  MediaCrawler, non-commercial); `docs/migrations/video_crawler/AUDIT_VIRAL_CAO_NGAY.md:155` (`_LINK_DOM`:
  `weibo.com | weibo.cn`).
- yt-dlp 2026.03.17 `yt_dlp/extractor/weibo.py`: `WeiboIE` (:133-134 `_VALID_URL`, :136-191 `_TESTS`),
  `WeiboVideoIE` (:212-217 `_VALID_URL`, :284-291 chỉ redirect `url_result` sang `WeiboIE` bằng
  `weibo.com/0/<mid>` — cũng là `_TESTS` thứ 3 của `WeiboIE` :182-184), `WeiboUserIE` (:294-295 `_VALID_URL`,
  :339-370 `_entries`/`_real_extract` — trả video ĐÃ trích đầy đủ, không phải mục phẳng, `playlist_mincount`
  195/61 ở `_TESTS` :296-313 xác nhận WeiboUser liệt kê video thật).
- GitHub `yt-dlp/yt-dlp` issue #13938 "weibo downloads broken - 403 forbidden" (đóng 2025-08-16 bởi PR #14012
  "[ie/weibo] Fix extractors") ⇒ 403 ẩn danh đã được vá bằng `_update_visitor_cookies` (weibo.py:24-54, sinh
  cookie khách qua `passport.weibo.com/visitor/genvisitor` khi bị redirect) — **không cần đăng nhập, không cần
  impersonate** để tải ẩn danh trên bản 2026.03.17 đã cài.
- Chế độ hỗ trợ = GIAO (donor có ∩ yt-dlp có extractor thật): `link` (WeiboIE/WeiboVideoIE) + `kenh`
  (WeiboUserIE liệt kê video thật). KHÔNG `tu_khoa` (yt-dlp không có `WeiboSearch`). KHÔNG `bo` (donor `❌`,
  yt-dlp không có extractor album/collection weibo).
"""
from __future__ import annotations

import re
import sys
import types

import pytest
import yt_dlp
from yt_dlp.extractor.weibo import WeiboIE, WeiboUserIE, WeiboVideoIE

from apps.video_crawler.adapters.base import CrawlItem, LoiCao, YeuCauCao
from apps.video_crawler.adapters.weibo import EXTRACTOR_CHO_PHEP, WeiboAdapter, chuan_hoa_kenh_weibo, tuy_chon


# ---------------------------------------------------------------- YoutubeDL giả (như test_1903, không mạng)
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
    return YeuCauCao(nen_tang="weibo", che_do=che_do, dau_vao=dau_vao, so_luong=n)


# Mid mẫu lấy trực tiếp từ `WeiboIE._TESTS` / `WeiboVideoIE._TESTS` (weibo.py) — số 16 chữ số.
_MID_1 = "4910815147462302"    # WeiboIE._TESTS[0]
_MID_2 = "4189191225395228"    # WeiboIE._TESTS[1] == WeiboVideoIE._TESTS[1]
_MID_3 = "4224132150961381"    # WeiboIE._TESTS[3] "no playback_list example" -> weibo.com/0/<mid>
_UID = "2066652961"            # WeiboUserIE._TESTS[0]


# ---------------------------------------------------------------- allowed_extractors
def test_allowed_extractors_chi_weibo_va_ton_tai_that():
    """IE_NAME phải thật (yt-dlp so `re.fullmatch` với `IE_NAME.lower()`, YoutubeDL.py:922-929)."""
    from yt_dlp.extractor import gen_extractor_classes

    ten_that = {ie.IE_NAME.lower() for ie in gen_extractor_classes()}
    ae = EXTRACTOR_CHO_PHEP
    assert ae and "generic" not in ae and "default" not in ae and "all" not in ae
    for ten in ae:
        assert ten in ten_that, ten
    assert {WeiboIE.IE_NAME.lower(), WeiboUserIE.IE_NAME.lower(), WeiboVideoIE.IE_NAME.lower()} == set(ae)
    assert tuy_chon()["allowed_extractors"] == list(ae)


def test_youtubedl_that_chi_nap_extractor_weibo():
    with yt_dlp.YoutubeDL(tuy_chon()) as y:
        ten = set(y._ies)
    assert ten and "Generic" not in ten
    assert all(k.lower().startswith("weibo") for k in ten), ten


def test_khong_co_extractor_tim_kiem_hay_bo_suu_tap():
    """Không `WeiboSearch`/album — cơ sở để loại `tu_khoa`/`bo` khỏi chế độ hỗ trợ."""
    from yt_dlp.extractor import gen_extractor_classes

    ten_weibo = {ie.IE_NAME for ie in gen_extractor_classes() if "weibo" in ie.IE_NAME.lower()}
    assert ten_weibo == {"Weibo", "WeiboUser", "WeiboVideo"}


def test_tuy_chon_khong_co_khoa_cam():
    o = tuy_chon()
    for khoa in ("nocheckcertificate", "cookiefile", "cookiesfrombrowser", "remote_components",
                 "download_archive", "exec", "exec_cmd", "netrc", "usenetrc"):
        assert khoa not in o
    assert o["ignoreerrors"] is False
    assert "impersonate" not in o          # weibo không cần impersonate (khác bilibili.tv/facebook)


def test_mac_dinh_nap_yt_dlp_luc_can(monkeypatch):
    goi = []
    gia = types.ModuleType("yt_dlp")
    gia.YoutubeDL = lambda opts: goi.append(opts) or "ydl"
    monkeypatch.setitem(sys.modules, "yt_dlp", gia)
    a = WeiboAdapter()
    assert a.nen_tang == "weibo"
    assert a._tao({"x": 1}) == "ydl" and goi == [{"x": 1}]


# ---------------------------------------------------------------- url_video / id_hop_le
def test_url_video_khop_valid_url_cua_weiboie():
    a = WeiboAdapter()
    for mid in (_MID_1, _MID_2, _MID_3):
        url = a.url_video(mid)
        assert url == f"https://weibo.com/0/{mid}"
        assert re.fullmatch(WeiboIE._VALID_URL, url), url


@pytest.mark.parametrize("mid", [_MID_1, _MID_2, _MID_3, "1234567890123"])
def test_id_hop_le_dung_voi_mid_so(mid):
    assert WeiboAdapter().id_hop_le(mid)


@pytest.mark.parametrize("sai", [
    "", "N4xlMvjhI", "abc", "12", "0" + _MID_1, "-" + _MID_1, _MID_1 + "x", _MID_1 + chr(10), None, 4910815147462302,
])
def test_id_hop_le_sai(sai):
    assert not WeiboAdapter().id_hop_le(sai), sai


# ---------------------------------------------------------------- url_kham_pha
def test_url_kham_pha_link_giu_nguyen():
    a = WeiboAdapter()
    url = f"https://weibo.com/0/{_MID_1}"
    assert a.url_kham_pha("link", url, 1) == url


@pytest.mark.parametrize("vao,ra", [
    (_UID, f"https://weibo.com/u/{_UID}"),
    (f"https://weibo.com/u/{_UID}", f"https://weibo.com/u/{_UID}"),
    (f"https://weibo.com/u/{_UID}?tabtype=video", f"https://weibo.com/u/{_UID}?tabtype=video"),
    (f"weibo.com/u/{_UID}", f"https://weibo.com/u/{_UID}"),
    ("", ""),
])
def test_url_kham_pha_kenh_chuan_hoa(vao, ra):
    assert WeiboAdapter().url_kham_pha("kenh", vao, 5) == ra
    assert chuan_hoa_kenh_weibo(vao) == ra


# ---------------------------------------------------------------- khám phá
def test_kham_pha_link_tra_mot_muc():
    url = f"https://weibo.com/0/{_MID_1}"
    nha = Nha(info={"id": _MID_1, "title": "T", "uploader": "U", "duration": 918.0,
                     "thumbnail": "https://x.sinaimg.cn/a.jpg"})
    ra = WeiboAdapter(nha).kham_pha(_yc("link", url, 5), bao_tien_do=_khong_bao)
    assert nha.tao[0].urls == [(url, False)]
    assert nha.tao[0].params["noplaylist"] is True
    assert ra == [CrawlItem(nen_tang="weibo", id=_MID_1, url=url, tieu_de="T", tac_gia="U",
                            thoi_luong_s=918, anh_bia="https://x.sinaimg.cn/a.jpg")]


def test_kham_pha_kenh_anh_xa_danh_sach_video_that():
    """WeiboUserIE trả video ĐÃ trích đầy đủ (không phẳng) — mô phỏng đúng hình dạng đó."""
    url = f"https://weibo.com/u/{_UID}"
    nha = Nha(info={"_type": "playlist", "id": _UID, "entries": [
        {"id": _MID_2, "title": "A", "uploader": "U1", "duration": 53, "thumbnail": "https://t/1.jpg"},
        {"id": _MID_3, "title": "B", "uploader": "U2", "duration": None,
         "thumbnails": [{"url": "https://t/2.jpg"}, {"url": "https://t/3.jpg"}]},
    ]})
    ra = WeiboAdapter(nha).kham_pha(_yc("kenh", _UID, 5), bao_tien_do=_khong_bao)
    assert nha.tao[0].urls == [(url, False)]
    assert ra == [
        CrawlItem("weibo", _MID_2, f"https://weibo.com/0/{_MID_2}", "A", "U1", 53, "https://t/1.jpg"),
        CrawlItem("weibo", _MID_3, f"https://weibo.com/0/{_MID_3}", "B", "U2", None, "https://t/3.jpg"),
    ]


def test_kham_pha_bo_muc_khong_id_hop_le():
    nha = Nha(info={"_type": "playlist", "id": _UID, "entries": [
        None, {"title": "khong id"}, {"id": "ngan"}, {"id": _MID_2}, {"id": _MID_3},
    ]})
    ra = WeiboAdapter(nha).kham_pha(_yc("kenh", _UID, 1), bao_tien_do=_khong_bao)
    assert [m.id for m in ra] == [_MID_2]     # id sai dạng bị bỏ, cắt theo n=1


def test_kham_pha_download_error_duoc_phan_loai():
    from yt_dlp.utils import DownloadError

    nha = Nha(loi=DownloadError("ERROR: [Weibo] x: Unable to download webpage: HTTP Error 403: Forbidden"))
    with pytest.raises(LoiCao) as e:
        WeiboAdapter(nha).kham_pha(_yc("kenh", _UID), bao_tien_do=_khong_bao)
    assert e.value.ma == "yt_403" and e.value.tam_thoi is True


# ---------------------------------------------------------------- tải (BLOCKER: URL bị sửa)
_ITEM = CrawlItem("weibo", _MID_1, f"https://weibo.com/0/{_MID_1}", tieu_de="T")


@pytest.mark.parametrize("item", [
    CrawlItem("weibo", _MID_1, f"http://weibo.com/0/{_MID_1}"),                    # http, không https
    CrawlItem("weibo", _MID_1, f"https://weibo.com/123456789/{_MID_1}"),           # dạng mblogid, không canonical
    CrawlItem("weibo", _MID_1, f"https://m.weibo.cn/status/{_MID_1}"),             # domain khác canonical
    CrawlItem("weibo", _MID_1, f"https://weibo.com/0/{_MID_2}"),                   # id trong url khác item.id
    CrawlItem("weibo", "N4xlMvjhI", "https://weibo.com/123456789/N4xlMvjhI"),      # id không hợp lệ (mblogid)
    CrawlItem("weibo", _MID_1, f"https://weibo.com/u/{_UID}"),                     # link kênh, không phải video
])
def test_tai_tu_choi_url_khong_chuan(tmp_path, item):
    nha = Nha()
    with pytest.raises(LoiCao) as e:
        WeiboAdapter(nha).tai(item, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro" and e.value.tam_thoi is False
    assert nha.tao == []


def test_tai_chap_nhan_url_chuan(tmp_path):
    def kb_ydl_factory(opts):
        class _Y(FakeYDL):
            def download(self, urls):
                self.urls.append((list(urls), True))
                (tmp_path / f"{_MID_1}.mp4").write_bytes(b"x" * 5)
                for h in self.params.get("progress_hooks", []):
                    h({"status": "finished", "filename": str(tmp_path / f"{_MID_1}.mp4")})
                return 0
        return _Y(opts)

    tep = WeiboAdapter(kb_ydl_factory).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert tep.duong_dan == tmp_path / f"{_MID_1}.mp4"
