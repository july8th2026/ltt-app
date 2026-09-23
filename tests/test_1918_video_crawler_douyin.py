"""DouyinAdapter (spec §11, §18, §21) — không bao giờ chạm mạng: YoutubeDL giả được tiêm qua
`ydl_factory`, và các khẳng định về extractor thật chỉ tra `yt_dlp.extractor` đã cài (không mạng).

Nguồn:
- Donor `docs/migrations/video_crawler/PLATFORM_MATRIX.md:19` (dòng `dy`): search/link/channel/
  collection đều đi qua MediaCrawler (giấy phép NON-COMMERCIAL — KHÔNG đọc/copy); link tự chuẩn hoá
  `modal_id`/`vid`/`note` ⇒ `douyin.com/video/<id>`; đăng nhập QR, cookie `sessionid`/`sessionid_ss`/
  `sid_tt`; `DOUYIN_NEED_LOGIN` (2483) khi search; khoá dedup `aweme_id`.
- `docs/migrations/video_crawler/AUDIT_VIRAL_CAO_NGAY.md` §7 (`W:4408-4436`): Douyin `modal_id`/`vid`/
  `/note/<id>` ⇒ `douyin.com/video/<id>`, khử trùng giữ thứ tự.
- yt-dlp 2026.03.17 đã cài, `site-packages/yt_dlp/extractor/tiktok.py:1351-1489` (`DouyinIE`):
  `_VALID_URL = r'https?://(?:www\\.)?douyin\\.com/video/(?P<id>[0-9]+)'`; `IE_NAME`/`ie_key()` ==
  `"Douyin"`; `_TESTS` (:1353-1471) toàn id 19 chữ số; `_real_extract` (:1475-1488) gọi
  `aweme/v1/web/aweme/detail/` rồi `raise ExtractorError('Fresh cookies (not necessarily logged in)
  are needed', ...)` khi JSON rỗng — KHÔNG dùng `impersonate=True` (khác bilibili.tv/facebook).
  yt-dlp chỉ có extractor MỘT video cho Douyin — không có search/user/channel (xem
  `yt-dlp/yt-dlp#2120` "Add DouyinUserIE", vẫn mở) và cookie "tươi" hay hỏng theo thời gian
  (`yt-dlp/yt-dlp#16867` "[Douyin] Fresh cookies issue with valid cookies on nightly").
"""
from __future__ import annotations

import re
import types
import sys
from pathlib import Path

import pytest
import yt_dlp
from yt_dlp.utils import DownloadError

from apps.video_crawler.adapters.base import CrawlItem, LoiCao, TepTai, YeuCauCao
from apps.video_crawler.adapters.douyin import DouyinAdapter, tuy_chon


# ---------------------------------------------------------------- YoutubeDL giả (như test_1903)
class FakeYDL:
    def __init__(self, opts, *, info=None, loi=None, kich_ban=None):
        self.params = opts
        self.info = info
        self.loi = loi
        self.kich_ban = kich_ban
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
        if self.kich_ban:
            self.kich_ban(self)
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


def _yc(che_do, dau_vao, n=5):
    return YeuCauCao(nen_tang="douyin", che_do=che_do, dau_vao=dau_vao, so_luong=n)


# id mẫu lấy trực tiếp từ `DouyinIE._TESTS` đã cài (không gõ tay).
def _ids_that() -> list[str]:
    from yt_dlp.extractor.tiktok import DouyinIE

    return [re.match(DouyinIE._VALID_URL, t["url"])["id"] for t in DouyinIE._TESTS]


_ID_THAT = _ids_that()


# ---------------------------------------------------------------- allowed_extractors / cấu hình
def test_allowed_extractors_chi_douyin_va_ton_tai_that():
    from yt_dlp.extractor import gen_extractor_classes

    ten_that = {ie.IE_NAME.lower() for ie in gen_extractor_classes()}
    ae = tuy_chon()["allowed_extractors"]
    assert ae == ["douyin"]
    assert "generic" not in ae and "default" not in ae and "all" not in ae
    for ten in ae:
        assert ten.replace("\\", "") in ten_that, ten


def test_youtubedl_that_chi_nap_extractor_douyin():
    with yt_dlp.YoutubeDL(tuy_chon()) as y:
        ten = set(y._ies)
    assert ten == {"Douyin"}


