"""Node `core.http` (`platform_core/workflow/nut_loi/http.py`) - plan wf-v2 P5/T3.

CO CHE DANG KY - vi sao co phep kiem rieng cho no

   Lan p5-http KHONG duoc sua `nut_loi/__init__.py` (lan p3 dang o do). Mot
   tep moi trong `nut_loi/` **khong tu dong** duoc nap: `dang_ky()` chi chay
   khi mo-dun duoc import. Nen dieu phai chung minh la: import tep nay LA du
   de node co mat trong `nut_loi.tat_ca()`.

   Neu khong do dieu do, ca cum test duoi day van xanh trong khi Canvas
   khong he thay node - dung khuon "hai cho khai cung mot dieu, khong ai bat
   khop".

DOI CHUNG

   `test_doi_chung_may_chu_gia_that_su_tra_loi` chung minh may chu HTTP gia
   co that. Khong co no, moi phep "FAILED" ben duoi xanh ca khi node khong
   he gui gi.
"""
from __future__ import annotations

import http.server
import json
import threading

import pytest

import platform_core.an_toan_mang as an_toan_mang
from platform_core.workflow import nut_loi
from platform_core.workflow.nut_loi import http as nut_http


class _Tay(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _tra(self, ma, than, them=None):
        self.send_response(ma)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(than)))
        for k, v in (them or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(than)

    def _ghi(self, than=b""):
        self.server.da_nhan.append({
            "duong": self.path, "cach": self.command, "than": than,
            "kieu": self.headers.get("Content-Type", ""),
            "rieng": self.headers.get("X-Rieng", ""),
            "uy_quyen": self.headers.get("Authorization", ""),
            "host": self.headers.get("Host", "")})

    def do_GET(self):  # noqa: N802
        self._ghi()
        if self.path == "/loi-500":
            self._tra(500, b'{"loi":"vo"}')
        elif self.path == "/loi-404":
            self._tra(404, b'{"loi":"khong co"}')
        elif self.path == "/that-to":
            self._tra(200, b"x" * (3 * 1024 * 1024))
        elif self.path == "/chuyen-huong":
            self._tra(302, b"{}", {"Location": "/dich-chuyen-huong"})
        elif self.path == "/dich-chuyen-huong":
            self._tra(200, b'{"toi":"dich"}')
        elif self.path == "/khong-phai-json":
            self._tra(200, b"<html>xin chao</html>")
        else:
            self._tra(200, b'{"ok":true}')

    def do_POST(self):  # noqa: N802
        self._ghi(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
        self._tra(200, b'{"ok":true}')

    do_PUT = do_POST
    do_DELETE = do_GET

    def log_message(self, *a):
        return


class _MayChu(http.server.ThreadingHTTPServer):
    """Nuot loi socket. `test_phan_hoi_qua_lon_bi_cat_thanh_FAILED` CO Y ngat
    giua chung, nen may chu gia se thay broken pipe - do la dau hieu phep kiem
    lam dung viec, khong phai mot su co can in ra."""

    def handle_error(self, request, client_address):
        return


@pytest.fixture()
def may_chu():
    """Cong EPHEMERAL tren 127.0.0.1. KHONG bao gio 8100 (production)."""
    srv = _MayChu(("127.0.0.1", 0), _Tay)
    srv.da_nhan = []
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()


def _url(srv, duong="/a"):
    return f"http://may-chu-gia.test:{srv.server_address[1]}{duong}"


def _chay(tham_so, **kw):
    """Goi node voi chinh sach THA + DNS gia tro ve may chu cuc bo."""
    kw.setdefault("chinh_sach", an_toan_mang.CHINH_SACH_NOI_BO)
    kw.setdefault("bo_phan_giai", lambda h: ["127.0.0.1"])
    return nut_http.thuc_thi(tham_so, **kw)


# -- 1. Co che dang ky -------------------------------------------------------

def test_import_mo_dun_LA_DU_de_node_co_mat_trong_so():
    """Khong sua `nut_loi/__init__.py` - import tep la du."""
    so = nut_loi.tat_ca()
    assert "core.http" in so, sorted(so)
    assert so["core.http"] is nut_http.CORE_HTTP


def test_dinh_nghia_node_hop_le():
    nd = nut_http.CORE_HTTP
    assert nd.type_version == 1
    assert nd.category == "NETWORK"
    assert nd.quyen == frozenset({"network"})
    # `publish_duoc=False` cho toi khi `bien_dich._node` biet dich `core.*`
    # - cung ly do `trigger.manual` va `ai.*` hom nay deu False.
    assert nd.publish_duoc is False
    assert set(nd.ma_loi) == set(nut_http.MA_LOI_HTTP)


def test_tham_so_khai_du_bon_thu_brief_doi():
    thuoc_tinh = nut_http.CORE_HTTP.tham_so["properties"]
    for ten in ("cach", "url", "headers", "than", "thoi_cho_s"):
        assert ten in thuoc_tinh, ten
    assert set(thuoc_tinh["cach"]["enum"]) == set(nut_http.CACH_CHO_PHEP)


# -- 2. Doi chung: may chu gia that su tra loi -------------------------------

def test_doi_chung_may_chu_gia_that_su_tra_loi(may_chu):
    ra = _chay({"cach": "GET", "url": _url(may_chu, "/xin-chao")})
    assert ra["trang_thai"] == 200
    assert ra["than"] == {"ok": True}
    assert may_chu.da_nhan[-1]["duong"] == "/xin-chao"


# -- 3. Phuong thuc, header, than, thoi cho ----------------------------------

@pytest.mark.parametrize("cach", ["GET", "POST", "PUT", "DELETE"])
def test_moi_phuong_thuc_di_dung_phuong_thuc(may_chu, cach):
    _chay({"cach": cach, "url": _url(may_chu, "/m"),
           "than": {"a": 1} if cach in ("POST", "PUT") else None})
    assert may_chu.da_nhan[-1]["cach"] == cach


def test_header_cua_nguoi_soan_di_toi_noi(may_chu):
    _chay({"cach": "GET", "url": _url(may_chu, "/h"),
           "headers": {"X-Rieng": "gia-tri-rieng"}})
    assert may_chu.da_nhan[-1]["rieng"] == "gia-tri-rieng"


def test_than_dict_di_thanh_JSON(may_chu):
    _chay({"cach": "POST", "url": _url(may_chu, "/p"),
           "than": {"ten": "Thang", "so": 7}})
    nhan = may_chu.da_nhan[-1]
    assert json.loads(nhan["than"]) == {"ten": "Thang", "so": 7}
    assert "application/json" in nhan["kieu"]


def test_than_chuoi_di_nguyen_van(may_chu):
    _chay({"cach": "POST", "url": _url(may_chu, "/p"), "than": "chu thuan"})
    assert may_chu.da_nhan[-1]["than"] == b"chu thuan"


def test_cach_khong_hop_le_bi_tu_choi_TRUOC_khi_gui(may_chu):
    with pytest.raises(nut_http.LoiHttp) as loi:
        _chay({"cach": "TRACE", "url": _url(may_chu)})
    assert loi.value.ma == "dau_vao_sai"
    assert not may_chu.da_nhan


def test_thoi_cho_duoc_truyen_xuong():
    """Thoi cho la mot so, khong phai mot loi hua trong tai lieu."""
    da_thay = {}

    class _ClientGia:
        def request(self, *a, **kw):
            raise AssertionError("khong toi day")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def _tao(chinh_sach=None, bo_phan_giai=None, **kw):
        da_thay.update(kw)
        return _ClientGia()

    # `_ClientGia` khong co `.stream` -> AttributeError. Bat DUNG loai do,
    # khong phai `Exception`: bat rong thi phep kiem van xanh ca khi hong vi
    # mot ly do hoan toan khac.
    with pytest.raises(AttributeError):
        _chay({"cach": "GET", "url": "https://x.example.com/a",
               "thoi_cho_s": 3.5}, tao_client=_tao)
    assert da_thay.get("timeout") == 3.5


# -- 4. Anh xa ma loi -> FAILED ----------------------------------------------

@pytest.mark.parametrize("duong,ma_http", [("/loi-404", 404), ("/loi-500", 500)])
def test_ma_trang_thai_loi_thanh_FAILED(may_chu, duong, ma_http):
    with pytest.raises(nut_http.LoiHttp) as loi:
        _chay({"cach": "GET", "url": _url(may_chu, duong)})
    assert loi.value.ma == "ma_trang_thai_loi"
    assert loi.value.trang_thai == ma_http
    # Than loi VAN phai den duoc tay nguoi soan workflow, neu khong ho khong
    # cach nao biet API kia phan nan cai gi.
    assert loi.value.than


def test_doi_chung_cho_phep_ma_loi_thi_KHONG_FAILED(may_chu):
    """Nguoc chieu: co API dung 404 lam cau tra loi binh thuong."""
    ra = _chay({"cach": "GET", "url": _url(may_chu, "/loi-404"),
                "ma_chap_nhan": [200, 404]})
    assert ra["trang_thai"] == 404


def test_dia_chi_bi_chan_thanh_FAILED_bi_chan_ssrf():
    with pytest.raises(nut_http.LoiHttp) as loi:
        nut_http.thuc_thi({"cach": "GET", "url": "https://khach.example.com/x"},
                          bo_phan_giai=lambda h: ["100.64.0.1"])
    assert loi.value.ma == "bi_chan_ssrf"


def test_url_sai_hinh_dang_thanh_FAILED_dau_vao_sai():
    with pytest.raises(nut_http.LoiHttp) as loi:
        nut_http.thuc_thi({"cach": "GET", "url": "khong-phai-url"})
    assert loi.value.ma == "dau_vao_sai"


def test_moi_ma_loi_khai_ra_deu_nam_trong_MA_LOI_HTTP():
    """Banh coc: mot ma loi khong khai la mot FAILED Canvas khong hien duoc."""
    assert "dau_vao_sai" in nut_http.MA_LOI_HTTP
    assert "bi_chan_ssrf" in nut_http.MA_LOI_HTTP
    assert "ma_trang_thai_loi" in nut_http.MA_LOI_HTTP
    assert "phan_hoi_qua_lon" in nut_http.MA_LOI_HTTP


# -- 5. Tran kich thuoc phan hoi ---------------------------------------------

def test_phan_hoi_qua_lon_bi_cat_thanh_FAILED(may_chu):
    """3 MB > tran. Mot dich thu dich khong duoc nhet day bo nho worker."""
    with pytest.raises(nut_http.LoiHttp) as loi:
        _chay({"cach": "GET", "url": _url(may_chu, "/that-to")})
    assert loi.value.ma == "phan_hoi_qua_lon"


# -- 6. Chuyen huong: MAC DINH KHONG theo ------------------------------------

def test_mac_dinh_KHONG_theo_chuyen_huong(may_chu):
    """Theo chuyen huong la gui LAI header cua nguoi soan toi mot host do
    DICH kia chon. Mac dinh phai tra ve 302, khong phai di tiep."""
    ra = _chay({"cach": "GET", "url": _url(may_chu, "/chuyen-huong"),
                "headers": {"Authorization": "Bearer bi-mat"}})
    assert ra["trang_thai"] == 302
    duong_da_di = [x["duong"] for x in may_chu.da_nhan]
    assert "/dich-chuyen-huong" not in duong_da_di
    assert all(x["uy_quyen"] in ("", "Bearer bi-mat")
               for x in may_chu.da_nhan)


def test_bat_theo_chuyen_huong_thi_di_tiep_VA_van_qua_bo_gac(may_chu):
    """Doi chung cho phep tren: bat co len thi no di that."""
    ra = _chay({"cach": "GET", "url": _url(may_chu, "/chuyen-huong"),
                "theo_chuyen_huong": True})
    assert ra["trang_thai"] == 200
    assert ra["than"] == {"toi": "dich"}


# -- 7. Than phan hoi khong phai JSON --------------------------------------

def test_than_khong_phai_JSON_tra_ve_chuoi_chu_khong_FAILED(may_chu):
    """Mot API tra HTML khong phai mot loi cua nguoi soan workflow."""
    ra = _chay({"cach": "GET", "url": _url(may_chu, "/khong-phai-json")})
    assert ra["trang_thai"] == 200
    assert ra["than"] == "<html>xin chao</html>"
