"""Tìm KÊNH theo tên (làn W4-L10) — không bao giờ chạm mạng: YoutubeDL / vận chuyển HTTP đều được tiêm giả.

Kết quả spike 23/09 (bảng đầy đủ + bằng chứng: `docs/migrations/video_crawler/PLATFORM_MATRIX.md`
mục "Tìm kênh theo TÊN"):
- YouTube: ẩn danh được — `https://www.youtube.com/results?search_query=<kw>&sp=EgIQAg%3D%3D` với
  `extract_flat` trả mục `ie_key='YoutubeTab'`, có `channel_follower_count` + `thumbnails`.
- Bilibili: ẩn danh được — `api.bilibili.com/x/web-interface/search/type?search_type=bili_user`
  (KHÔNG cần ký WBI; nhưng thiếu cookie buvid ẩn danh ⇒ HTTP 412 ⇒ phải GET `bilibili.com` trước).
- Douyin: CẦN phiên — `/aweme/v1/web/discover/search/` `search_channel=aweme_user_web`
  (`Evil0ctal/Douyin_TikTok_Download_API` Apache-2.0 @9fa3e54 `endpoints.py:USER_SEARCH`);
  ẩn danh trả HTTP 200 THÂN RỖNG (tín hiệu chống bot) ⇒ test bằng phản hồi giả.
- Xiaohongshu: CẦN phiên — POST `/api/sns/web/v1/search/usersearch` thân `{"search_user_request": {...}}`
  (`ReaJason/xhs` MIT @f4b62d9 `xhs/core.py:get_user_by_keyword`) ⇒ test bằng phản hồi giả.
- TikTok / Weibo / Facebook / Instagram / Twitter / Kuaishou: chưa có đường ⇒ lỗi `chua_ho_tro_tim_kenh`.
"""
from __future__ import annotations

import json
import math

import pytest

from apps.video_crawler.adapters import douyin_web as dw
from apps.video_crawler.adapters import xhs_web
from apps.video_crawler.adapters.base import (
    ID_KENH_AN_TOAN,
    MA_CHUA_HO_TRO_TIM_KENH,
    KenhItem,
    LoiCao,
    YeuCauTimKenh,
    tao_kenh,
)
from apps.video_crawler.adapters.bilibili import BilibiliAdapter
from apps.video_crawler.adapters.douyin import DouyinAdapter
from apps.video_crawler.adapters.tiktok import TikTokAdapter
from apps.video_crawler.adapters.xiaohongshu import XiaohongshuAdapter
from apps.video_crawler.adapters.youtube import YoutubeAdapter

KENH_YT = "UCSJ4gkVC6NrvII8umztf0Ow"          # smoke thật 23/09: "Lofi Girl", 15 800 000 người theo dõi
SEC = "MS4wLjABAAAArDVBosPJF3eIWVEFp0szuJ-e1V_-rK0ieJeWwpE77E8"
USER_XHS = "5ff0e6410000000001008400"


def _bao():
    ghi: list = []
    return ghi, (lambda pct, msg: ghi.append((pct, msg)))


def _yc(nen, tu_khoa="lofi", n=5) -> YeuCauTimKenh:
    return YeuCauTimKenh(nen_tang=nen, tu_khoa=tu_khoa, so_luong=n)


# ================================================================ base: làm sạch
def test_tao_kenh_giu_du_lieu_sach():
    k = tao_kenh("youtube", KENH_YT, f"https://www.youtube.com/channel/{KENH_YT}", ten="  Lofi   Girl ",
                 anh_dai_dien="https://yt3.ggpht.com/a.jpg", so_theo_doi=15800000, so_video=1200,
                 mo_ta="Lofi  House\nis now available!")
    assert k == KenhItem(nen_tang="youtube", id=KENH_YT, ten="Lofi Girl",
                         url=f"https://www.youtube.com/channel/{KENH_YT}",
                         anh_dai_dien="https://yt3.ggpht.com/a.jpg", so_theo_doi=15800000, so_video=1200,
                         mo_ta="Lofi House is now available!")
    assert KenhItem.from_dict(k.to_dict()) == k


