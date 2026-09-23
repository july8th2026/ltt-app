"""Xiaohongshu `tu_khoa` + `kenh` qua API web (edith) — không bao giờ chạm mạng.

Nguồn cấu trúc (không chép mã, chỉ hình dạng dữ liệu/điểm cuối):
- `ReaJason/xhs` (MIT, SHA f4b62d9f) `xhs/core.py`: `get_note_by_keyword` POST `/api/sns/web/v1/search/notes`
  (keyword, page, page_size, search_id, sort, note_type — `SearchNoteType.VIDEO = 1`) trả `{has_more, items}`;
  `get_user_notes` GET `/api/sns/web/v1/user_posted` (num, cursor, user_id, image_scenes) trả
  `{cursor, has_more, notes: [{note_id, xsec_token, type, display_title, cover, user}]}`;
  `xhs/exception.py`: 300012 IP bị chặn, 300015 ký sai, -100 hết phiên; HTTP 461/471 = captcha.
- Mục kết quả tìm: `{id, model_type: "note", xsec_token, note_card: {type, display_title, user, cover}}`
  (`1sdv/TripStar` `backend/app/services/xhs_service.py`, `autoclaw-cc/xiaohongshu-skills` `scripts/xhs/types.py`).
- Ký: `Cloxl/xhshow` 0.2.0 (MIT, PyPI) — thuần Python, không trình duyệt.
Id/token mẫu: như `test_1916` (yt-dlp `_TESTS`, issue #13728/#16519).
"""
from __future__ import annotations

import json
import re
from http.cookiejar import Cookie
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from apps.video_crawler.adapters import xhs_web
from apps.video_crawler.adapters.base import ID_AN_TOAN, LoiCao, YeuCauCao
from apps.video_crawler.adapters.xiaohongshu import XiaohongshuAdapter

NOTE_1 = "6411cf99000000001300b6d9"
NOTE_2, TOKEN_2 = "674051740000000007027a15", "CBgeL8Dxd1ZWBhwqRd568gAZ_iwG-9JIf9tnApNmteU2E="
NOTE_3, TOKEN_3 = "644f0a200000000013030186", "ABbpHsLUVDfzFGQhVGvLVuGvU3I6sq5eTi_zhlKGjCbmk="
NOTE_4, TOKEN_4 = "69ce30d3000000002100791c", "ABQNiuPr9iBog5WzaYReZHkB_M-H0_ueF_FpSximzkuxc="
USER = "5ff0e6410000000001008400"


def _cookie(ten, gia_tri, mien=".xiaohongshu.com"):
    return Cookie(0, ten, gia_tri, None, False, mien, True, True, "/", True, False, None, False, None, None, {})


COOKIE_DU = [_cookie("a1", "gia-a1"), _cookie("web_session", "gia-ws"), _cookie("webId", "gia-webid")]


class Resp:
    def __init__(self, du_lieu, status=200):
        self.status = status
        self._b = json.dumps(du_lieu).encode()

    def read(self):
        return self._b


class FakeYDL:
    def __init__(self, opts, tra_loi, cookie):
        self.params = opts
        self.tra_loi = list(tra_loi)
        self.cookiejar = list(cookie)
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

    def extract_info(self, url, download=True):          # chế độ web KHÔNG được gọi yt-dlp extractor
        raise AssertionError("tu_khoa/kenh khong di qua extractor yt-dlp")


class Nha:
    def __init__(self, tra_loi, cookie=COOKIE_DU):
        self.tra_loi, self.cookie = tra_loi, cookie
        self.tao: list[FakeYDL] = []

    def __call__(self, opts):
        y = FakeYDL(opts, self.tra_loi, self.cookie)
        self.tao.append(y)
        return y

    @property
    def req(self):
        return [r for y in self.tao for r in y.req]


class KyGia:
    def __init__(self):
        self.goi: list = []

    def ky(self, method, url, cookies, *, params=None, payload=None):
        self.goi.append((method, url, dict(cookies), params, payload))
        return {"x-s": "XYS_gia", "x-t": "1", "x-s-common": "gia"}

    def url_get(self, url, params):
        return url + "?" + urlencode(params)

    def search_id(self):
        return "sid-gia"


