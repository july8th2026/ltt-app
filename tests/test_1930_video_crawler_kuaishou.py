"""KuaishouAdapter + tầng HTTP `kuaishou_web` — không bao giờ chạm mạng (tiêm web giả / opener giả).

Nguồn characterization (KHÔNG đọc/chép MediaCrawler — NON-COMMERCIAL; KHÔNG đọc KS-Downloader — GPLv3):
- `sonderlau/KuaiShouVideoDownload` (MIT, commit 8f1941a0e2aa9ae0d4ee3ec3ebde001e9e3ef4e6):
  `utils/GraphQLWrapper.py` (POST `https://www.kuaishou.com/graphql`, operationName `visionProfilePhotoList`,
  biến `userId`/`pcursor`/`page="profile"`); `API/get_all_videos.json` (phản hồi thật: `result=1`, `pcursor`,
  `feeds[].photo.{id,duration(ms, chuỗi),caption,coverUrl,photoUrl}`, `feeds[].author.{id,name}`;
  `photoUrl` = mp4 trực tiếp trên `v1.kwaicdn.com`/`v2.kwaicdn.com`, ảnh bìa trên `tx2.a.kwimgs.com`).
- `markbang/wgetx-skill` (MIT, commit 0e864328e643ccb87af919a4c49f3954d58a2fc8)
  `skills/wgetx/scripts/kuaishou/`: trang `https://www.kuaishou.com/short-video/<photoId>` render SSR
  `window.__APOLLO_STATE__={"defaultClient":{"VisionVideoDetailPhoto:<id>":{caption,duration(ms),coverUrl,
  photoUrl,...},"VisionVideoDetailAuthor:<uid>":{name,...}}}` — GET thuần, không cần đăng nhập;
  id mẫu `3xruk6a5qw3n6xq`, user mẫu `3x984ye63jkct29`.
- Donor (chỉ đọc) `D:\\Viral\\resources\\app-src\\web_app.py:1105-1112`: request tự động chưa đăng nhập bị
  CAPTCHA trượt `captcha.zt.kuaishou.com/...ANTICRAWL_DEFAULT`; `W:17788-17790` cookie phiên
  `passToken`/`kuaishou.server.web_st`.
"""
from __future__ import annotations

import io
import json

import pytest

from apps.video_crawler.adapters import kuaishou_web
from apps.video_crawler.adapters.base import CrawlItem, LoiCao, YeuCauCao
from apps.video_crawler.adapters.kuaishou import CDN_VIDEO, KuaishouAdapter, doc_apollo

PHOTO = "3xruk6a5qw3n6xq"          # wgetx-skill README
USER = "3x984ye63jkct29"           # wgetx-skill README
MP4 = "https://v2.kwaicdn.com/upic/2021/08/11/17/BMjAyMTA4MTExNzQ5MTlf_b_B33acb99778ad05f7b.mp4?tag=1"
BIA = "https://tx2.a.kwimgs.com/upic/2021/08/11/17/BMjAyMTA4MTExNzQ5MTlf_B01a6b112b42fa300b"


def _ip_ngoai(host):
    return ["1.1.1.1"]


def _trang(photo=PHOTO, *, duration=15000, photo_url=MP4, undefined=False):
    anh = {"id": photo, "caption": "mèo con / tập 1", "duration": duration, "coverUrl": BIA,
           "photoUrl": photo_url, "timestamp": 1628675403899}
    st = {"defaultClient": {f"VisionVideoDetailPhoto:{photo}": anh,
                            f"VisionVideoDetailAuthor:{USER}": {"id": USER, "name": "Tác giả"}}}
    js = json.dumps(st, ensure_ascii=False).replace("/", "\\u002F")
    if undefined:
        js = js.replace('"timestamp": 1628675403899', '"timestamp": undefined')
    return f"<html><head></head><body><script>window.__APOLLO_STATE__={js};(function(){{var s;}}());</script></body></html>"