@pytest.mark.parametrize("id_xau", ["", "..", "a/b", "a:b", "x" * 201, None, 123, "a b"])
def test_tao_kenh_tu_choi_id_khong_an_toan(id_xau):
    assert tao_kenh("youtube", id_xau, "https://www.youtube.com/channel/x") is None


@pytest.mark.parametrize("url_xau", ["", "javascript:alert(1)", "/channel/x", "ftp://a/b", None])
def test_tao_kenh_tu_choi_url_khong_phai_http(url_xau):
    assert tao_kenh("youtube", KENH_YT, url_xau) is None


def test_tao_kenh_du_lieu_la_khong_lam_vo():
    """Thiếu trường / sai kiểu / số vô lý ⇒ rơi về mặc định, KHÔNG ném."""
    k = tao_kenh("bilibili", "1685650605", "https://space.bilibili.com/1685650605",
                 ten=None, anh_dai_dien={"url": "x"}, so_theo_doi="nhiều", so_video=-3, mo_ta=["a"])
    assert k is not None
    assert (k.ten, k.anh_dai_dien, k.so_theo_doi, k.so_video, k.mo_ta) == ("1685650605", "", None, None, "")
    assert tao_kenh("bilibili", "1", "https://space.bilibili.com/1", so_theo_doi=math.nan).so_theo_doi is None
    assert tao_kenh("bilibili", "1", "https://space.bilibili.com/1", so_theo_doi=10 ** 13).so_theo_doi is None
    assert tao_kenh("bilibili", "1", "https://space.bilibili.com/1", so_theo_doi=True).so_theo_doi is None


def test_tao_kenh_anh_khong_giao_thuc_thanh_https_va_khong_tai():
    """Bilibili `upic` là `//i2.hdslb.com/...`. Ảnh chỉ là URL — proxy `anh_bia` mới tải (không tải ở đây)."""
    k = tao_kenh("bilibili", "1", "https://space.bilibili.com/1", anh_dai_dien="//i2.hdslb.com/bfs/face/a.jpg")
    assert k.anh_dai_dien == "https://i2.hdslb.com/bfs/face/a.jpg"


def test_tao_kenh_cat_chuoi_dai():
    k = tao_kenh("youtube", KENH_YT, f"https://www.youtube.com/channel/{KENH_YT}",
                 ten="T" * 500, mo_ta="M" * 500)
    assert len(k.ten) == 120 and len(k.mo_ta) == 200


def test_id_kenh_an_toan_cung_bo_ky_tu_voi_id_video():
    """Chỉ nới ĐỘ DÀI (sec_user_id Douyin ~55-200), không nới bộ ký tự ⇒ vẫn an toàn làm khoá/đường dẫn."""
    assert ID_KENH_AN_TOAN == r"[A-Za-z0-9_-]{1,200}"
    assert tao_kenh("douyin", SEC, f"https://www.douyin.com/user/{SEC}") is not None


# ================================================================ nền chưa hỗ trợ
@pytest.mark.parametrize("ten_mod,ten_lop", [
    ("tiktok", "TikTokAdapter"), ("weibo", "WeiboAdapter"), ("facebook", "FacebookAdapter"),
    ("instagram", "InstagramAdapter"), ("twitter", "TwitterAdapter"), ("kuaishou", "KuaishouAdapter"),
    ("bilibili_tv", "BilibiliTvAdapter"),
])
def test_nen_chua_ho_tro_nem_ma_rieng(ten_mod, ten_lop):
    import importlib

    mod = importlib.import_module(f"apps.video_crawler.adapters.{ten_mod}")
    adapter = getattr(mod, ten_lop)()
    _ghi, bao = _bao()
    with pytest.raises(LoiCao) as e:
        adapter.tim_kenh(_yc(adapter.nen_tang), bao_tien_do=bao)
    assert e.value.ma == MA_CHUA_HO_TRO_TIM_KENH and e.value.tam_thoi is False


