"""BilibiliTvAdapter (spec §11, §18, §21) — không bao giờ chạm mạng: YoutubeDL giả tiêm qua `ydl_factory`.

Donor CHỈ hỗ trợ chế độ "Theo link" cho `bilitv` — không tìm-theo-từ-khoá, không trang cá nhân,
không "Theo bộ" (PLATFORM_MATRIX dòng `bilitv`: search ❌, channel ❌, collection ❌, link ✅ duy nhất;
donor `Y:1655-1661` chặn CLI khi `a.type != "detail"`). Không impersonate ⇒ `www.bilibili.tv` RESET kết
nối giữa chừng, đo 0/9 lượt lấy metadata; có `impersonate=chrome` ⇒ 6/6 (`Y:2126-2135`).

Nguồn characterization yt-dlp 2026.03.17 (site-packages `yt_dlp/extractor/bilibili.py`):
- `BiliIntlIE` (:2192-2193): `_VALID_URL` khớp `/play/<season_id>/<ep_id>` (một tập) HOẶC `/video/<aid>`
  (video độc lập); `IE_NAME` tự suy = "BiliIntl".
- `_real_extract` (:2430): `video_id = ep_id or aid` — season_id CHỈ dùng nội bộ để gọi API, KHÔNG có
  trong info-dict trả về ⇒ không đủ để `url_video(id)` dựng lại URL `/play/...` gốc.
- `BiliIntlSeriesIE` (:2463, IE_NAME "biliIntl:series"): trích danh sách tập của một season = "Theo bộ",
  donor không hỗ trợ ⇒ không nằm trong `allowed_extractors`.
"""
from __future__ import annotations

import pytest
import yt_dlp
from yt_dlp.extractor.bilibili import BiliIntlIE, BiliIntlSeriesIE

from apps.video_crawler.adapters.base import CrawlItem, LoiCao, YeuCauCao
from apps.video_crawler.adapters.bilibili_tv import EXTRACTOR_CHO_PHEP, BilibiliTvAdapter


# ---------------------------------------------------------------- YoutubeDL giả (rút gọn từ test_1903)
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
    return YeuCauCao(nen_tang="bilibili_tv", che_do=che_do, dau_vao=dau_vao, so_luong=n)


# Link mẫu từ chính `_TESTS` của extractor (site-packages, không phải link tự bịa).
_URL_AID = "https://www.bilibili.tv/en/video/2045730385"
_URL_AID_TRAN = "https://www.bilibili.tv/video/2019955076"
_URL_EP = "https://www.bilibili.tv/en/play/34613/341736"
_URL_SERIES_PLAY = "https://www.bilibili.tv/en/play/34613"
_URL_SERIES_MEDIA = "https://www.bilibili.tv/en/media/1048837"


# ---------------------------------------------------------------- allowed_extractors thật
def test_allowed_extractors_ton_tai_that_va_khong_generic():
    from yt_dlp.extractor import gen_extractor_classes

    ten_that = {ie.IE_NAME.lower() for ie in gen_extractor_classes()}
    ae = EXTRACTOR_CHO_PHEP
    assert ae and "generic" not in ae and "default" not in ae and "all" not in ae
    for ten in ae:
        assert ten.lower() in ten_that, ten
    assert BiliIntlIE.IE_NAME.lower() in [t.lower() for t in ae]
    # BLOCKER nếu lọt vào: extractor liệt kê cả season (donor không hỗ trợ "Theo bộ").
    assert BiliIntlSeriesIE.IE_NAME.lower() not in [t.lower() for t in ae]


def test_youtubedl_that_chi_nap_biliintl():
    with yt_dlp.YoutubeDL(BilibiliTvAdapter.tuy_chon_goc()) as y:
        ten = set(y._ies)
    assert ten == {"BiliIntl"}


def test_impersonate_bat():
    assert BilibiliTvAdapter.impersonate is True


# ---------------------------------------------------------------- id_hop_le (mẫu id từ _TESTS)
def test_id_hop_le_dung_voi_id_video_doc_lap():
    a = BilibiliTvAdapter()
    for vid in ("2045730385", "2019955076", "341736", "0"):
        assert a.id_hop_le(vid), vid


@pytest.mark.parametrize("sai", ["", "34613/341736", "abc", "2045730385x", " 2045730385", None, 12345])
def test_id_hop_le_sai(sai):
    a = BilibiliTvAdapter()
    assert not a.id_hop_le(sai), sai


# ---------------------------------------------------------------- url_video khớp _VALID_URL thật
def test_url_video_khop_valid_url_cua_extractor():
    a = BilibiliTvAdapter()
    url = a.url_video("2045730385")
    assert url == "https://www.bilibili.tv/video/2045730385"
    m = BiliIntlIE._match_valid_url(url)
    assert m is not None and m.group("aid") == "2045730385"
    assert m.group("season_id") is None and m.group("ep_id") is None