def _a(tra_loi, *, cookie=COOKIE_DU, co_tep=True):
    nha, ky = Nha(tra_loi, cookie), KyGia()
    a = XiaohongshuAdapter(nha, ky=ky, ngu=lambda s: None)
    a.tep_cookie = "C:/tam/cookies.txt" if co_tep else None
    return a, nha, ky


def _yc(che_do, dau_vao, n=5):
    return YeuCauCao(nen_tang="xiaohongshu", che_do=che_do, dau_vao=dau_vao, so_luong=n)


def _bao(pct, msg):
    pass


def _muc_tim(note, tok, loai="video", model="note", tieu_de="T"):
    return {"id": note, "model_type": model, "xsec_token": tok,
            "note_card": {"type": loai, "display_title": tieu_de,
                          "user": {"user_id": USER, "nickname": "Nguoi A"},
                          "cover": {"url_default": f"https://sns-webpic-qc.xhscdn.com/{note}"}}}


def _trang_tim(items, has_more=False):
    return Resp({"code": 0, "success": True, "msg": "", "data": {"has_more": has_more, "items": items}})


def _trang_kenh(notes, has_more=False, cursor=""):
    return Resp({"code": 0, "success": True, "data": {"cursor": cursor, "has_more": has_more, "notes": notes}})


def _note_kenh(note, tok, loai="video"):
    return {"note_id": note, "xsec_token": tok, "type": loai, "display_title": "K",
            "user": {"user_id": USER, "nickname": "Kenh B"}, "cover": {"url_default": "https://x.xhscdn.com/c"}}


# ------------------------------------------------------------------ tu_khoa
def test_tu_khoa_chi_giu_note_video_co_token_va_url_chuan():
    a, nha, ky = _a([_trang_tim([
        _muc_tim(NOTE_2, TOKEN_2),
        _muc_tim(NOTE_3, TOKEN_3, loai="normal"),          # note ảnh
        _muc_tim(NOTE_4, ""),                               # thiếu token ⇒ không tải được
        {"id": "hq1", "model_type": "hot_query"},           # không phải note
        _muc_tim(NOTE_1, "bad"),                            # token sai mẫu
    ])])
    ra = a.kham_pha(_yc("tu_khoa", "mèo con", 5), bao_tien_do=_bao)
    assert [m.id for m in ra] == [NOTE_2]
    m = ra[0]
    assert m.url == f"https://www.xiaohongshu.com/explore/{NOTE_2}?xsec_token={TOKEN_2}"
    assert a.url_chuan(m.id, m.url) == m.url                 # tai() chấp nhận chính URL này
    assert re.fullmatch(ID_AN_TOAN, m.id)
    assert (m.tieu_de, m.tac_gia, m.anh_bia) == ("T", "Nguoi A", f"https://sns-webpic-qc.xhscdn.com/{NOTE_2}")
    assert m.thoi_luong_s is None


def test_tu_khoa_goi_dung_diem_cuoi_ky_va_than_json_khop_chu_ky():
    a, nha, ky = _a([_trang_tim([_muc_tim(NOTE_2, TOKEN_2)])])
    a.kham_pha(_yc("tu_khoa", "mèo", 5), bao_tien_do=_bao)
    (r,) = nha.req
    assert r.method == "POST" and r.url == "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes"
    than = json.loads(r.data.decode())
    assert than["keyword"] == "mèo" and than["page"] == 1 and than["note_type"] == 1
    assert than["search_id"] == "sid-gia"
    method, url, cookies, params, payload = ky.goi[0]
    assert (method, url, params) == ("POST", r.url, None) and payload == than
    assert cookies["a1"] == "gia-a1" and cookies["web_session"] == "gia-ws"
    h = {k.lower(): v for k, v in r.headers.items()}
    assert h["x-s"] == "XYS_gia" and h["x-t"] == "1" and h["x-s-common"] == "gia"
    assert h["origin"] == "https://www.xiaohongshu.com"
    assert nha.tao[0].params.get("cookiefile") == "C:/tam/cookies.txt"