def test_moi_adapter_da_dang_ky_deu_co_tim_kenh():
    """Tầng trên gọi `adapter.tim_kenh` trên MỌI nền ⇒ không nền nào được thiếu (AttributeError)."""
    from apps.video_crawler import nen_tang
    from apps.video_crawler.adapters import tao

    for nen in nen_tang.cac_nen_bat():
        assert callable(getattr(tao(nen.id), "tim_kenh", None)), nen.id


# ================================================================ YouTube (ẩn danh)
class FakeYDL:
    def __init__(self, opts, info=None, loi=None):
        self.params, self.info, self.loi = opts, info, loi
        self.urls: list = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=True):
        self.urls.append(url)
        if self.loi:
            raise self.loi
        return self.info


class NhaYDL:
    def __init__(self, info=None, loi=None):
        self.info, self.loi = info, loi
        self.tao: list[FakeYDL] = []

    def __call__(self, opts):
        y = FakeYDL(opts, self.info, self.loi)
        self.tao.append(y)
        return y


def _kenh_yt(cid=KENH_YT, title="Lofi Girl", followers=15800000, **kw):
    d = {"_type": "url", "ie_key": "YoutubeTab", "id": cid, "title": title,
         "channel_follower_count": followers, "description": "Lofi House is now available!",
         "thumbnails": [{"url": "https://yt3.ggpht.com/small.jpg"}, {"url": "https://yt3.ggpht.com/big.jpg"}]}
    d.update(kw)
    return d


def test_youtube_tim_kenh_tra_the_kenh():
    nha = NhaYDL(info={"entries": [_kenh_yt(), _kenh_yt("UC" + "b" * 22, "Lofi Records", 120000)]})
    ghi, bao = _bao()
    ra = YoutubeAdapter(nha).tim_kenh(_yc("youtube"), bao_tien_do=bao)
    assert [k.id for k in ra] == [KENH_YT, "UC" + "b" * 22]
    assert ra[0].ten == "Lofi Girl" and ra[0].so_theo_doi == 15800000
    assert ra[0].url == f"https://www.youtube.com/channel/{KENH_YT}"
    assert ra[0].anh_dai_dien == "https://yt3.ggpht.com/big.jpg"      # ảnh lớn nhất = phần tử cuối
    assert ra[0].mo_ta == "Lofi House is now available!"
    assert ghi[0][0] == 0 and ghi[-1][0] == 100


def test_youtube_tim_kenh_dung_url_tim_kenh_va_extract_flat():
    nha = NhaYDL(info={"entries": []})
    YoutubeAdapter(nha).tim_kenh(_yc("youtube", "lofi girl", 7), bao_tien_do=_bao()[1])
    y = nha.tao[0]
    assert y.urls == ["https://www.youtube.com/results?search_query=lofi%20girl&sp=EgIQAg%3D%3D"]
    assert y.params["extract_flat"] == "in_playlist" and y.params["playlistend"] == 7
    assert y.params["skip_download"] is True
    assert "youtube:search_url" in y.params["allowed_extractors"]
    assert "generic" not in y.params["allowed_extractors"]            # spec §21


def test_youtube_tim_kenh_danh_sach_rong_khong_phai_loi():
    ra = YoutubeAdapter(NhaYDL(info={"entries": []})).tim_kenh(_yc("youtube"), bao_tien_do=_bao()[1])
    assert ra == []
    ra2 = YoutubeAdapter(NhaYDL(info=None)).tim_kenh(_yc("youtube"), bao_tien_do=_bao()[1])
    assert ra2 == []


def test_youtube_tim_kenh_bo_muc_khong_phai_kenh_va_du_lieu_la():
    """Video lẫn trong kết quả (`ie_key='Youtube'`), mục thiếu id, id sai mẫu, mục không phải dict."""
    info = {"entries": [
        _kenh_yt(ie_key="Youtube"),                          # video, không phải kênh
        {"ie_key": "YoutubeTab", "title": "khong co id"},
        _kenh_yt("../../etc"),                               # id không an toàn
        "chuoi la",
        None,
        _kenh_yt("UC" + "c" * 22, title=None, followers=None, thumbnails=None, description=None),
    ]}
    ra = YoutubeAdapter(NhaYDL(info=info)).tim_kenh(_yc("youtube"), bao_tien_do=_bao()[1])
    assert [k.id for k in ra] == ["UC" + "c" * 22]
    assert (ra[0].ten, ra[0].anh_dai_dien, ra[0].so_theo_doi, ra[0].mo_ta) == ("UC" + "c" * 22, "", None, "")


