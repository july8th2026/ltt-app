"""Douyin `tu_khoa` (tìm video) + `kenh` (video của một người dùng) qua client web — không bao giờ chạm mạng:
vận chuyển HTTP và hàm ký được tiêm giả; ký a_bogus thật chỉ chạy thuần CPU.

Cấu trúc JSON mẫu dựng tay theo tài liệu nguồn (giấy phép dùng được, KHÔNG MediaCrawler):
- Endpoint + tham số tìm kiếm: `jiji262/douyin-downloader` (MIT) `core/api_client.py` @9874f41 `search_aweme`
  (`/aweme/v1/web/general/search/single/`, `search_channel=aweme_video_web`, `offset`/`count`); phản hồi
  `data[].aweme_info`, `has_more`, `cursor`; `status_code == 2483` = cần đăng nhập (`_LOGIN_REQUIRED_STATUS_CODES`);
  200 thân rỗng = tín hiệu chống bot phổ biến (thử lại với chữ ký mới).
- Endpoint + tham số kênh: `Evil0ctal/Douyin_TikTok_Download_API` (Apache-2.0) @9fa3e54
  `src/dtk/platforms/douyin/params.py:author_posts_params` + `base_params`; `Johnserf-Seed/f2` (Apache-2.0)
  @7dab3e2 `f2/apps/douyin/filter.py:UserPostFilter`: `aweme_list[*].aweme_id/desc/author.nickname/
  video.duration`, `has_more`, `max_cursor`, `images` (bài ảnh).
- `video.duration` tính bằng ms, ảnh bìa `video.cover.url_list`: yt-dlp 2026.03.17
  `extractor/tiktok.py:_parse_aweme_video_app` (`int_or_none(scale=1000)`, `cover`/`origin_cover`).
- a_bogus: port `f2/utils/abogus.py` (blob 419cf56) vào `apps/video_crawler/vendor/f2_abogus/`; giá trị vàng
  dưới đây tính bằng CHÍNH tệp upstream (gmssl thay bằng shim hashlib) với random/clock cố định.
"""
from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from apps.video_crawler.adapters import douyin_web as dw
from apps.video_crawler.adapters.base import CrawlItem, LoiCao, YeuCauCao
from apps.video_crawler.adapters.douyin import DouyinAdapter

SEC = "MS4wLjABAAAArDVBosPJF3eIWVEFp0szuJ-e1V_-rK0ieJeWwpE77E8"   # sec_user_id mẫu trong f2 abogus.py __main__
ID1, ID2, ID3 = "7380308675841297704", "7467485482314763572", "6961737553342991651"


def _aweme(aid, desc="T", nick="U", dur_ms=15300, cover="https://p3.douyinpic.com/c.jpeg", **kw):
    d = {"aweme_id": aid, "desc": desc, "author": {"nickname": nick, "sec_uid": SEC},
         "video": {"duration": dur_ms, "cover": {"url_list": [cover]}}, "aweme_type": 0}
    d.update(kw)
    return d


def _json(d) -> tuple[int, bytes]:
    return 200, json.dumps(d).encode()


class VanChuyen:
    """Vận chuyển giả: trả lần lượt các phản hồi xếp sẵn, ghi lại (url, headers)."""

    def __init__(self, *phan_hoi):
        self.phan_hoi = list(phan_hoi)
        self.goi: list[tuple[str, dict]] = []

    def __call__(self, url, headers):
        self.goi.append((url, dict(headers)))
        p = self.phan_hoi.pop(0)
        if isinstance(p, BaseException):
            raise p
        return p


class Nha:
    """van_chuyen_factory giả: ghi lại tep_cookie được truyền."""

    def __init__(self, vc):
        self.vc = vc
        self.cookie: list = []

    def __call__(self, tep_cookie):
        self.cookie.append(tep_cookie)
        return self.vc


def _ky(q, ua):
    return "KY"


def _khong_bao(pct, msg):
    pass


def _yc(che_do, dau_vao, n=5):
    return YeuCauCao(nen_tang="douyin", che_do=che_do, dau_vao=dau_vao, so_luong=n)


def _ad(vc, tep_cookie="C:/tam/cookies.txt"):
    nha = Nha(vc)
    a = DouyinAdapter(van_chuyen_factory=nha, ky=_ky)
    a.tep_cookie = tep_cookie
    return a, nha


