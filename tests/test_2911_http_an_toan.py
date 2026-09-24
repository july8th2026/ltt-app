"""Client HTTP an toan (`platform_core/http_an_toan.py`) - plan wf-v2 P5/T2.

PORT tu `langchain_core/_security/_transport.py`, repo langchain-ai/langchain,
commit 7622d3dce760ac4be6d9aef4c653277e06064aea. Thu DANG lay la loi **ghim
IP** (`pinned_url = request.url.copy_with(host=pinned_ip)` + giu `Host` va
`sni_hostname`), khong phai danh sach mang cua ho - vi tu van la
`an_toan_mang` (P5/T1).

VI SAO GHIM IP, khong chi "kiem roi goi"

   `platform_core/public_api/delivery.py` hom nay kiem URL roi giao cho
   urllib goi. Giua hai buoc do co **hai lan phan giai DNS**: mot lan de
   kiem, mot lan khi noi. Ke tan cong dieu khien duoc DNS tra ve dia chi
   cong cong cho lan dau va 127.0.0.1 cho lan sau (DNS rebinding, ca
   TOCTOU kinh dien). Ghim IP xoa han cua so do: chi con MOT lan phan
   giai, va dia chi duoc noi toi la dung dia chi da qua bo gac.

DOI CHUNG

   `test_doi_chung_may_chu_gia_that_su_tra_loi` chung minh may chu gia
   cuc bo co that va client co that su goi toi. Neu khong co no, moi phep
   "bi chan" duoi day xanh ca khi client khong he gui gi.
"""
from __future__ import annotations

import http.server
import threading

import pytest

import platform_core.an_toan_mang as an_toan_mang
import platform_core.http_an_toan as http_an_toan


class _Tay(http.server.BaseHTTPRequestHandler):
    """Ghi lai Host header va tra mot than JSON nho."""

    protocol_version = "HTTP/1.1"

    def _tra(self, ma: int, than: bytes, them: dict | None = None) -> None:
        self.send_response(ma)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(than)))
        for k, v in (them or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(than)

    def do_GET(self):  # noqa: N802
        self.server.da_nhan.append({
            "duong": self.path, "host": self.headers.get("Host", ""),
            "than": b"",
            "cookie": self.headers.get("Cookie", ""),
            "uy_quyen": self.headers.get("Authorization", ""),
            "tat_ca": {k.lower() for k in self.headers.keys()}})
        if self.path == "/chuyen-huong-noi-bo":
            # 302 toi metadata dam may -> hop thu HAI phai bi tu choi,
            # KE CA duoi chinh sach tha `cho_phep_noi_bo=True`.
            self._tra(302, b"{}",
                      {"Location": "https://metadata.dam-may.vidu/bi-mat"})
            return
        if self.path == "/loi-500":
            self._tra(500, b'{"loi":"vo"}')
            return
        self._tra(200, b'{"ok":true}')

    def do_POST(self):  # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        than = self.rfile.read(n)
        self.server.da_nhan.append({"duong": self.path,
                                    "host": self.headers.get("Host", ""),
                                    "than": than,
                                    "kieu": self.headers.get("Content-Type", ""),
                                    "rieng": self.headers.get("X-Rieng", "")})
        self._tra(200, b'{"ok":true}')

    def log_message(self, *a):  # im lang trong test
        return


@pytest.fixture()
def may_chu():
    """May chu HTTP gia tren 127.0.0.1, cong EPHEMERAL.

    Cong 0 -> he dieu hanh cap. KHONG bao gio 8100: do la production.
    """
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Tay)
    srv.da_nhan = []
    luong = threading.Thread(target=srv.serve_forever, daemon=True)
    luong.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()


def _dia_chi(srv) -> str:
    return f"http://may-chu-gia.test:{srv.server_address[1]}"


def _phan_giai_ve_may_chu(host):
    return ["127.0.0.1"]


# -- 1. Doi chung: may chu gia that su tra loi --------------------------------

def test_doi_chung_may_chu_gia_that_su_tra_loi(may_chu):
    """Neu phep nay do, moi phep 'bi chan' duoi day khong do gi ca."""
    with http_an_toan.tao_client(chinh_sach=an_toan_mang.CHINH_SACH_NOI_BO,
                                 bo_phan_giai=_phan_giai_ve_may_chu) as c:
        r = c.get(_dia_chi(may_chu) + "/xin-chao")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert may_chu.da_nhan[-1]["duong"] == "/xin-chao"


# -- 2. Ghim IP: giu Host va SNI --------------------------------------------