def test_youtube_tim_kenh_ton_trong_so_luong():
    info = {"entries": [_kenh_yt("UC" + chr(97 + i) * 22) for i in range(6)]}
    ra = YoutubeAdapter(NhaYDL(info=info)).tim_kenh(_yc("youtube", n=2), bao_tien_do=_bao()[1])
    assert len(ra) == 2


def test_youtube_tim_kenh_loi_ytdlp_thanh_loicao():
    from yt_dlp.utils import DownloadError

    nha = NhaYDL(loi=DownloadError("ERROR: HTTP Error 429: Too Many Requests"))
    with pytest.raises(LoiCao):
        YoutubeAdapter(nha).tim_kenh(_yc("youtube"), bao_tien_do=_bao()[1])


# ================================================================ Bilibili (ẩn danh, cần buvid)
class Resp:
    def __init__(self, du_lieu, status=200):
        self.status = status
        self._b = du_lieu if isinstance(du_lieu, bytes) else json.dumps(du_lieu).encode()

    def read(self):
        return self._b


class NhaBili:
    def __init__(self, *tra_loi):
        self.tra_loi = list(tra_loi)
        self.req: list = []
        self.tao: list = []

    def __call__(self, opts):
        self.tao.append(opts)
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def urlopen(self, req):
        self.req.append(req)
        r = self.tra_loi.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r

    def extract_info(self, url, download=True):
        raise AssertionError("tim_kenh khong di qua extractor yt-dlp")


def _bili_user(mid=1685650605, uname="LofiGirl", fans=178195, videos=151, **kw):
    d = {"type": "bili_user", "mid": mid, "uname": uname, "fans": fans, "videos": videos,
         "usign": "Lofi moi ngay", "upic": "//i2.hdslb.com/bfs/face/abc.jpg"}
    d.update(kw)
    return d


def _bili_ok(*users):
    return Resp({"code": 0, "message": "OK", "data": {"page": 1, "result": list(users)}})


def test_bilibili_tim_kenh_tra_the_kenh():
    nha = NhaBili(Resp(b"<html>trang chu</html>"), _bili_ok(_bili_user(), _bili_user(270913865, "Lofi-China", 11119, 122)))
    ghi, bao = _bao()
    ra = BilibiliAdapter(nha).tim_kenh(_yc("bilibili"), bao_tien_do=bao)
    assert [k.id for k in ra] == ["1685650605", "270913865"]
    assert ra[0].ten == "LofiGirl" and ra[0].so_theo_doi == 178195 and ra[0].so_video == 151
    assert ra[0].url == "https://space.bilibili.com/1685650605"
    assert ra[0].anh_dai_dien == "https://i2.hdslb.com/bfs/face/abc.jpg"
    assert ra[0].mo_ta == "Lofi moi ngay"
    assert ghi[-1][0] == 100


def test_bilibili_tim_kenh_ham_nong_buvid_truoc_roi_moi_goi_api():
    """Thiếu cookie buvid ẩn danh ⇒ API trả HTTP 412 (smoke thật 23/09) ⇒ phải GET trang chủ trước."""
    nha = NhaBili(Resp(b"<html/>"), _bili_ok(_bili_user()))
    BilibiliAdapter(nha).tim_kenh(_yc("bilibili", "lofi"), bao_tien_do=_bao()[1])
    assert nha.req[0].url == "https://www.bilibili.com/"
    assert nha.req[1].url.startswith("https://api.bilibili.com/x/web-interface/search/type?")
    assert "search_type=bili_user" in nha.req[1].url and "keyword=lofi" in nha.req[1].url
    assert nha.req[1].headers.get("Referer") == "https://www.bilibili.com/"