def _q(url):
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query, keep_blank_values=True).items()}


# ---------------------------------------------------------------- a_bogus (vendor port)
def test_sm3_hashlib_dung_vector_chuan():
    """GB/T 32905-2016 phụ lục A.1: SM3("abc")."""
    from apps.video_crawler.vendor.f2_abogus.abogus import CryptoUtility

    assert bytes(CryptoUtility.sm3_to_array("abc")).hex() == (
        "66c7f0f462eeedd9d1f2d46bdc10e4e24167c4875cf2f7a2297da02b8f4ba8e0")


def test_a_bogus_khop_gia_tri_vang_cua_f2_upstream():
    from apps.video_crawler.vendor.f2_abogus.abogus import ABogus

    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/130.0.0.0 Safari/537.36")
    fp = "1536|747|1536|834|0|30|0|0|1536|864|1536|864|1536|747|24|24|Win32"
    it = iter([0.1234, 0.5678, 0.9012])
    ra = ABogus(fp=fp, user_agent=ua, rand=lambda: next(it), now_ms=lambda: 1758500000000).generate_abogus(
        "device_platform=webapp&aid=6383&keyword=%E7%8C%AB")
    assert ra[1] == ("E7mhBdu2krjihxWT5AOLfY3q6ll3YmIH0SVkMD2fDnfw4y39HMYD9exoC4tvPb8ji4/sIeYjy4hbT3ohrQ2y8qwf9W0L/"
                     "25gsDSkKl12so0j53inCLf/E0iw5hsAtFH8svr4iKi8owVtSYyhldAJ5kIlO62-zo0/96R=")
    assert ra[0].endswith("&a_bogus=" + ra[1])


def test_ky_a_bogus_mac_dinh_tra_chuoi_bang_chu_cai_rieng():
    s = dw.ky_a_bogus("a=1", dw.UA)
    assert s and set(s) <= set("Dkdpgh2ZmsQB80/MfvV36XI1R45-WUAlEixNLwoqYTOPuzKFjJnry79HbGcaStCe=")


def test_vendor_co_license_notice_va_sha_nguon():
    from pathlib import Path

    goc = Path(dw.__file__).resolve().parent.parent / "vendor" / "f2_abogus"
    assert "Apache License" in (goc / "LICENSE").read_text(encoding="utf-8")
    notice = (goc / "NOTICE").read_text(encoding="utf-8")
    assert "7dab3e2ffffaa2535834d28fca99dbc2e89fa9d3" in notice and "Johnserf-Seed/f2" in notice


# ---------------------------------------------------------------- dựng URL
def test_dung_url_ky_tren_query_da_ma_hoa_va_them_mstoken():
    nhan = []

    def ky(q, ua):
        nhan.append((q, ua))
        return "SIG"

    url = dw.dung_url(dw.DUONG_TIM, {"keyword": "mèo con", "offset": "0"}, ms_token="MT", ky=ky)
    q_ky, ua = nhan[0]
    assert ua == dw.UA
    assert url == f"https://www.douyin.com/aweme/v1/web/general/search/single/?{q_ky}&a_bogus=SIG"
    assert "keyword=m%C3%A8o%20con" in q_ky and q_ky.endswith("&msToken=MT")


def test_dung_url_khong_mstoken_thi_khong_them():
    url = dw.dung_url(dw.DUONG_KENH, {"a": "1"}, ms_token="", ky=_ky)
    assert "msToken" not in url


def test_tham_so_goc_co_truong_bat_buoc():
    p = dw.tham_so_goc()
    for k, v in {"device_platform": "webapp", "aid": "6383", "channel": "channel_pc_web",
                 "browser_name": "Chrome", "browser_version": "130.0.0.0"}.items():
        assert p[k] == v
    assert "Chrome/130.0.0.0" in dw.UA          # UA phải khớp browser_version gửi đi (Evil0ctal params.py)


# ---------------------------------------------------------------- cookie Netscape
def test_doc_cookie_netscape(tmp_path):
    f = tmp_path / "cookies.txt"
    f.write_text("# Netscape HTTP Cookie File\n"
                 ".douyin.com\tTRUE\t/\tFALSE\t0\tttwid\tTW\n"
                 "#HttpOnly_.douyin.com\tTRUE\t/\tTRUE\t0\tmsToken\tMSX\n"
                 "dong hong\n", encoding="utf-8")
    assert dw.doc_cookie(str(f), "msToken") == "MSX"
    assert dw.doc_cookie(str(f), "ttwid") == "TW"
    assert dw.doc_cookie(str(f), "khong_co") == ""
    assert dw.doc_cookie(None, "msToken") == ""
    assert dw.doc_cookie(str(tmp_path / "vang.txt"), "msToken") == ""