def test_tuy_chon_khong_impersonate_khong_extractor_args():
    o = tuy_chon()
    assert "impersonate" not in o     # DouyinIE._real_extract không dùng impersonate=True
    assert "extractor_args" not in o  # không extractor_args nào được biết cần cho Douyin


@pytest.mark.parametrize("khoa", [
    "nocheckcertificate", "cookiefile", "cookiesfrombrowser", "remote_components",
    "download_archive", "exec", "exec_cmd", "netrc", "usenetrc",
])
def test_tuy_chon_khong_co_khoa_cam(khoa):
    assert khoa not in tuy_chon()
    assert khoa not in tuy_chon(thu_muc=Path("x"))


def test_tuy_chon_ignoreerrors_tuong_minh_false(tmp_path):
    for o in (tuy_chon(), tuy_chon(thu_muc=tmp_path)):
        assert "ignoreerrors" in o and o["ignoreerrors"] is False


def test_mac_dinh_nap_youtubedl_luc_can(monkeypatch):
    goi = []
    gia = types.ModuleType("yt_dlp")
    gia.YoutubeDL = lambda opts: goi.append(opts) or "ydl"
    monkeypatch.setitem(sys.modules, "yt_dlp", gia)
    a = DouyinAdapter()
    assert a.nen_tang == "douyin"
    assert a._tao({"x": 1}) == "ydl" and goi == [{"x": 1}]


# ---------------------------------------------------------------- id_hop_le / url_video (BLOCKER: URL bị sửa)
def test_id_hop_le_dung_voi_id_that_cua_extractor():
    a = DouyinAdapter()
    for vid in _ID_THAT:
        assert len(vid) == 19, vid          # ghi lại sự thật: mẫu _TESTS toàn 19 chữ số
        assert a.id_hop_le(vid)


@pytest.mark.parametrize("sai", [
    "", "123", "1" * 18, "1" * 20, "a" * 19, "1234567891234567x",
    "1234567891234567 ", None, 6961737553342991651,
])
def test_id_hop_le_sai(sai):
    assert not DouyinAdapter().id_hop_le(sai)


def test_url_video_khop_valid_url_that_cua_extractor():
    from yt_dlp.extractor.tiktok import DouyinIE

    a = DouyinAdapter()
    for vid in _ID_THAT:
        url = a.url_video(vid)
        assert url == f"https://www.douyin.com/video/{vid}"
        m = re.fullmatch(DouyinIE._VALID_URL, url)
        assert m is not None and m["id"] == vid


# ---------------------------------------------------------------- url_kham_pha (chế độ link)
@pytest.mark.parametrize("vao,id_ky_vong", [
    ("https://www.douyin.com/video/6961737553342991651", "6961737553342991651"),
    ("http://douyin.com/video/6961737553342991651", "6961737553342991651"),
    ("https://www.douyin.com/discover?modal_id=6982497745948921092", "6982497745948921092"),
    ("https://www.douyin.com/user/abc?vid=6953975910773099811", "6953975910773099811"),
    ("https://www.douyin.com/note/6963263655114722595", "6963263655114722595"),
])
def test_url_kham_pha_link_chuan_hoa_modal_id_vid_note(vao, id_ky_vong):
    ra = DouyinAdapter().url_kham_pha("link", vao, 1)
    assert ra == f"https://www.douyin.com/video/{id_ky_vong}"


def test_url_kham_pha_link_khong_khop_giu_nguyen():
    """Không có dạng id THẬT nào khớp (vd v.douyin.com rút gọn — yt-dlp không có extractor cho nó,
    xem báo cáo lane) ⇒ giữ nguyên, để `kham_pha`/`tai` tự từ chối qua yt-dlp/`id_hop_le`."""
    vao = "https://v.douyin.com/abc123/"
    assert DouyinAdapter().url_kham_pha("link", vao, 1) == vao


@pytest.mark.parametrize("che_do", ["tu_khoa", "kenh", "bo"])
def test_url_kham_pha_che_do_khac_chua_ho_tro(che_do):
    """`url_kham_pha` (đường yt-dlp) chỉ phục vụ `link`; tu_khoa/kenh đi client web riêng
    (`test_1928_video_crawler_douyin_tim.py`), `bo` chưa làm."""
    with pytest.raises(NotImplementedError):
        DouyinAdapter().url_kham_pha(che_do, "x", 5)