def test_bilibili_tim_kenh_412_thanh_nen_chan():
    from yt_dlp.networking.exceptions import HTTPError

    loi = HTTPError.__new__(HTTPError)
    loi.status = 412
    Exception.__init__(loi, "HTTP Error 412")
    nha = NhaBili(Resp(b"<html/>"), loi)
    with pytest.raises(LoiCao) as e:
        BilibiliAdapter(nha).tim_kenh(_yc("bilibili"), bao_tien_do=_bao()[1])
    assert e.value.ma == "nen_chan"


def test_bilibili_tim_kenh_code_khac_khong_thanh_loi():
    nha = NhaBili(Resp(b"<html/>"), Resp({"code": -412, "message": "risk control"}))
    with pytest.raises(LoiCao) as e:
        BilibiliAdapter(nha).tim_kenh(_yc("bilibili"), bao_tien_do=_bao()[1])
    assert e.value.ma == "nen_chan"


def test_bilibili_tim_kenh_khong_ai_khop_la_danh_sach_rong():
    nha = NhaBili(Resp(b"<html/>"), Resp({"code": 0, "data": {"page": 1}}))       # `result` VẮNG khi 0 kết quả
    assert BilibiliAdapter(nha).tim_kenh(_yc("bilibili"), bao_tien_do=_bao()[1]) == []


def test_bilibili_tim_kenh_du_lieu_la_khong_lam_vo():
    nha = NhaBili(Resp(b"<html/>"), _bili_ok(
        {"type": "video", "mid": 1, "uname": "video lot vao"},     # không phải bili_user
        {"type": "bili_user"},                                     # thiếu mid
        {"type": "bili_user", "mid": "../x", "uname": "id xau"},
        "chuoi la",
        _bili_user(432074585, "lofi", fans=None, videos="nhieu", upic=None, usign=None),
    ))
    ra = BilibiliAdapter(nha).tim_kenh(_yc("bilibili"), bao_tien_do=_bao()[1])
    assert [k.id for k in ra] == ["432074585"]
    assert (ra[0].so_theo_doi, ra[0].so_video, ra[0].anh_dai_dien, ra[0].mo_ta) == (None, None, "", "")


def test_bilibili_tim_kenh_than_khong_phai_json():
    nha = NhaBili(Resp(b"<html/>"), Resp(b"<html>captcha</html>"))
    with pytest.raises(LoiCao) as e:
        BilibiliAdapter(nha).tim_kenh(_yc("bilibili"), bao_tien_do=_bao()[1])
    assert e.value.ma == "nen_chan"


# ================================================================ Douyin (cần phiên)
class VanChuyen:
    def __init__(self, *phan_hoi):
        self.phan_hoi = list(phan_hoi)
        self.goi: list[tuple[str, dict]] = []

    def __call__(self, url, headers):
        self.goi.append((url, dict(headers)))
        p = self.phan_hoi.pop(0)
        if isinstance(p, BaseException):
            raise p
        return p


def _dy_user(sec=SEC, nickname="Lofi", followers=12345, awemes=88, **kw):
    d = {"user_info": {"sec_uid": sec, "uid": "111", "nickname": nickname, "signature": "nhac lofi",
                       "follower_count": followers, "aweme_count": awemes,
                       "avatar_thumb": {"url_list": ["https://p3.douyinpic.com/a.jpeg"]}}}
    d["user_info"].update(kw)
    return d


def _dy_json(d) -> tuple[int, bytes]:
    return 200, json.dumps(d).encode()


def _dy_adapter(van_chuyen, cookie="C:/tmp/cookies.txt"):
    a = DouyinAdapter(van_chuyen_factory=lambda tep: van_chuyen, ky=lambda q, ua: "abogus_gia")
    a.tep_cookie = cookie
    return a


def test_douyin_tim_kenh_tra_the_kenh():
    vc = VanChuyen(_dy_json({"status_code": 0, "user_list": [_dy_user(), _dy_user("MS4wLjABAAAA" + "b" * 30, "Lofi2")]}))
    ra = _dy_adapter(vc).tim_kenh(_yc("douyin"), bao_tien_do=_bao()[1])
    assert [k.id for k in ra] == [SEC, "MS4wLjABAAAA" + "b" * 30]
    assert ra[0].ten == "Lofi" and ra[0].so_theo_doi == 12345 and ra[0].so_video == 88
    assert ra[0].url == f"https://www.douyin.com/user/{SEC}"
    assert ra[0].anh_dai_dien == "https://p3.douyinpic.com/a.jpeg" and ra[0].mo_ta == "nhac lofi"