def _feed(pid, dur="53166", url=MP4, ten="Tác giả kênh"):
    return {"type": 1, "author": {"id": USER, "name": ten},
            "photo": {"id": pid, "duration": dur, "caption": f"cap {pid}", "coverUrl": BIA, "photoUrl": url}}


def _gql(ten_op, feeds, *, pcursor="no_more", result=1, **them):
    return json.dumps({"data": {ten_op: {"result": result, "pcursor": pcursor, "feeds": feeds, **them}}})


class WebGia:
    def __init__(self, *, trang=None, gql=(), noi_dung=b"x" * 1000):
        self.trang, self.gql, self.noi_dung = trang, list(gql), noi_dung
        self.goi: list = []

    def lay_trang(self, url, *, cookie=""):
        self.goi.append(("trang", url, cookie))
        if isinstance(self.trang, BaseException):
            raise self.trang
        return self.trang

    def goi_graphql(self, body, *, cookie="", referer=""):
        self.goi.append(("gql", body, cookie, referer))
        r = self.gql.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r

    def tai_luong(self, url, dich, *, toi_da, kiem_url, moi_khoi):
        self.goi.append(("tai", url))
        kiem_url(url)
        if len(self.noi_dung) > toi_da:
            raise kuaishou_web.QuaLon()
        nua = len(self.noi_dung) // 2
        with open(dich, "wb") as f:
            for k in (self.noi_dung[:nua], self.noi_dung[nua:]):
                f.write(k)
                moi_khoi(f.tell(), len(self.noi_dung))
        return len(self.noi_dung)


def _ad(web, **kw):
    kw.setdefault("phan_giai", _ip_ngoai)
    return KuaishouAdapter(web, nghi_s=0, **kw)


def _yc(che_do, dau_vao, n=5):
    return YeuCauCao(nen_tang="kuaishou", che_do=che_do, dau_vao=dau_vao, so_luong=n)


def _khong_bao(pct, msg):
    pass


@pytest.fixture
def cookie(tmp_path):
    p = tmp_path / "cookies_kuaishou.txt"
    p.write_text("# Netscape HTTP Cookie File\n"
                 ".kuaishou.com\tTRUE\t/\tFALSE\t0\tpassToken\tPT-GIA\n"
                 "#HttpOnly_.kuaishou.com\tTRUE\t/\tTRUE\t0\tkuaishou.server.web_st\tST-GIA\n"
                 ".example.com\tTRUE\t/\tFALSE\t0\tla\tKHONG\n", encoding="utf-8")
    return str(p)


# ------------------------------------------------------------------ đăng ký
def test_lop_khop_registry_va_tao_tim_thay():
    from apps.video_crawler import nen_tang
    from apps.video_crawler.adapters import kuaishou
    nen = nen_tang.lay("kuaishou")
    assert nen.adapter == "kuaishou" and KuaishouAdapter.nen_tang == "kuaishou"
    lop = [v for v in vars(kuaishou).values()
           if isinstance(v, type) and getattr(v, "nen_tang", None) == "kuaishou" and hasattr(v, "tai")]
    assert lop == [KuaishouAdapter]
    assert KuaishouAdapter().tep_cookie is None


def test_id_hop_le_va_url_video():
    ad = _ad(WebGia())
    assert ad.id_hop_le(PHOTO) and ad.id_hop_le("3xdg9js6qn3u9ii")
    for xau in ("", "a/b", "..", "x:y", "a" * 65, None, 5):
        assert not ad.id_hop_le(xau)
    assert ad.url_video(PHOTO) == f"https://www.kuaishou.com/short-video/{PHOTO}"


# ------------------------------------------------------------------ Apollo
def test_doc_apollo_giai_ma_unicode_escape_va_undefined():
    st = doc_apollo(_trang(undefined=True))
    anh = st["defaultClient"][f"VisionVideoDetailPhoto:{PHOTO}"]
    assert anh["photoUrl"] == MP4 and anh["timestamp"] is None


def test_doc_apollo_khong_co_tra_none():
    assert doc_apollo("<html>captcha</html>") is None