# ---------------------------------------------------------------- sec_uid
@pytest.mark.parametrize("vao", [
    f"https://www.douyin.com/user/{SEC}",
    f"https://www.douyin.com/user/{SEC}?from_tab_name=main&vid={ID1}",
    f"douyin.com/user/{SEC}/",
    SEC,
])
def test_sec_uid_tu_link(vao):
    assert dw.sec_uid_tu_link(vao) == SEC


@pytest.mark.parametrize("vao", [
    "https://www.douyin.com/user/self", "https://v.douyin.com/abc123/", f"https://www.douyin.com/video/{ID1}",
    "https://evil.com/user/" + SEC, "ngan", "", "https://www.douyin.com/user/" + "A" * 300,
])
def test_sec_uid_tu_link_sai(vao):
    assert dw.sec_uid_tu_link(vao) is None


# ---------------------------------------------------------------- aweme -> mục
def test_muc_tu_aweme_doi_ms_sang_giay():
    m = dw.muc_tu_aweme(_aweme(ID1, desc="Mèo", nick="Tác giả", dur_ms=15600))
    assert m == {"id": ID1, "tieu_de": "Mèo", "tac_gia": "Tác giả", "thoi_luong_s": 16,
                 "anh_bia": "https://p3.douyinpic.com/c.jpeg"}


def test_muc_tu_aweme_bia_du_phong_origin_cover_va_thieu_truong():
    aw = {"aweme_id": ID1, "video": {"origin_cover": {"url_list": ["https://o.jpg"]}}}
    assert dw.muc_tu_aweme(aw) == {"id": ID1, "tieu_de": "", "tac_gia": "", "thoi_luong_s": None,
                                   "anh_bia": "https://o.jpg"}


@pytest.mark.parametrize("aw", [
    _aweme(ID1, images=[{"url_list": ["x"]}]),     # bài ảnh — yt-dlp không có video để tải
    {"desc": "không id"}, "chuoi", None,
])
def test_muc_tu_aweme_bo_bai_anh_va_rac(aw):
    assert dw.muc_tu_aweme(aw) is None


# ---------------------------------------------------------------- tu_khoa
def test_tim_tu_khoa_tra_muc_va_goi_dung_endpoint():
    vc = VanChuyen(_json({"status_code": 0, "has_more": 0, "cursor": 10, "data": [
        {"type": 1, "aweme_info": _aweme(ID1, desc="A", nick="N1", dur_ms=9000)},
        {"type": 4, "user_list": []},                       # thẻ không phải video
        {"type": 1, "aweme_info": _aweme(ID2, desc="B")},
    ]}))
    a, nha = _ad(vc)
    bao = []
    ra = a.kham_pha(_yc("tu_khoa", "mèo", 5), bao_tien_do=lambda p, m: bao.append(p))
    assert ra == [
        CrawlItem("douyin", ID1, f"https://www.douyin.com/video/{ID1}", "A", "N1", 9,
                  "https://p3.douyinpic.com/c.jpeg"),
        CrawlItem("douyin", ID2, f"https://www.douyin.com/video/{ID2}", "B", "U", 15,
                  "https://p3.douyinpic.com/c.jpeg"),
    ]
    assert nha.cookie == ["C:/tam/cookies.txt"]
    url, headers = vc.goi[0]
    assert url.startswith("https://www.douyin.com/aweme/v1/web/general/search/single/?")
    q = _q(url)
    assert q["keyword"] == "mèo" and q["search_channel"] == "aweme_video_web" and q["offset"] == "0"
    assert q["a_bogus"] == "KY"
    assert headers["User-Agent"] == dw.UA and headers["Referer"].startswith("https://www.douyin.com/")
    assert bao[0] == 0 and bao[-1] == 100