def test_douyin_tim_kenh_goi_dung_diem_cuoi_va_kenh_tim_nguoi_dung():
    vc = VanChuyen(_dy_json({"status_code": 0, "user_list": []}))
    _dy_adapter(vc).tim_kenh(_yc("douyin", "lofi"), bao_tien_do=_bao()[1])
    url = vc.goi[0][0]
    assert url.startswith("https://www.douyin.com/aweme/v1/web/discover/search/?")
    assert "search_channel=aweme_user_web" in url and "keyword=lofi" in url and "a_bogus=abogus_gia" in url


def test_douyin_tim_kenh_khong_co_phien_thi_doi_dang_nhap():
    """Ẩn danh: HTTP 200 THÂN RỖNG (spike 23/09) — chặn ngay, không đốt một lượt gọi mạng."""
    vc = VanChuyen()
    with pytest.raises(LoiCao) as e:
        _dy_adapter(vc, cookie=None).tim_kenh(_yc("douyin"), bao_tien_do=_bao()[1])
    assert e.value.ma == "can_dang_nhap" and vc.goi == []


def test_douyin_tim_kenh_ma_2483_thanh_can_dang_nhap():
    vc = VanChuyen(_dy_json({"status_code": 2483}))
    with pytest.raises(LoiCao) as e:
        _dy_adapter(vc).tim_kenh(_yc("douyin"), bao_tien_do=_bao()[1])
    assert e.value.ma == "can_dang_nhap"


def test_douyin_tim_kenh_than_rong_hai_lan_thanh_nen_chan():
    vc = VanChuyen((200, b""), (200, b"   "))
    with pytest.raises(LoiCao) as e:
        _dy_adapter(vc).tim_kenh(_yc("douyin"), bao_tien_do=_bao()[1])
    assert e.value.ma == "nen_chan"


def test_douyin_tim_kenh_danh_sach_rong_va_du_lieu_la():
    vc = VanChuyen(_dy_json({"status_code": 0, "user_list": []}))
    assert _dy_adapter(vc).tim_kenh(_yc("douyin"), bao_tien_do=_bao()[1]) == []
    vc2 = VanChuyen(_dy_json({"status_code": 0, "user_list": [
        {}, {"user_info": None}, {"user_info": {"sec_uid": "a/b"}}, "la",
        {"user_info": {"sec_uid": SEC}},
    ]}))
    ra = _dy_adapter(vc2).tim_kenh(_yc("douyin"), bao_tien_do=_bao()[1])
    assert [k.id for k in ra] == [SEC] and ra[0].ten == SEC and ra[0].so_theo_doi is None


def test_douyin_muc_tu_user_bo_rac():
    assert dw.kenh_tu_user(None) is None
    assert dw.kenh_tu_user({"user_info": {"nickname": "khong co sec_uid"}}) is None


# ================================================================ Xiaohongshu (cần phiên)
class FakeYDLXhs:
    def __init__(self, opts, tra_loi, cookie):
        self.params, self.tra_loi, self.cookiejar = opts, list(tra_loi), list(cookie)
        self.req: list = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def urlopen(self, req):
        self.req.append(req)
        r = self.tra_loi.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r


class NhaXhs:
    def __init__(self, tra_loi, cookie):
        self.tra_loi, self.cookie = tra_loi, cookie
        self.tao: list[FakeYDLXhs] = []

    def __call__(self, opts):
        y = FakeYDLXhs(opts, self.tra_loi, self.cookie)
        self.tao.append(y)
        return y


class KyGia:
    def __init__(self):
        self.goi: list = []

    def ky(self, method, url, cookies, *, params=None, payload=None):
        self.goi.append((method, url, dict(cookies), params, payload))
        return {"x-s": "XYS_gia", "x-t": "1", "x-s-common": "gia"}

    def url_get(self, url, params):
        return url

    def search_id(self):
        return "search-id-gia"