def test_ghim_IP_van_giu_nguyen_Host_header(may_chu):
    """Noi toi IP da qua bo gac, nhung may chu van thay ten that.

    Neu khong giu `Host`, moi virtual host va moi chung chi TLS deu hong -
    tuc loi ghim IP se khong dung duoc that.
    """
    with http_an_toan.tao_client(chinh_sach=an_toan_mang.CHINH_SACH_NOI_BO,
                                 bo_phan_giai=_phan_giai_ve_may_chu) as c:
        assert c.get(_dia_chi(may_chu) + "/a").status_code == 200
    host = may_chu.da_nhan[-1]["host"]
    assert host.startswith("may-chu-gia.test:"), host
    assert "127.0.0.1" not in host


def test_chi_phan_giai_DNS_DUNG_MOT_LAN(may_chu):
    """Cua so TOCTOU bi dong: goi lan hai la mot lan phan giai khac, nhung
    TRONG mot request chi co dung mot lan hoi DNS."""
    dem = {"n": 0}

    def _dem(host):
        dem["n"] += 1
        return ["127.0.0.1"]

    with http_an_toan.tao_client(chinh_sach=an_toan_mang.CHINH_SACH_NOI_BO,
                                 bo_phan_giai=_dem) as c:
        c.get(_dia_chi(may_chu) + "/a")
    assert dem["n"] == 1, f"phan giai {dem['n']} lan - con cua so rebinding"


# -- 3. Bo gac cam vao that ---------------------------------------------------

def test_chinh_sach_mac_dinh_TU_CHOI_chinh_may_chu_cuc_bo(may_chu):
    """Banh coc: doi chung o phep 1 dung chinh sach tha. Mac dinh phai chan."""
    with http_an_toan.tao_client(bo_phan_giai=_phan_giai_ve_may_chu) as c:
        with pytest.raises(an_toan_mang.LoiChanSSRF):
            c.get(_dia_chi(may_chu) + "/a")
    assert not may_chu.da_nhan, "da gui that toi may chu du bi chan"


@pytest.mark.parametrize("dia_chi", ["10.0.0.7", "100.64.0.1",
                                     "169.254.169.254", "239.255.255.250"])
def test_dia_chi_bi_chan_khong_bao_gio_duoc_noi_toi(dia_chi):
    with http_an_toan.tao_client(bo_phan_giai=lambda h: [dia_chi]) as c:
        with pytest.raises(an_toan_mang.LoiChanSSRF):
            c.get("https://khach-chon.example.com/x")


def test_so_do_khong_phai_https_bi_tu_choi():
    with http_an_toan.tao_client(bo_phan_giai=lambda h: ["93.184.216.34"]) as c:
        with pytest.raises(an_toan_mang.LoiChanSSRF):
            c.get("http://ok.example.com/x")


# -- 4. Redirect: MOI hop deu qua bo gac -------------------------------------

def test_redirect_toi_dia_chi_noi_bo_bi_chan_o_hop_HAI(may_chu):
    """Cai gia tri that cua transport: `follow_redirects` goi lai transport
    cho tung hop, nen hop hai cung phai qua bo gac.

    Hop mot di toi may chu gia (duoc, vi chinh sach tha), hop hai tro ve
    `169.254.169.254` - dia chi metadata, bi chan KE CA duoi chinh sach tha.
    Chon dia chi do co chu y: no chung minh luon rang co "dev" KHONG mo
    duong toi kho thong tin dang nhap cua may ao.
    """
    with http_an_toan.tao_client(chinh_sach=an_toan_mang.CHINH_SACH_NOI_BO,
                                 bo_phan_giai=lambda h: (
                                     ["127.0.0.1"] if h.endswith(".test")
                                     else ["169.254.169.254"])) as c:
        with pytest.raises(an_toan_mang.LoiChanSSRF):
            c.get(_dia_chi(may_chu) + "/chuyen-huong-noi-bo")
    # Doi chung: hop MOT that su da xay ra - nen phep nay do dung hop hai.
    assert may_chu.da_nhan[-1]["duong"] == "/chuyen-huong-noi-bo"


# -- 5. Khong dinh kem thu gi cua nen tang -----------------------------------

def test_khong_gui_cookie_va_khong_gui_thong_tin_dang_nhap(may_chu):
    """Do o PHIA MAY CHU, khong o phia client.

    `assert c.cookies == {}` gan nhu luon dung va khong chung minh duoc gi -
    no do trang thai cua client chu khong do BYTE da di tren day. May chu gia
    ghi lai chinh header no nhan duoc.
    """
    with http_an_toan.tao_client(chinh_sach=an_toan_mang.CHINH_SACH_NOI_BO,
                                 bo_phan_giai=_phan_giai_ve_may_chu) as c:
        c.get(_dia_chi(may_chu) + "/a")
    nhan = may_chu.da_nhan[-1]
    assert nhan["cookie"] == "", nhan["cookie"]
    assert nhan["uy_quyen"] == "", nhan["uy_quyen"]
    # Doi chung: may chu THAT SU doc duoc header - neu khong, hai phep tren
    # xanh vi `_Tay` khong ghi gi ca.
    assert "host" in nhan["tat_ca"] and "user-agent" in nhan["tat_ca"]