def test_tu_khoa_phan_trang_toi_du_n():
    a, nha, ky = _a([
        _trang_tim([_muc_tim(NOTE_1, TOKEN_2), _muc_tim(NOTE_2, TOKEN_2)], has_more=True),
        _trang_tim([_muc_tim(NOTE_3, TOKEN_3), _muc_tim(NOTE_4, TOKEN_4)], has_more=True),
    ])
    ra = a.kham_pha(_yc("tu_khoa", "x", 3), bao_tien_do=_bao)
    assert [m.id for m in ra] == [NOTE_1, NOTE_2, NOTE_3]
    assert [json.loads(r.data)["page"] for r in nha.req] == [1, 2]


def test_tu_khoa_het_trang_thi_dung():
    a, nha, ky = _a([_trang_tim([_muc_tim(NOTE_2, TOKEN_2)], has_more=False)])
    assert len(a.kham_pha(_yc("tu_khoa", "x", 10), bao_tien_do=_bao)) == 1
    assert len(nha.req) == 1


def test_tu_khoa_bo_trung_id():
    a, nha, ky = _a([_trang_tim([_muc_tim(NOTE_2, TOKEN_2), _muc_tim(NOTE_2, TOKEN_2)])])
    assert [m.id for m in a.kham_pha(_yc("tu_khoa", "x", 5), bao_tien_do=_bao)] == [NOTE_2]


# ------------------------------------------------------------------ kenh
@pytest.mark.parametrize("vao", [
    f"https://www.xiaohongshu.com/user/profile/{USER}",
    f"https://www.xiaohongshu.com/user/profile/{USER}?xsec_token={TOKEN_2}&xsec_source=pc_note",
    f"https://xiaohongshu.com/user/profile/{USER}/",
    USER,
])
def test_kenh_nhan_url_ho_so_hoac_id(vao):
    a, nha, ky = _a([_trang_kenh([_note_kenh(NOTE_2, TOKEN_2)])])
    ra = a.kham_pha(_yc("kenh", vao, 5), bao_tien_do=_bao)
    assert [m.id for m in ra] == [NOTE_2]
    (r,) = nha.req
    sp = urlsplit(r.url)
    assert r.method == "GET" and f"{sp.scheme}://{sp.netloc}{sp.path}" == \
        "https://edith.xiaohongshu.com/api/sns/web/v1/user_posted"
    q = parse_qs(sp.query, keep_blank_values=True)
    assert q["user_id"] == [USER] and q["cursor"] == [""]
    assert ky.goi[0][3]["user_id"] == USER                   # ký đúng bộ tham số đem gửi


def test_kenh_chi_video_va_phan_trang_theo_cursor():
    a, nha, ky = _a([
        _trang_kenh([_note_kenh(NOTE_1, TOKEN_2, loai="normal"), _note_kenh(NOTE_2, TOKEN_2)],
                    has_more=True, cursor="c1"),
        _trang_kenh([_note_kenh(NOTE_3, TOKEN_3), _note_kenh(NOTE_4, "")], has_more=False, cursor="c2"),
    ])
    ra = a.kham_pha(_yc("kenh", USER, 5), bao_tien_do=_bao)
    assert [m.id for m in ra] == [NOTE_2, NOTE_3]
    assert ra[0].tac_gia == "Kenh B" and ra[0].url.endswith(f"xsec_token={TOKEN_2}")
    assert [parse_qs(urlsplit(r.url).query, keep_blank_values=True)["cursor"] for r in nha.req] == [[""], ["c1"]]


@pytest.mark.parametrize("vao", [
    "https://www.xiaohongshu.com/explore/" + NOTE_2,
    "https://www.xiaohongshu.com/user/profile/abc",
    "https://evil.com/user/profile/" + USER,
    "ten_nguoi_dung",
])
def test_kenh_dau_vao_sai_thi_tu_choi_khong_goi_mang(vao):
    a, nha, ky = _a([])
    with pytest.raises(LoiCao) as e:
        a.kham_pha(_yc("kenh", vao, 5), bao_tien_do=_bao)
    assert e.value.ma == "url_khong_ho_tro" and e.value.tam_thoi is False
    assert nha.req == []