# ---------------------------------------------------------------- khám phá
def test_kham_pha_link_tra_mot_muc():
    url = "https://www.douyin.com/video/6961737553342991651"
    nha = Nha(info={"id": "6961737553342991651", "title": "T", "uploader": "U", "duration": 19.0})
    ra = DouyinAdapter(nha).kham_pha(_yc("link", url, 5), bao_tien_do=_khong_bao)
    assert nha.tao[0].urls == [(url, False)]
    assert nha.tao[0].params["noplaylist"] is True
    assert ra == [CrawlItem(nen_tang="douyin", id="6961737553342991651", url=url,
                            tieu_de="T", tac_gia="U", thoi_luong_s=19, anh_bia="")]


def test_kham_pha_link_chuan_hoa_modal_id_truoc_khi_goi_ydl():
    vao = "https://www.douyin.com/discover?modal_id=6982497745948921092"
    nha = Nha(info={"id": "6982497745948921092", "title": "T"})
    DouyinAdapter(nha).kham_pha(_yc("link", vao, 1), bao_tien_do=_khong_bao)
    assert nha.tao[0].urls == [("https://www.douyin.com/video/6982497745948921092", False)]


def test_kham_pha_bo_id_khong_hop_le():
    nha = Nha(info={"id": "khong-hop-le", "title": "x"})
    ra = DouyinAdapter(nha).kham_pha(
        _yc("link", "https://www.douyin.com/video/6961737553342991651", 1), bao_tien_do=_khong_bao)
    assert ra == []


def test_kham_pha_download_error_duoc_phan_loai():
    """DouyinIE ném ExtractorError 'Fresh cookies (not necessarily logged in) are needed'
    (`tiktok.py:1483-1486`) — phía yt-dlp bọc thành DownloadError; phải phân loại được, không vỡ."""
    nha = Nha(loi=DownloadError("ERROR: [Douyin] 123: Fresh cookies (not necessarily logged in) are needed"))
    with pytest.raises(LoiCao) as e:
        DouyinAdapter(nha).kham_pha(
            _yc("link", "https://www.douyin.com/video/6961737553342991651", 1), bao_tien_do=_khong_bao)
    # Smoke thật 22/09: thử lại ẩn danh không bao giờ khỏi ⇒ `can_dang_nhap`, không retry (loi.py).
    assert e.value.ma == "can_dang_nhap" and e.value.tam_thoi is False


# ---------------------------------------------------------------- tải
_ITEM = CrawlItem("douyin", "6961737553342991651",
                  "https://www.douyin.com/video/6961737553342991651", tieu_de='Mèo: "con"/<to>?*|')


def _ghi(p: Path, n=10) -> Path:
    p.write_bytes(b"x" * n)
    return p


def test_tai_tra_tep_tu_hook_va_ten_hien_thi_sach(tmp_path):
    that = tmp_path / "6961737553342991651.mp4"

    def kb(y):
        _ghi(that, 42)
        y.pp_hook({"status": "finished", "postprocessor": "MoveFiles", "info_dict": {"filepath": str(that)}})

    tep = DouyinAdapter(Nha(kich_ban=kb)).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert tep == TepTai(duong_dan=that, kich_thuoc=42,
                         ten_hien_thi="Mèo con to [6961737553342991651].mp4")


def test_tai_khong_thay_tep(tmp_path):
    with pytest.raises(LoiCao) as e:
        DouyinAdapter(Nha()).tai(_ITEM, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "khong_thay_tep" and e.value.tam_thoi is True


@pytest.mark.parametrize("item", [
    CrawlItem("douyin", "6961737553342991651", "https://www.douyin.com/discover?modal_id=6961737553342991651"),
    CrawlItem("douyin", "6961737553342991651", "http://www.douyin.com/video/6961737553342991651"),
    CrawlItem("douyin", "6961737553342991651", "https://www.douyin.com/video/6961737553342991651?x=1"),
    CrawlItem("douyin", "6961737553342991651", "https://www.douyin.com/video/khac1234567890123"),
    CrawlItem("douyin", "123", "https://www.douyin.com/video/123"),
    CrawlItem("douyin", "6961737553342991651", "https://v.douyin.com/abc123/"),
])
def test_tai_tu_choi_url_khong_chuan(tmp_path, item):
    nha = Nha()
    with pytest.raises(LoiCao) as e:
        DouyinAdapter(nha).tai(item, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro" and e.value.tam_thoi is False
    assert nha.tao == []          # không dựng YoutubeDL, không chạm mạng