def test_tim_tu_khoa_phan_trang_theo_cursor_va_cat_n():
    vc = VanChuyen(
        _json({"status_code": 0, "has_more": 1, "cursor": 2, "data": [
            {"aweme_info": _aweme(ID1)}, {"aweme_info": _aweme(ID2)}]}),
        _json({"status_code": 0, "has_more": 1, "cursor": 4, "data": [
            {"aweme_info": _aweme(ID2)}, {"aweme_info": _aweme(ID3)}]}),     # ID2 trùng ⇒ bỏ
    )
    a, _ = _ad(vc)
    ra = a.kham_pha(_yc("tu_khoa", "x", 3), bao_tien_do=_khong_bao)
    assert [m.id for m in ra] == [ID1, ID2, ID3]
    assert _q(vc.goi[1][0])["offset"] == "2"
    assert len(vc.goi) == 2


def test_tim_dung_khi_het_trang_hoac_cursor_khong_tien():
    vc = VanChuyen(
        _json({"status_code": 0, "has_more": 1, "cursor": 0, "data": [{"aweme_info": _aweme(ID1)}]}),
    )
    a, _ = _ad(vc)
    ra = a.kham_pha(_yc("tu_khoa", "x", 5), bao_tien_do=_khong_bao)
    assert [m.id for m in ra] == [ID1] and len(vc.goi) == 1


def test_tim_bo_id_khong_hop_le_va_video_qua_dai():
    vc = VanChuyen(_json({"status_code": 0, "has_more": 0, "data": [
        {"aweme_info": _aweme("123")},
        {"aweme_info": _aweme(ID1, dur_ms=4 * 3600 * 1000)},
        {"aweme_info": _aweme(ID2)},
    ]}))
    a, _ = _ad(vc)
    assert [m.id for m in a.kham_pha(_yc("tu_khoa", "x", 5), bao_tien_do=_khong_bao)] == [ID2]


def test_tim_khong_ket_qua_tra_rong():
    vc = VanChuyen(_json({"status_code": 0, "has_more": 0, "data": []}))
    a, _ = _ad(vc)
    assert a.kham_pha(_yc("tu_khoa", "zzzz", 5), bao_tien_do=_khong_bao) == []


def test_tim_khong_phien_thi_can_dang_nhap_khong_cham_mang():
    """Donor: tìm Douyin đòi đăng nhập (`DOUYIN_NEED_LOGIN` 2483) ⇒ chặn trước, không gửi request ẩn danh."""
    vc = VanChuyen()
    a, nha = _ad(vc, tep_cookie=None)
    with pytest.raises(LoiCao) as e:
        a.kham_pha(_yc("tu_khoa", "x", 5), bao_tien_do=_khong_bao)
    assert e.value.ma == "can_dang_nhap" and e.value.tam_thoi is False
    assert nha.cookie == [] and vc.goi == []


def test_status_2483_la_can_dang_nhap():
    vc = VanChuyen(_json({"status_code": 2483, "status_msg": "请先登录"}))
    a, _ = _ad(vc)
    with pytest.raises(LoiCao) as e:
        a.kham_pha(_yc("tu_khoa", "x", 5), bao_tien_do=_khong_bao)
    assert e.value.ma == "can_dang_nhap" and e.value.tam_thoi is False
    assert "请先登录" not in e.value.thong_diep           # không lộ văn bản thô của nền


def test_status_khac_0_la_nen_chan():
    vc = VanChuyen(_json({"status_code": 5, "status_msg": "x"}))
    a, _ = _ad(vc)
    with pytest.raises(LoiCao) as e:
        a.kham_pha(_yc("kenh", SEC, 5), bao_tien_do=_khong_bao)
    assert e.value.ma == "nen_chan" and e.value.tam_thoi is False


def test_than_rong_thu_lai_mot_lan_voi_chu_ky_moi_roi_nen_chan():
    ky_goi = []
    vc = VanChuyen((200, b""), (200, b"  "))
    a = DouyinAdapter(van_chuyen_factory=lambda c: vc, ky=lambda q, ua: ky_goi.append(q) or "K")
    a.tep_cookie = "c.txt"
    with pytest.raises(LoiCao) as e:
        a.kham_pha(_yc("tu_khoa", "x", 5), bao_tien_do=_khong_bao)
    assert e.value.ma == "nen_chan" and e.value.tam_thoi is False
    assert len(vc.goi) == 2 and len(ky_goi) == 2