# ------------------------------------------------------------------ phiên + lỗi
@pytest.mark.parametrize("cookie,co_tep", [
    (COOKIE_DU, False),                                               # không có phiên
    ([_cookie("a1", "gia-a1")], True),                                # thiếu web_session
    ([_cookie("a1", "x", ".evil.com"), _cookie("web_session", "y", ".evil.com")], True),   # sai miền
])
def test_chua_dang_nhap_thi_can_dang_nhap(cookie, co_tep):
    a, nha, ky = _a([], cookie=cookie, co_tep=co_tep)
    with pytest.raises(LoiCao) as e:
        a.kham_pha(_yc("tu_khoa", "x", 5), bao_tien_do=_bao)
    assert e.value.ma == "can_dang_nhap" and e.value.tam_thoi is False
    assert nha.req == [] and ky.goi == []


def _loi_http(status):
    from yt_dlp.networking import Response
    from yt_dlp.networking.exceptions import HTTPError
    import io
    return HTTPError(Response(io.BytesIO(b'{"code":-1}'), "https://edith.xiaohongshu.com/x", {}, status=status))


@pytest.mark.parametrize("tra,ma,tam_thoi", [
    (lambda: _loi_http(461), "nen_chan", False),
    (lambda: _loi_http(471), "nen_chan", False),
    (lambda: Resp({"code": 300017, "success": False, "msg": "x"}), "nen_chan", False),
    (lambda: Resp({"code": -104, "success": False, "msg": "x"}), "nen_chan", False),
    (lambda: Resp({"code": 300012, "success": False, "msg": "x"}), "nen_chan", False),
    (lambda: Resp({"code": 300015, "success": False, "msg": "x"}), "nen_chan", False),
    (lambda: Resp({"code": -100, "success": False, "msg": "x"}), "can_dang_nhap", False),
    # smoke thật 22/09 (ký xhshow, cookie a1 tự sinh, không web_session): -101 "无登录信息，或登录信息为空"
    (lambda: Resp({"code": -101, "success": False, "msg": "x"}), "can_dang_nhap", False),
    (lambda: Resp({"code": 12345, "success": False, "msg": "x"}), "loi_khac", True),
    (lambda: Resp("khong phai dict"), "loi_khac", True),
    (lambda: _loi_http(500), "loi_khac", True),
])
def test_phan_loai_loi_api(tra, ma, tam_thoi):
    a, nha, ky = _a([tra()])
    with pytest.raises(LoiCao) as e:
        a.kham_pha(_yc("tu_khoa", "x", 5), bao_tien_do=_bao)
    assert (e.value.ma, e.value.tam_thoi) == (ma, tam_thoi)
    assert "gia-ws" not in e.value.thong_diep and "edith" not in e.value.thong_diep


def test_loi_mang_la_tam_thoi():
    from yt_dlp.networking.exceptions import TransportError
    a, nha, ky = _a([TransportError("timed out")])
    with pytest.raises(LoiCao) as e:
        a.kham_pha(_yc("kenh", USER, 5), bao_tien_do=_bao)
    assert (e.value.ma, e.value.tam_thoi) == ("mang", True)


def test_bao_tien_do_moi_trang_va_huy_duoc():
    class Huy(Exception):
        pass

    goi = []

    def bao(pct, msg):
        goi.append(pct)
        if len(goi) >= 2:
            raise Huy

    a, nha, ky = _a([_trang_tim([_muc_tim(NOTE_2, TOKEN_2)], has_more=True)] * 5)
    with pytest.raises(Huy):
        a.kham_pha(_yc("tu_khoa", "x", 20), bao_tien_do=bao)
    assert len(nha.req) <= 2


# ------------------------------------------------------------------ ký thật (xhshow, không mạng)
def test_ky_xhshow_that_ra_du_header():
    h = xhs_web.KyXhshow().ky("GET", "https://edith.xiaohongshu.com/api/sns/web/v1/user_posted",
                              {"a1": "gia-a1", "web_session": "gia-ws", "webId": "gia"},
                              params={"num": 30, "cursor": "", "user_id": USER})
    assert {"x-s", "x-t", "x-s-common"} <= {k.lower() for k in h}