def _cookie_xhs():
    from http.cookiejar import Cookie

    def c(ten, gia):
        return Cookie(0, ten, gia, None, False, ".xiaohongshu.com", True, True, "/", True, False,
                      None, False, None, None, {})
    return [c("a1", "gia-a1"), c("web_session", "gia-ws")]


def _xhs_user(uid=USER_XHS, name="Lofi", fans="1.2万", **kw):
    d = {"id": uid, "name": name, "image": "https://sns-avatar-qc.xhscdn.com/a.jpg",
         "fans": fans, "sub_title": "nhac lofi moi ngay", "note_count": 42}
    d.update(kw)
    return d


def _xhs_adapter(tra_loi, cookie=None, tep="C:/tmp/cookies.txt"):
    nha = NhaXhs(tra_loi, _cookie_xhs() if cookie is None else cookie)
    a = XiaohongshuAdapter(nha, ky=KyGia())
    a.tep_cookie = tep
    return a, nha


def test_xhs_tim_kenh_tra_the_kenh():
    a, nha = _xhs_adapter([Resp({"success": True, "data": {"users": [_xhs_user()], "has_more": False}})])
    ra = a.tim_kenh(_yc("xiaohongshu"), bao_tien_do=_bao()[1])
    assert [k.id for k in ra] == [USER_XHS]
    assert ra[0].ten == "Lofi" and ra[0].url == f"https://www.xiaohongshu.com/user/profile/{USER_XHS}"
    assert ra[0].anh_dai_dien == "https://sns-avatar-qc.xhscdn.com/a.jpg"
    assert ra[0].mo_ta == "nhac lofi moi ngay" and ra[0].so_video == 42
    assert ra[0].so_theo_doi is None          # "1.2万" không phải số ⇒ bỏ, không đoán


def test_xhs_tim_kenh_goi_dung_diem_cuoi_va_than():
    a, nha = _xhs_adapter([Resp({"success": True, "data": {"users": []}})])
    a.tim_kenh(_yc("xiaohongshu", "lofi", 7), bao_tien_do=_bao()[1])
    req = nha.tao[0].req[0]
    assert req.url == xhs_web.API + xhs_web.URI_TIM_KENH == xhs_web.API + "/api/sns/web/v1/search/usersearch"
    assert req.method == "POST"
    than = json.loads(req.data.decode())
    assert than["search_user_request"]["keyword"] == "lofi"
    assert than["search_user_request"]["biz_type"] == "web_search_user"
    assert than["search_user_request"]["page"] == 1


def test_xhs_tim_kenh_khong_co_phien_thi_doi_dang_nhap():
    a, _ = _xhs_adapter([], cookie=[], tep=None)
    with pytest.raises(LoiCao) as e:
        a.tim_kenh(_yc("xiaohongshu"), bao_tien_do=_bao()[1])
    assert e.value.ma == "can_dang_nhap"


def test_xhs_tim_kenh_het_phien_thanh_can_dang_nhap():
    a, _ = _xhs_adapter([Resp({"success": False, "code": -100, "msg": "登录已过期"})])
    with pytest.raises(LoiCao) as e:
        a.tim_kenh(_yc("xiaohongshu"), bao_tien_do=_bao()[1])
    assert e.value.ma == "can_dang_nhap"


def test_xhs_tim_kenh_danh_sach_rong_va_du_lieu_la():
    a, _ = _xhs_adapter([Resp({"success": True, "data": {"users": []}})])
    assert a.tim_kenh(_yc("xiaohongshu"), bao_tien_do=_bao()[1]) == []
    b, _ = _xhs_adapter([Resp({"success": True, "data": {"users": [
        {}, {"id": "khong-phai-hex-24"}, "la", None, _xhs_user(name=None, image=None, sub_title=None,
                                                               note_count=None),
    ]}})])
    ra = b.tim_kenh(_yc("xiaohongshu"), bao_tien_do=_bao()[1])
    assert [k.id for k in ra] == [USER_XHS]
    assert (ra[0].ten, ra[0].anh_dai_dien, ra[0].mo_ta, ra[0].so_video) == (USER_XHS, "", "", None)