def test_than_rong_lan_dau_roi_co_du_lieu_thi_qua():
    vc = VanChuyen((200, b""), _json({"status_code": 0, "has_more": 0, "data": [{"aweme_info": _aweme(ID1)}]}))
    a, _ = _ad(vc)
    assert [m.id for m in a.kham_pha(_yc("tu_khoa", "x", 5), bao_tien_do=_khong_bao)] == [ID1]


@pytest.mark.parametrize("phan_hoi,ma,tam_thoi", [
    ((403, b'{"ArgusSecurityPlugin":1}'), "nen_chan", False),
    ((200, b"<html>verify</html>"), "nen_chan", False),
    ((200, b"[1,2]"), "nen_chan", False),
    ((502, b""), "mang", True),
])
def test_phan_loai_http(phan_hoi, ma, tam_thoi):
    vc = VanChuyen(phan_hoi)
    a, _ = _ad(vc)
    with pytest.raises(LoiCao) as e:
        a.kham_pha(_yc("kenh", SEC, 5), bao_tien_do=_khong_bao)
    assert (e.value.ma, e.value.tam_thoi) == (ma, tam_thoi)


def test_loi_mang_tu_van_chuyen_di_thang():
    vc = VanChuyen(LoiCao("mang", "m", tam_thoi=True))
    a, _ = _ad(vc)
    with pytest.raises(LoiCao) as e:
        a.kham_pha(_yc("kenh", SEC, 5), bao_tien_do=_khong_bao)
    assert e.value.ma == "mang"


# ---------------------------------------------------------------- kenh
def test_kenh_tra_muc_va_tham_so_dung():
    vc = VanChuyen(_json({"status_code": 0, "has_more": 0, "max_cursor": 1700000000000, "aweme_list": [
        _aweme(ID1, desc="A"), _aweme(ID2, images=[{"url_list": ["x"]}]), _aweme(ID3, desc="C")]}))
    a, _ = _ad(vc)
    ra = a.kham_pha(_yc("kenh", f"https://www.douyin.com/user/{SEC}?vid={ID1}", 5), bao_tien_do=_khong_bao)
    assert [(m.id, m.tieu_de, m.url) for m in ra] == [
        (ID1, "A", f"https://www.douyin.com/video/{ID1}"), (ID3, "C", f"https://www.douyin.com/video/{ID3}")]
    url, _h = vc.goi[0]
    assert url.startswith("https://www.douyin.com/aweme/v1/web/aweme/post/?")
    q = _q(url)
    assert q["sec_user_id"] == SEC and q["max_cursor"] == "0" and q["count"] == "20"


def test_kenh_phan_trang_theo_max_cursor():
    vc = VanChuyen(
        _json({"status_code": 0, "has_more": 1, "max_cursor": 1700000000000, "aweme_list": [_aweme(ID1)]}),
        _json({"status_code": 0, "has_more": 0, "max_cursor": 1600000000000, "aweme_list": [_aweme(ID2)]}),
    )
    a, _ = _ad(vc)
    ra = a.kham_pha(_yc("kenh", SEC, 5), bao_tien_do=_khong_bao)
    assert [m.id for m in ra] == [ID1, ID2]
    assert _q(vc.goi[1][0])["max_cursor"] == "1700000000000"


def test_kenh_so_trang_co_tran():
    """Trang nào cũng has_more=1 nhưng toàn mục lọc bỏ ⇒ không lặp vô hạn."""
    trang = [_json({"status_code": 0, "has_more": 1, "max_cursor": 1000 - i,
                    "aweme_list": [_aweme("1")]}) for i in range(50)]
    vc = VanChuyen(*trang)
    a, _ = _ad(vc)
    assert a.kham_pha(_yc("kenh", SEC, 5), bao_tien_do=_khong_bao) == []
    assert len(vc.goi) <= dw.SO_TRANG_TOI_DA