# ------------------------------------------------------------------ link
@pytest.mark.parametrize("vao", [
    f"https://www.kuaishou.com/short-video/{PHOTO}",
    f"https://www.kuaishou.com/short-video/{PHOTO}?authorId={USER}&streamSource=profile",
    f"kuaishou.com/short-video/{PHOTO}",
])
def test_link_tra_mot_muc(vao):
    web = WebGia(trang=_trang())
    ra = _ad(web).kham_pha(_yc("link", vao), bao_tien_do=_khong_bao)
    assert ra == [CrawlItem(nen_tang="kuaishou", id=PHOTO, url=f"https://www.kuaishou.com/short-video/{PHOTO}",
                            tieu_de="mèo con / tập 1", tac_gia="Tác giả", thoi_luong_s=15, anh_bia=BIA)]
    assert web.goi[0][1] == f"https://www.kuaishou.com/short-video/{PHOTO}"   # dựng lại từ id, bỏ query khách


@pytest.mark.parametrize("vao", [
    "https://evil.com/short-video/3xruk6a5qw3n6xq",
    "https://www.kuaishou.com.evil.com/short-video/3xruk6a5qw3n6xq",
    "https://www.kuaishou.com/profile/3x984ye63jkct29",
    "https://www.kuaishou.com/short-video/../x",
])
def test_link_sai_bi_tu_choi_khong_goi_mang(vao):
    web = WebGia(trang=_trang())
    with pytest.raises(LoiCao) as e:
        _ad(web).kham_pha(_yc("link", vao), bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro" and web.goi == []


def test_link_gui_cookie_chi_cua_kuaishou(cookie):
    web = WebGia(trang=_trang())
    ad = _ad(web)
    ad.tep_cookie = cookie
    ad.kham_pha(_yc("link", f"https://www.kuaishou.com/short-video/{PHOTO}"), bao_tien_do=_khong_bao)
    assert web.goi[0][2] == "passToken=PT-GIA; kuaishou.server.web_st=ST-GIA"


def test_link_trang_captcha_la_nen_chan():
    web = WebGia(trang='<html><script src="https://captcha.zt.kuaishou.com/x?type=ANTICRAWL_DEFAULT"></script>')
    with pytest.raises(LoiCao) as e:
        _ad(web).kham_pha(_yc("link", f"https://www.kuaishou.com/short-video/{PHOTO}"), bao_tien_do=_khong_bao)
    assert e.value.ma == "nen_chan" and e.value.tam_thoi is False


def test_link_apollo_co_truy_van_chi_tiet_nhung_khong_co_video_la_khong_ton_tai():
    trang = _trang(photo="3xkhac000000000").replace(
        '{"defaultClient": {', '{"defaultClient": {"ROOT_QUERY": {"visionVideoDetail({\\"photoId\\":\\"x\\"})": null}, ', 1)
    web = WebGia(trang=trang)
    with pytest.raises(LoiCao) as e:
        _ad(web).kham_pha(_yc("link", f"https://www.kuaishou.com/short-video/{PHOTO}"), bao_tien_do=_khong_bao)
    assert e.value.ma == "khong_ton_tai"


def test_link_apollo_khong_he_co_du_lieu_chi_tiet_la_nen_chan():
    """Smoke thật 22/09: GET ẩn danh trả Apollo chỉ có ROOT_QUERY cấu hình trang (kconf/visionConfig),
    KHÔNG có truy vấn chi tiết nào — server không trả dữ liệu video cho request này ⇒ chặn, không phải "đã gỡ"."""
    trang = ('<script>window.__APOLLO_STATE__={"defaultClient":{"ROOT_QUERY":{"visionStartup":{},'
             '"visionConfig":{}}},"clients":{}};(function(){}());</script>')
    with pytest.raises(LoiCao) as e:
        _ad(WebGia(trang=trang)).kham_pha(_yc("link", f"https://www.kuaishou.com/short-video/{PHOTO}"),
                                          bao_tien_do=_khong_bao)
    assert e.value.ma == "nen_chan"


def test_link_bai_anh_la_chi_la_anh():
    web = WebGia(trang=_trang(duration=0, photo_url=""))
    with pytest.raises(LoiCao) as e:
        _ad(web).kham_pha(_yc("link", f"https://www.kuaishou.com/short-video/{PHOTO}"), bao_tien_do=_khong_bao)
    assert e.value.ma == "chi_la_anh"


@pytest.mark.parametrize("loi, ma, tam_thoi", [
    (kuaishou_web.LoiHttp(404), "khong_ton_tai", False),
    (kuaishou_web.LoiHttp(302), "nen_chan", False),
    (kuaishou_web.LoiHttp(429), "nen_chan", False),
    (kuaishou_web.LoiHttp(500), "loi_khac", True),
    (TimeoutError("timed out"), "mang", True),
    (OSError("connection reset"), "mang", True),
])
def test_loi_http_phan_loai(loi, ma, tam_thoi):
    with pytest.raises(LoiCao) as e:
        _ad(WebGia(trang=loi)).kham_pha(_yc("link", f"https://www.kuaishou.com/short-video/{PHOTO}"),
                                        bao_tien_do=_khong_bao)
    assert (e.value.ma, e.value.tam_thoi) == (ma, tam_thoi)


# ------------------------------------------------------------------ kênh / từ khoá
def test_kenh_va_tu_khoa_khong_phien_la_can_dang_nhap_khong_goi_mang():
    for che_do, vao in (("kenh", f"https://www.kuaishou.com/profile/{USER}"), ("tu_khoa", "mèo")):
        web = WebGia()
        with pytest.raises(LoiCao) as e:
            _ad(web).kham_pha(_yc(che_do, vao), bao_tien_do=_khong_bao)
        assert e.value.ma == "can_dang_nhap" and web.goi == []


@pytest.mark.parametrize("vao", [f"https://www.kuaishou.com/profile/{USER}", USER, f"www.kuaishou.com/profile/{USER}?x=1"])
def test_kenh_phan_trang_den_du_n(cookie, vao):
    web = WebGia(gql=[
        _gql("visionProfilePhotoList", [_feed("3xaaaaaaaaaaaa1"), _feed("3xaaaaaaaaaaaa2")], pcursor="1.6e12"),
        _gql("visionProfilePhotoList", [_feed("3xaaaaaaaaaaaa2"), _feed("3xaaaaaaaaaaaa3", dur="0", url=""),
                                        _feed("3xaaaaaaaaaaaa4"), _feed("3xaaaaaaaaaaaa5")], pcursor="no_more"),
    ])
    ad = _ad(web)
    ad.tep_cookie = cookie
    ra = ad.kham_pha(_yc("kenh", vao, n=3), bao_tien_do=_khong_bao)
    assert [m.id for m in ra] == ["3xaaaaaaaaaaaa1", "3xaaaaaaaaaaaa2", "3xaaaaaaaaaaaa4"]   # dedup + bỏ bài ảnh
    assert ra[0].thoi_luong_s == 53 and ra[0].tac_gia == "Tác giả kênh" and ra[0].anh_bia == BIA
    b1, b2 = web.goi[0][1], web.goi[1][1]
    assert b1["operationName"] == "visionProfilePhotoList"
    assert b1["variables"] == {"userId": USER, "pcursor": "", "page": "profile"}
    assert b2["variables"]["pcursor"] == "1.6e12"
    assert "visionProfilePhotoList(" in b1["query"]
    assert web.goi[0][2] == "passToken=PT-GIA; kuaishou.server.web_st=ST-GIA"
    assert web.goi[0][3] == f"https://www.kuaishou.com/profile/{USER}"


def test_kenh_dung_khi_het_trang(cookie):
    web = WebGia(gql=[_gql("visionProfilePhotoList", [_feed("3xaaaaaaaaaaaa1")], pcursor="no_more")])
    ad = _ad(web)
    ad.tep_cookie = cookie
    assert len(ad.kham_pha(_yc("kenh", USER, n=10), bao_tien_do=_khong_bao)) == 1
    assert len(web.goi) == 1


def test_kenh_id_sai_bi_tu_choi(cookie):
    ad = _ad(WebGia())
    ad.tep_cookie = cookie
    for vao in ("https://evil.com/profile/abc", "a/b", "https://www.kuaishou.com/short-video/3xruk6a5qw3n6xq"):
        with pytest.raises(LoiCao) as e:
            ad.kham_pha(_yc("kenh", vao), bao_tien_do=_khong_bao)
        assert e.value.ma == "url_khong_ho_tro"


def test_tu_khoa_gui_keyword_va_session(cookie):
    web = WebGia(gql=[
        _gql("visionSearchPhoto", [_feed("3xbbbbbbbbbbbb1")], pcursor="1", searchSessionId="S1"),
        _gql("visionSearchPhoto", [_feed("3xbbbbbbbbbbbb2")], pcursor="no_more", searchSessionId="S1"),
    ])
    ad = _ad(web)
    ad.tep_cookie = cookie
    ra = ad.kham_pha(_yc("tu_khoa", "  mèo con  ", n=5), bao_tien_do=_khong_bao)
    assert [m.id for m in ra] == ["3xbbbbbbbbbbbb1", "3xbbbbbbbbbbbb2"]
    b1, b2 = web.goi[0][1], web.goi[1][1]
    assert b1["operationName"] == "visionSearchPhoto"
    assert b1["variables"] == {"keyword": "mèo con", "pcursor": "", "page": "search", "searchSessionId": ""}
    assert b2["variables"]["searchSessionId"] == "S1" and b2["variables"]["pcursor"] == "1"


def test_tu_khoa_rong_bi_tu_choi(cookie):
    ad = _ad(WebGia())
    ad.tep_cookie = cookie
    with pytest.raises(LoiCao) as e:
        ad.kham_pha(_yc("tu_khoa", "   "), bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro"


@pytest.mark.parametrize("phan_hoi, ma", [
    (_gql("visionSearchPhoto", [], result=400002), "nen_chan"),                          # captcha / chặn
    (json.dumps({"result": 2, "error_msg": "请登录后再试 login"}), "can_dang_nhap"),
    ('<html>https://captcha.zt.kuaishou.com/?ANTICRAWL_DEFAULT</html>', "nen_chan"),
    (json.dumps({"data": None, "errors": [{"message": "x"}]}), "nen_chan"),
])
def test_graphql_bi_chan(cookie, phan_hoi, ma):
    ad = _ad(WebGia(gql=[phan_hoi]))
    ad.tep_cookie = cookie
    with pytest.raises(LoiCao) as e:
        ad.kham_pha(_yc("tu_khoa", "meo"), bao_tien_do=_khong_bao)
    assert e.value.ma == ma and e.value.tam_thoi is False


def test_kham_pha_loc_qua_dai(cookie):
    web = WebGia(gql=[_gql("visionSearchPhoto", [_feed("3xbbbbbbbbbbbb1", dur=str(4 * 3600 * 1000)),
                                                 _feed("3xbbbbbbbbbbbb2")])])
    ad = _ad(web)
    ad.tep_cookie = cookie
    assert [m.id for m in ad.kham_pha(_yc("tu_khoa", "meo"), bao_tien_do=_khong_bao)] == ["3xbbbbbbbbbbbb2"]


def test_kham_pha_bao_tien_do_va_huy_lan_ra(cookie):
    class Huy(Exception):
        pass

    def bao(pct, msg):
        raise Huy()

    ad = _ad(WebGia(trang=_trang()))
    with pytest.raises(Huy):
        ad.kham_pha(_yc("link", f"https://www.kuaishou.com/short-video/{PHOTO}"), bao_tien_do=bao)


# ------------------------------------------------------------------ tải
def _muc(pid=PHOTO, url=None):
    return CrawlItem(nen_tang="kuaishou", id=pid, url=url or f"https://www.kuaishou.com/short-video/{pid}",
                     tieu_de="mèo: con/1")


def test_tai_lay_url_moi_tu_trang_va_ghi_tep(tmp_path):
    web = WebGia(trang=_trang())
    bao = []
    tep = _ad(web).tai(_muc(), tmp_path, bao_tien_do=lambda p, m: bao.append(p))
    assert tep.duong_dan == tmp_path / f"{PHOTO}.mp4" and tep.duong_dan.read_bytes() == b"x" * 1000
    assert tep.kich_thuoc == 1000 and tep.ten_hien_thi == f"mèo con 1 [{PHOTO}].mp4"
    assert [g[0] for g in web.goi] == ["trang", "tai"] and web.goi[1][1] == MP4
    assert bao and all(0 <= p <= 98 for p in bao) and bao[-1] == 98


@pytest.mark.parametrize("muc", [
    _muc(pid="a/b"),
    _muc(url="https://evil.com/short-video/3xruk6a5qw3n6xq"),
    _muc(url=f"https://www.kuaishou.com/short-video/{PHOTO}?x=1"),
])
def test_tai_tu_choi_muc_gia_mao(tmp_path, muc):
    web = WebGia(trang=_trang())
    with pytest.raises(LoiCao) as e:
        _ad(web).tai(muc, tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "url_khong_ho_tro" and web.goi == []


@pytest.mark.parametrize("mp4, ip", [
    ("https://evil.com/x.mp4", "1.1.1.1"),
    ("http://127.0.0.1/x.mp4", "127.0.0.1"),
    ("https://v2.kwaicdn.com/x.mp4", "10.0.0.5"),        # DNS rebinding về nội bộ
    ("file:///c:/x.mp4", "1.1.1.1"),
])
def test_tai_chan_url_ngoai_cdn_hoac_noi_bo(tmp_path, mp4, ip):
    web = WebGia(trang=_trang(photo_url=mp4))
    with pytest.raises(LoiCao) as e:
        _ad(web, phan_giai=lambda h: [ip]).tai(_muc(), tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "cdn_khong_cho_phep" and e.value.tam_thoi is False
    assert not list(tmp_path.iterdir())


def test_cdn_video_la_mien_kuaishou():
    assert set(CDN_VIDEO) == {"kwaicdn.com", "kwimgs.com", "yximgs.com"}


def test_tai_qua_lon(tmp_path):
    web = WebGia(trang=_trang(), noi_dung=b"y" * 2000)
    with pytest.raises(LoiCao) as e:
        _ad(web, max_filesize=1000).tai(_muc(), tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "qua_lon" and e.value.tam_thoi is False


def test_tai_qua_dai(tmp_path):
    web = WebGia(trang=_trang(duration=4 * 3600 * 1000))
    with pytest.raises(LoiCao) as e:
        _ad(web).tai(_muc(), tmp_path, bao_tien_do=_khong_bao)
    assert e.value.ma == "qua_dai"


def test_tai_huy_giua_chung_lan_ra_ngoai_le_goc(tmp_path):
    class Huy(Exception):
        pass

    dem = []

    def bao(p, m):
        dem.append(p)
        if len(dem) >= 2:
            raise Huy()

    with pytest.raises(Huy):
        _ad(WebGia(trang=_trang())).tai(_muc(), tmp_path, bao_tien_do=bao)


# ------------------------------------------------------------------ tầng HTTP thật (opener giả)
class _PhanHoi(io.BytesIO):
    def __init__(self, du_lieu, *, status=200, headers=None):
        super().__init__(du_lieu)
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _web_gia(phan_hoi, ghi):
    web = kuaishou_web.KuaishouWeb()

    def mo(req, *, theo_chuyen_huong, kiem_url=None):
        ghi.append((req, theo_chuyen_huong))
        if isinstance(phan_hoi, BaseException):
            raise phan_hoi
        return phan_hoi

    web._mo = mo
    return web


def test_web_lay_trang_gui_cookie_khong_theo_chuyen_huong():
    ghi = []
    web = _web_gia(_PhanHoi("chào".encode()), ghi)
    assert web.lay_trang("https://www.kuaishou.com/short-video/x", cookie="a=b") == "chào"
    req, theo = ghi[0]
    assert theo is False and req.get_header("Cookie") == "a=b" and "Mozilla" in req.get_header("User-agent")


def test_web_graphql_post_json():
    ghi = []
    web = _web_gia(_PhanHoi(b'{"data":{}}'), ghi)
    assert web.goi_graphql({"a": 1}, cookie="", referer="https://www.kuaishou.com/") == '{"data":{}}'
    req, _ = ghi[0]
    assert req.full_url == "https://www.kuaishou.com/graphql" and req.get_method() == "POST"
    assert json.loads(req.data) == {"a": 1} and req.get_header("Content-type") == "application/json"
    assert req.get_header("Cookie") is None and req.get_header("Referer") == "https://www.kuaishou.com/"


def test_web_status_khac_200_la_loi_http():
    web = _web_gia(_PhanHoi(b"", status=302), [])
    with pytest.raises(kuaishou_web.LoiHttp) as e:
        web.lay_trang("https://www.kuaishou.com/short-video/x")
    assert e.value.status == 302


def test_web_http_error_la_loi_http():
    import urllib.error
    web = _web_gia(urllib.error.HTTPError("u", 404, "nf", {}, None), [])
    with pytest.raises(kuaishou_web.LoiHttp) as e:
        web.lay_trang("https://www.kuaishou.com/short-video/x")
    assert e.value.status == 404


def test_web_tai_luong_theo_khoi_va_kiem_url(tmp_path):
    ghi, kiem, khoi = [], [], []
    web = _web_gia(_PhanHoi(b"z" * 300_000, headers={"Content-Length": "300000"}), ghi)
    n = web.tai_luong("https://v2.kwaicdn.com/a.mp4", tmp_path / "a.mp4", toi_da=10**6,
                      kiem_url=lambda u: kiem.append(u) or u, moi_khoi=lambda x, t: khoi.append((x, t)))
    assert n == 300_000 and (tmp_path / "a.mp4").stat().st_size == 300_000
    assert kiem == ["https://v2.kwaicdn.com/a.mp4"] and ghi[0][1] is True
    assert khoi[-1] == (300_000, 300_000) and len(khoi) >= 2


def test_web_tai_luong_qua_lon_theo_content_length_va_theo_luong(tmp_path):
    for headers in ({"Content-Length": "5000"}, {}):
        web = _web_gia(_PhanHoi(b"z" * 5000, headers=headers), [])
        with pytest.raises(kuaishou_web.QuaLon):
            web.tai_luong("https://v2.kwaicdn.com/a.mp4", tmp_path / "a.mp4", toi_da=1000,
                          kiem_url=lambda u: u, moi_khoi=lambda x, t: None)
        assert not (tmp_path / "a.mp4").exists()


def test_web_tai_luong_huy_xoa_tep_do_dang(tmp_path):
    web = _web_gia(_PhanHoi(b"z" * 300_000), [])

    def moi_khoi(x, t):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        web.tai_luong("https://v2.kwaicdn.com/a.mp4", tmp_path / "a.mp4", toi_da=10**6,
                      kiem_url=lambda u: u, moi_khoi=moi_khoi)
    assert not (tmp_path / "a.mp4").exists()


def test_web_chuyen_huong_tai_bi_kiem():
    """Handler chuyển hướng của đường tải gọi `kiem_url` cho MỖI đích mới (chặn CDN giả/IP nội bộ)."""
    import urllib.request

    bi_kiem = []

    def kiem(u):
        bi_kiem.append(u)
        if "evil" in u:
            raise ValueError("chan")
        return u

    h = kuaishou_web._ChuyenHuongCoKiem(kiem)
    req = urllib.request.Request("https://v2.kwaicdn.com/a.mp4")
    assert h.redirect_request(req, None, 302, "Found", {}, "https://v1.kwaicdn.com/b.mp4") is not None
    with pytest.raises(ValueError):
        h.redirect_request(req, None, 302, "Found", {}, "https://evil.com/b.mp4")
    assert bi_kiem == ["https://v1.kwaicdn.com/b.mp4", "https://evil.com/b.mp4"]