def test_tim_kenh_khong_bao_gio_tai_anh(monkeypatch):
    """Ảnh đại diện chỉ là URL — adapter KHÔNG được mở kết nối tới CDN ảnh trong lúc tìm."""
    import urllib.request

    def cam(*a, **k):
        raise AssertionError("tim_kenh khong duoc tai anh")

    monkeypatch.setattr(urllib.request, "urlopen", cam)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", cam)
    ra = YoutubeAdapter(NhaYDL(info={"entries": [_kenh_yt()]})).tim_kenh(_yc("youtube"), bao_tien_do=_bao()[1])
    assert ra[0].anh_dai_dien.startswith("https://")


def test_anh_dai_dien_moi_nen_da_lam_deu_nam_trong_allowlist_anh_bia():
    """Miền ảnh đại diện thật (smoke 23/09 + tài liệu nguồn) phải đã có trong `anh_bia.CDN_ANH`."""
    from apps.video_crawler.anh_bia import CDN_ANH

    that = {"youtube": "yt3.ggpht.com", "bilibili": "i2.hdslb.com", "douyin": "p3-pc.douyinpic.com",
            "xiaohongshu": "sns-avatar-qc.xhscdn.com"}
    for nen, host in that.items():
        assert any(host == h or host.endswith("." + h) for h in CDN_ANH[nen]), (nen, host)


def test_tiktok_tim_kenh_van_chua_ho_tro():
    """Đường `api/search/user/full` ẩn danh trả 200 thân rỗng và cần ký X-Bogus/msToken (spike 23/09);
    yt-dlp không có extractor tìm người dùng ⇒ chưa làm, không đoán."""
    with pytest.raises(LoiCao) as e:
        TikTokAdapter().tim_kenh(_yc("tiktok"), bao_tien_do=_bao()[1])
    assert e.value.ma == MA_CHUA_HO_TRO_TIM_KENH


# ── Nền nào tìm kênh được: SUY TỪ ADAPTER, không khai tay ────────────────────

def test_co_tim_kenh_KHONG_bat_nham_cho_adapter_ho_yt_dlp_chua_khai():
    """Rà soát gộp W4-L11: mọi adapter họ yt-dlp đều KẾ THỪA `YtdlpAdapter.tim_kenh`, nên phép so "có ghi đè
    `tim_kenh` không" trả True cho cả nền chưa khai `ie_key_kenh` — bản chung ấy chỉ ném "chưa hỗ trợ".
    Giao diện vì thế mời khách gõ tên kênh rồi mới báo lỗi. Một nguồn duy nhất: `nen_tang.co_tim_kenh`."""
    from apps.video_crawler import nen_tang
    assert nen_tang.co_tim_kenh("youtube") is True
    assert nen_tang.co_tim_kenh("bilibili") is True
    for nen_id in ("facebook", "instagram", "twitter", "weibo", "bilibili_tv", "tiktok"):
        assert nen_tang.co_tim_kenh(nen_id) is False, nen_id


def test_co_tim_kenh_suy_tu_adapter_khong_phai_co_khai_tay():
    """Một cờ khai tay trong registry là nguồn chân lý thứ hai: thêm `tim_kenh` cho một nền mà quên bật cờ thì
    giao diện giấu mất tính năng vừa làm. Hỏi thẳng lớp adapter — kể cả điều kiện `ie_key_kenh` của họ yt-dlp."""
    from apps.video_crawler import nen_tang
    from apps.video_crawler.adapters import base, tao
    from apps.video_crawler.adapters._ytdlp import YtdlpAdapter
    for nen in nen_tang.cac_nen_bat():
        lop = type(tao(nen.id))
        if lop.tim_kenh is base.PlatformAdapter.tim_kenh:
            mong = False
        elif lop.tim_kenh is YtdlpAdapter.tim_kenh:
            mong = bool(getattr(lop, "ie_key_kenh", ()))
        else:
            mong = True
        assert nen_tang.co_tim_kenh(nen.id) is mong, nen.id
    assert nen_tang.co_tim_kenh("nen-khong-co-that") is False