def test_kenh_link_sai_la_url_khong_ho_tro_khong_cham_mang():
    vc = VanChuyen()
    a, nha = _ad(vc)
    with pytest.raises(LoiCao) as e:
        a.kham_pha(_yc("kenh", "https://v.douyin.com/abc123/", 5), bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro" and e.value.tam_thoi is False
    assert vc.goi == [] and nha.cookie == []


def test_kenh_khong_phien_van_thu_an_danh():
    """Kênh không bị chặn trước khi thiếu phiên (smoke quyết định); vận chuyển nhận tep_cookie=None."""
    vc = VanChuyen(_json({"status_code": 0, "has_more": 0, "aweme_list": [_aweme(ID1)]}))
    a, nha = _ad(vc, tep_cookie=None)
    assert [m.id for m in a.kham_pha(_yc("kenh", SEC, 5), bao_tien_do=_khong_bao)] == [ID1]
    assert nha.cookie == [None]


def test_mstoken_lay_tu_tep_cookie(tmp_path):
    f = tmp_path / "cookies.txt"
    f.write_text(".douyin.com\tTRUE\t/\tFALSE\t0\tmsToken\tMS1\n", encoding="utf-8")
    vc = VanChuyen(_json({"status_code": 0, "has_more": 0, "aweme_list": []}))
    a, _ = _ad(vc, tep_cookie=str(f))
    a.kham_pha(_yc("kenh", SEC, 5), bao_tien_do=_khong_bao)
    assert _q(vc.goi[0][0])["msToken"] == "MS1"


def test_huy_giua_trang_di_thang_ra_ngoai():
    class Huy(Exception):
        pass

    vc = VanChuyen(_json({"status_code": 0, "has_more": 1, "max_cursor": 5, "aweme_list": [_aweme(ID1)]}))
    a, _ = _ad(vc)

    def bao(p, m):
        if p not in (0,):
            raise Huy()

    with pytest.raises(Huy):
        a.kham_pha(_yc("kenh", SEC, 5), bao_tien_do=bao)
    assert len(vc.goi) == 1


# ---------------------------------------------------------------- link vẫn qua yt-dlp; bo chưa hỗ trợ
def test_link_van_di_qua_ytdlp_khong_dung_client_web():
    goi = []

    class Y:
        def __init__(self, o):
            self.params = o

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download=True):
            goi.append(url)
            return {"id": ID3, "title": "T"}

    vc = VanChuyen()
    a = DouyinAdapter(Y, van_chuyen_factory=Nha(vc), ky=_ky)
    ra = a.kham_pha(_yc("link", f"https://www.douyin.com/video/{ID3}", 1), bao_tien_do=_khong_bao)
    assert [m.id for m in ra] == [ID3] and goi and vc.goi == []


def test_bo_chua_ho_tro():
    with pytest.raises(NotImplementedError):
        DouyinAdapter().url_kham_pha("bo", "x", 5)


# ---------------------------------------------------------------- vận chuyển mặc định (không mạng)
class _R:
    status = 200

    def read(self):
        return b"{}"


def _ydl_gia(tao, loi=None):
    class YDL:
        def __init__(self, o):
            tao.append(o)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def urlopen(self, req):
            tao.append(req)
            if loi is not None:
                raise loi
            return _R()

    return YDL


def test_van_chuyen_mac_dinh_dung_ytdlp_voi_cookiefile():
    tao: list = []
    lay = dw.van_chuyen_ytdlp("C:/tam/c.txt", ydl_factory=_ydl_gia(tao))
    assert lay("https://www.douyin.com/x", {"User-Agent": "UA"}) == (200, b"{}")
    assert tao[0]["cookiefile"] == "C:/tam/c.txt"
    assert tao[1].url == "https://www.douyin.com/x" and tao[1].headers["User-Agent"] == "UA"


def test_van_chuyen_mac_dinh_khong_cookie_khong_cookiefile():
    tao: list = []
    dw.van_chuyen_ytdlp(None, ydl_factory=_ydl_gia(tao))("https://www.douyin.com/x", {})
    assert "cookiefile" not in tao[0]


def test_van_chuyen_mac_dinh_http_error_tra_ma_va_than():
    from yt_dlp.networking import Response
    from yt_dlp.networking.exceptions import HTTPError
    import io

    loi = HTTPError(Response(io.BytesIO(b"chan"), "https://www.douyin.com/x", {}, status=403))
    tao: list = []
    assert dw.van_chuyen_ytdlp(None, ydl_factory=_ydl_gia(tao, loi))("https://www.douyin.com/x", {}) == (403, b"chan")


def test_van_chuyen_mac_dinh_loi_mang_la_loicao_mang():
    from yt_dlp.networking.exceptions import TransportError

    tao: list = []
    with pytest.raises(LoiCao) as e:
        dw.van_chuyen_ytdlp(None, ydl_factory=_ydl_gia(tao, TransportError("timed out")))(
            "https://www.douyin.com/x", {})
    assert e.value.ma == "mang" and e.value.tam_thoi is True
