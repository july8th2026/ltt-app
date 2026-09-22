"""XiaohongshuAdapter (spec Sec.11, Sec.18, Sec.19, Sec.21) — khong bao gio cham mang.

Nguon characterization:
- yt-dlp `yt_dlp/extractor/xiaohongshu.py` (XiaoHongShuIE), dong 13-41 (`_VALID_URL`, `_TESTS`).
- Id/token mau thuc te (khong bia): `_TESTS` dong 17, 30; issue yt-dlp/yt-dlp#13728 (comment goc,
  URL `explore/644f0a200000000013030186?xsec_token=ABbpHsLUVDfzFGQhVGvLVuGvU3I6sq5eTi_zhlKGjCbmk=`);
  issue yt-dlp/yt-dlp#16519 (URL `explore/69ce30d3000000002100791c?xsec_token=ABQNiuPr9iBog5WzaYReZHkB_M-H0_ueF_FpSximzkuxc=`).
- Donor: `docs/migrations/video_crawler/PLATFORM_MATRIX.md` dong 24 (cot `link`: bat buoc xsec_token);
  `docs/migrations/video_crawler/AUDIT_VIRAL_CAO_NGAY.md` Sec.0 dong 21 (creator/detail di trinh duyet).
"""
from __future__ import annotations

import re
import sys
import types

import pytest
import yt_dlp
from yt_dlp.extractor.xiaohongshu import XiaoHongShuIE

from apps.video_crawler.adapters.base import CrawlItem, LoiCao, YeuCauCao
from apps.video_crawler.adapters.xiaohongshu import EXTRACTOR_CHO_PHEP, XiaohongshuAdapter

# ---------------------------------------------------------------- id/token mau thuc (khong bia)
NOTE_1 = "6411cf99000000001300b6d9"                                    # _TESTS[0]
NOTE_2, TOKEN_2 = "674051740000000007027a15", "CBgeL8Dxd1ZWBhwqRd568gAZ_iwG-9JIf9tnApNmteU2E="  # _TESTS[1]
NOTE_3, TOKEN_3 = "644f0a200000000013030186", "ABbpHsLUVDfzFGQhVGvLVuGvU3I6sq5eTi_zhlKGjCbmk="  # issue #13728
NOTE_4, TOKEN_4 = "69ce30d3000000002100791c", "ABQNiuPr9iBog5WzaYReZHkB_M-H0_ueF_FpSximzkuxc="  # issue #16519


def _khong_bao(pct, msg):
    pass


def _yc(che_do, dau_vao, n=5):
    return YeuCauCao(nen_tang="xiaohongshu", che_do=che_do, dau_vao=dau_vao, so_luong=n)


# ---------------------------------------------------------------- allowed_extractors
def test_allowed_extractors_ton_tai_that_va_khong_generic():
    from yt_dlp.extractor import gen_extractor_classes

    ten_that = {ie.IE_NAME.lower() for ie in gen_extractor_classes()}
    ae = XiaohongshuAdapter.tuy_chon_goc()["allowed_extractors"]
    assert ae and "generic" not in ae and "default" not in ae and "all" not in ae
    for ten in ae:
        assert ten in ten_that, ten
    assert EXTRACTOR_CHO_PHEP == ("xiaohongshu",)


def test_youtubedl_that_chi_nap_extractor_xiaohongshu():
    with yt_dlp.YoutubeDL(XiaohongshuAdapter.tuy_chon_goc()) as y:
        ten = set(y._ies)
    assert ten == {"XiaoHongShu"}


def test_khong_co_extractor_search_hoac_user_cho_xiaohongshu():
    """Xac nhan yt-dlp KHONG co extractor search/creator cho xhs — GIAO voi donor chi con "link"."""
    from yt_dlp.extractor import gen_extractor_classes

    ten = [ie.IE_NAME for ie in gen_extractor_classes() if "xiaohongshu" in ie.IE_NAME.lower()]
    assert ten == ["XiaoHongShu"]


def test_rednote_khong_duoc_yt_dlp_ho_tro():
    """RedNote (quoc te): khong extractor nao, khong domain nao trong yt-dlp da cai — issue #16519 (mo)."""
    from yt_dlp.extractor import gen_extractor_classes

    ten = [ie.IE_NAME for ie in gen_extractor_classes() if "rednote" in ie.IE_NAME.lower()]
    assert ten == []
    assert re.match(XiaoHongShuIE._VALID_URL, "https://www.rednote.com/explore/" + NOTE_1) is None


# ---------------------------------------------------------------- id_hop_le / url_video
def test_id_hop_le_note_thuan_va_note_token():
    a = XiaohongshuAdapter()
    assert a.id_hop_le(NOTE_1)
    assert a.id_hop_le(f"{NOTE_2}:{TOKEN_2}")
    assert a.id_hop_le(f"{NOTE_3}:{TOKEN_3}")
    assert a.id_hop_le(f"{NOTE_4}:{TOKEN_4}")


@pytest.mark.parametrize("sai", [
    "", "ngan", "G" * 24, NOTE_1.upper(), NOTE_1 + "x", NOTE_1 + ":",
    NOTE_1 + ":" + "a" * 5, NOTE_1 + ":" + "*" * 44, NOTE_1 + "\n", None, 123,
])
def test_id_hop_le_tu_choi_sai(sai):
    assert not XiaohongshuAdapter().id_hop_le(sai), sai