# ---------------------------------------------------------------- url_kham_pha
def test_url_kham_pha_link_video_doc_lap_giu_nguyen():
    a = BilibiliTvAdapter()
    assert a.url_kham_pha("link", _URL_AID, 5) == _URL_AID
    assert a.url_kham_pha("link", _URL_AID_TRAN, 5) == _URL_AID_TRAN


@pytest.mark.parametrize("url", [_URL_EP, _URL_SERIES_PLAY, _URL_SERIES_MEDIA, "khong phai url", ""])
def test_url_kham_pha_tu_choi_dang_khong_du_de_dung_lai(url):
    """BLOCKER nếu cho qua: link '/play/<season>/<ep>' trích ra `id=ep_id`, nhưng season_id không có
    trong info-dict (bilibili.py:2430) ⇒ `url_video(ep_id)` dựng SAI URL (đổi sang endpoint aid=ep_id).
    """
    a = BilibiliTvAdapter()
    with pytest.raises(LoiCao) as e:
        a.url_kham_pha("link", url, 5)
    assert e.value.ma == "url_khong_ho_tro" and e.value.tam_thoi is False


# ---------------------------------------------------------------- khám phá (che_do link -> 1 mục)
def test_kham_pha_link_tra_mot_muc():
    nha = Nha(info={"id": "2045730385", "title": "T", "uploader": "U", "duration": 42.9,
                     "thumbnail": "https://pic.bstarstatic.com/a.png"})
    ra = BilibiliTvAdapter(nha).kham_pha(_yc("link", _URL_AID, 5), bao_tien_do=_khong_bao)
    y = nha.tao[0]
    assert y.urls == [(_URL_AID, False)]
    assert y.params["noplaylist"] is True
    assert y.params["allowed_extractors"] == list(EXTRACTOR_CHO_PHEP)
    assert ra == [CrawlItem(nen_tang="bilibili_tv", id="2045730385",
                            url="https://www.bilibili.tv/video/2045730385",
                            tieu_de="T", tac_gia="U", thoi_luong_s=42,
                            anh_bia="https://pic.bstarstatic.com/a.png")]


def test_kham_pha_link_bo_muc_id_khong_hop_le():
    nha = Nha(info={"id": "ngan-khong-so", "title": "x"})
    ra = BilibiliTvAdapter(nha).kham_pha(_yc("link", _URL_AID, 5), bao_tien_do=_khong_bao)
    assert ra == []


def test_kham_pha_tu_choi_truoc_khi_dung_yt_dlp():
    """`url_kham_pha` phải chặn TRƯỚC khi dựng YoutubeDL — không âm thầm cào nhầm season/episode."""
    nha = Nha()
    with pytest.raises(LoiCao) as e:
        BilibiliTvAdapter(nha).kham_pha(_yc("link", _URL_EP, 5), bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro"
    assert nha.tao == []


# ---------------------------------------------------------------- tải: từ chối URL không chuẩn
_ITEM_OK = CrawlItem("bilibili_tv", "2045730385", "https://www.bilibili.tv/video/2045730385", tieu_de="T")


@pytest.mark.parametrize("item", [
    CrawlItem("bilibili_tv", "341736", "https://www.bilibili.tv/en/play/34613/341736"),
    CrawlItem("bilibili_tv", "2045730385", "https://www.bilibili.tv/en/video/2045730385"),  # khác domain-path chuẩn
    CrawlItem("bilibili_tv", "2045730385", "http://www.bilibili.tv/video/2045730385"),      # http, không https
    CrawlItem("bilibili_tv", "2045730385", "https://www.bilibili.tv/video/khac"),
    CrawlItem("bilibili_tv", "34613", "https://www.bilibili.tv/en/play/34613"),
])
def test_tai_tu_choi_url_khong_chuan(tmp_path, item):
    nha = Nha()
    with pytest.raises(LoiCao) as e:
        BilibiliTvAdapter(nha).tai(item, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro" and e.value.tam_thoi is False
    assert nha.tao == []          # không dựng YoutubeDL, không chạm mạng


def test_tai_chap_nhan_url_chuan(tmp_path):
    def kb():
        (tmp_path / "2045730385.mp4").write_bytes(b"x" * 5)

    class FakeYDLTai(FakeYDL):
        def download(self, urls):
            self.urls.append((list(urls), True))
            kb()
            return 0

    nha = Nha()
    nha.kw = {}
    nha_factory = lambda opts: FakeYDLTai(opts)
    tep = BilibiliTvAdapter(nha_factory).tai(_ITEM_OK, tmp_path, bao_tien_do=_khong_bao)
    assert tep.duong_dan == tmp_path / "2045730385.mp4"