def test_url_video_note_thuan():
    a = XiaohongshuAdapter()
    url = a.url_video(NOTE_1)
    assert url == f"https://www.xiaohongshu.com/explore/{NOTE_1}"
    assert re.match(XiaoHongShuIE._VALID_URL, url) is not None


def test_url_video_note_va_token_khop_valid_url_va_giu_token():
    a = XiaohongshuAdapter()
    url = a.url_video(f"{NOTE_2}:{TOKEN_2}")
    assert url == f"https://www.xiaohongshu.com/explore/{NOTE_2}?xsec_token={TOKEN_2}"
    m = re.match(XiaoHongShuIE._VALID_URL, url)
    assert m is not None and m.group("id") == NOTE_2
    assert f"xsec_token={TOKEN_2}" in url


# ---------------------------------------------------------------- url_kham_pha
def test_url_kham_pha_link_tra_nguyen_url_khach_dan():
    a = XiaohongshuAdapter()
    url = f"https://www.xiaohongshu.com/discovery/item/{NOTE_2}?xsec_token={TOKEN_2}"
    assert a.url_kham_pha("link", url, 1) == url


# ---------------------------------------------------------------- kham_pha (fake YoutubeDL)
class FakeYDL:
    def __init__(self, opts, *, info=None):
        self.params = opts
        self.info = info
        self.urls: list = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=True):
        self.urls.append((url, download))
        return self.info


class Nha:
    def __init__(self, **kw):
        self.kw = kw
        self.tao: list[FakeYDL] = []

    def __call__(self, opts):
        y = FakeYDL(opts, **self.kw)
        self.tao.append(y)
        return y


def test_mac_dinh_nap_yt_dlp_luc_can(monkeypatch):
    goi = []
    gia = types.ModuleType("yt_dlp")
    gia.YoutubeDL = lambda opts: goi.append(opts) or "ydl"
    monkeypatch.setitem(sys.modules, "yt_dlp", gia)
    a = XiaohongshuAdapter()
    assert a.nen_tang == "xiaohongshu"
    assert a._tao({"x": 1}) == "ydl" and goi == [{"x": 1}]


def test_kham_pha_link_gan_token_tu_webpage_url():
    url = f"https://www.xiaohongshu.com/discovery/item/{NOTE_2}?xsec_token={TOKEN_2}"
    info = {
        "id": NOTE_2, "webpage_url": url, "title": "T", "uploader_id": "u1",
        "duration": 28.073, "thumbnails": [{"url": "https://sns-webpic-qc.xhscdn.com/1/a/b"}],
    }
    nha = Nha(info=info)
    ra = XiaohongshuAdapter(nha).kham_pha(_yc("link", url, 5), bao_tien_do=_khong_bao)
    assert nha.tao[0].urls == [(url, False)]
    assert ra == [CrawlItem(
        nen_tang="xiaohongshu", id=f"{NOTE_2}:{TOKEN_2}",
        url=f"https://www.xiaohongshu.com/explore/{NOTE_2}?xsec_token={TOKEN_2}",
        tieu_de="T", tac_gia="u1", thoi_luong_s=28,
        anh_bia="https://sns-webpic-qc.xhscdn.com/1/a/b",
    )]


def test_kham_pha_link_khong_co_token_trong_url_van_ra_muc_nhung_id_khong_token():
    url = f"https://www.xiaohongshu.com/explore/{NOTE_1}"
    info = {"id": NOTE_1, "webpage_url": url, "title": "A", "duration": 101.726}
    nha = Nha(info=info)
    ra = XiaohongshuAdapter(nha).kham_pha(_yc("link", url, 5), bao_tien_do=_khong_bao)
    assert ra == [CrawlItem(
        nen_tang="xiaohongshu", id=NOTE_1,
        url=f"https://www.xiaohongshu.com/explore/{NOTE_1}",
        tieu_de="A", tac_gia="", thoi_luong_s=101,
    )]


# ---------------------------------------------------------------- tai (BLOCKER: URL bi sua)
@pytest.mark.parametrize("item", [
    CrawlItem("xiaohongshu", f"{NOTE_2}:{TOKEN_2}", "https://www.xiaohongshu.com/explore/" + NOTE_3),
    CrawlItem("xiaohongshu", NOTE_2, f"https://www.xiaohongshu.com/explore/{NOTE_2}?xsec_token={TOKEN_2}"),
    CrawlItem("xiaohongshu", f"{NOTE_2}:{TOKEN_2}", f"http://www.xiaohongshu.com/explore/{NOTE_2}?xsec_token={TOKEN_2}"),
    CrawlItem("xiaohongshu", f"{NOTE_2}:{TOKEN_2}", "https://www.rednote.com/explore/" + NOTE_2 + "?xsec_token=" + TOKEN_2),
    CrawlItem("xiaohongshu", NOTE_1 + ":bad", f"https://www.xiaohongshu.com/explore/{NOTE_1}?xsec_token=bad"),
])
def test_tai_tu_choi_url_khong_chuan(tmp_path, item):
    nha = Nha()
    with pytest.raises(LoiCao) as e:
        XiaohongshuAdapter(nha).tai(item, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro" and e.value.tam_thoi is False
    assert nha.tao == []
