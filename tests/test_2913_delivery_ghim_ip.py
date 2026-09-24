"""`platform_core/public_api/delivery.py` phai GHIM IP - plan wf-v2 P5b/T1.

VAN DE (TOCTOU / DNS rebinding)

   Ban truoc 24/09/2026 cua `send_delivery` lam hai viec roi rac:

       webhooks.validate_target(url, resolver=...)   # phan giai LAN 1 de KIEM
       opener.open(request)                          # phan giai LAN 2 de NOI

   Giua hai lan do DNS doi duoc. Ke tan cong dieu khien ban ghi cua chinh
   ten minh chi can tra dia chi cong cong cho lan mot va `127.0.0.1` cho lan
   hai: bo gac phe duyet mot dia chi, socket di toi MOT DIA CHI KHAC - dia
   chi chua he duoc kiem. Day dung la khuon TOCTOU.

   Cach vay duy nhat la GHIM IP: phan giai MOT lan, kiem MOI dia chi tra ve,
   roi noi toi DUNG dia chi da kiem. Loi ghim da duoc port vao
   `platform_core/http_an_toan.py` (P5/T2) - o day ta DUNG LAI no, khong
   viet bo kiem thu hai.

DOI CHUNG (vi sao cac phep duoi day khong xanh vi khong do gi)

   * `test_doi_chung_...` chung minh may chu gia co that, `send_delivery`
     that su mo ket noi toi no, va byte di tren day dung la cua
     `delivery.py` (USER_AGENT + header chu ky cua webhook).
   * Phep chinh KHONG assert "khong nhan duoc gi" - no assert MOI host ma
     tang socket duoc dua deu la mot DIA CHI DA QUA BO GAC. Tren ma cu,
     host do la mot TEN MIEN (`ip_address()` nem ValueError) => do.
"""
from __future__ import annotations

import http.server
import ipaddress
import socket
import threading
import types

import pytest

import platform_core.an_toan_mang as an_toan_mang
from platform_core.public_api import delivery as delivery_mod
from platform_core.public_api import webhooks

#: Ten mien cua "nguoi nhan". KHONG bao gio duoc dua cho tang socket.
TEN = "ten-doi-ip.test"
#: Dia chi cong cong ma bo gac phe duyet (TRA LOI DNS LAN MOT).
DIA_CHI_TOT = "93.184.216.34"
#: Dia chi ke tan cong nham toi (TRA LOI DNS LAN HAI).
DIA_CHI_XAU = "127.0.0.1"

BI_MAT = "s" * 40


class _Tay(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _tra(self, ma: int, than: bytes, them: dict | None = None) -> None:
        self.send_response(ma)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(than)))
        for k, v in (them or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(than)

    def do_POST(self):  # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        self.server.da_nhan.append({
            "duong": self.path,
            "host": self.headers.get("Host", ""),
            "than": self.rfile.read(n),
            "user_agent": self.headers.get("User-Agent", ""),
            "chu_ky": self.headers.get(webhooks.SIGNATURE_HEADER, ""),
            "su_kien": self.headers.get(webhooks.EVENT_HEADER, ""),
        })
        if self.path == "/chuyen-huong":
            self._tra(302, b"{}",
                      {"Location": "http://noi-bo-cua-ke-tan-cong.test/x"})
            return
        self._tra(200, b'{"ok":true}')

    def log_message(self, *a):  # im lang
        return


@pytest.fixture()
def may_chu():
    """May chu gia tren 127.0.0.1, cong EPHEMERAL (0). KHONG bao gio 8100."""
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Tay)
    srv.da_nhan = []
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()


@pytest.fixture()
def dang_ky(monkeypatch, may_chu):
    """(subscription, delivery) toi thieu - khong CSDL, khong cau hinh that."""
    from platform_core import secretbox

    monkeypatch.setattr(secretbox, "giai_ma", lambda _blob: BI_MAT)
    cong = may_chu.server_address[1]
    sub = types.SimpleNamespace(url="http://%s:%d/hook" % (TEN, cong),
                                secret_enc="khong-dung-den", enabled=True)
    dl = types.SimpleNamespace(event_id="e" * 32, payload={"id": "e" * 32},
                               event_type=webhooks.EVENT_JOB_SUCCEEDED)
    return sub, dl


def _cai_dns(monkeypatch, ho_so_os, lan_hai):
    """`socket.getaddrinfo` gia - dung cho CA urllib LAN httpx.

    `socket.create_connection` (ca `http.client` lan `httpcore` deu dung)
    tra cuu `getaddrinfo` nhu bien toan cuc cua mo-dun `socket`, nen mot lan
    va o day bat duoc ca hai duong.

    Ban thu nghiem noi doi MOT dieu co chu y: no tra ve loopback cho MOI
    host, ke ca `93.184.216.34`. Tuc may chu gia DONG VAI nguoi nhan cong
    cong - nho the phep kiem khong he gui mot goi nao ra Internet, va van
    phan biet duoc "tang socket da duoc dua cai gi".
    """
    that = socket.getaddrinfo

    def _gia(host, port, family=0, type=0, proto=0, flags=0):  # noqa: A002
        ho_so_os.append(host)
        try:
            ipaddress.ip_address(host)
        except ValueError:
            # Mot TEN duoc dua cho he dieu hanh => DNS tra loi LAN HAI, va
            # day dung la cho ke tan cong doi cau tra loi.
            lan_hai.append(DIA_CHI_XAU)
        return that("127.0.0.1", port, family, type, proto, flags)

    monkeypatch.setattr(socket, "getaddrinfo", _gia)


# -- 1. Doi chung -------------------------------------------------------------

def test_doi_chung_send_delivery_that_su_gui_byte_cua_webhook(monkeypatch,
                                                              may_chu, dang_ky):
    """Neu phep nay do, moi phep an toan duoi day khong do gi ca.

    Bo gac bi vo hieu CO CHU Y **chi trong phep nay**: dieu can chung minh o
    day la duong ong - `send_delivery` mo ket noi that va gui dung byte cua
    `delivery.py`, khong phai la no chan dung.
    """
    _cai_dns(monkeypatch, [], [])
    monkeypatch.setattr(an_toan_mang, "kiem_dia_chi", lambda *a, **k: None)
    sub, dl = dang_ky
    ma = delivery_mod.send_delivery(sub, dl, require_https=False,
                                    resolver=lambda h: [DIA_CHI_XAU])
    assert ma == 200
    assert may_chu.da_nhan, "khong he gui gi - moi phep duoi day vo nghia"
    nhan = may_chu.da_nhan[-1]
    assert nhan["user_agent"] == delivery_mod.USER_AGENT
    assert nhan["chu_ky"].startswith(webhooks.SIGNATURE_VERSION + "=")
    assert nhan["su_kien"] == dl.event_id
    assert nhan["than"] == webhooks.canonical_body(dl.payload)


# -- 2. TOCTOU: moi dia chi socket nhan phai la dia chi DA KIEM ---------------

def test_ten_mien_khong_bao_gio_den_tang_socket(monkeypatch, may_chu, dang_ky):
    """Phep tai hien DNS rebinding.

    Bo phan giai tra `93.184.216.34` cho lan hoi THU NHAT (bo gac phe duyet)
    va `127.0.0.1` cho lan THU HAI. Tren ma cu, lan thu hai do he dieu hanh
    hoi khi mo ket noi - va ket noi di toi mot dia chi CHUA HE duoc kiem.

    Assert khong phai "khong nhan duoc gi" (phep do se xanh ca khi test noi
    day sai) ma la: MOI host tang socket duoc dua deu phai la mot DIA CHI
    DA QUA BO GAC. Tren ma cu, host do la mot TEN MIEN.
    """
    ho_so_os: list[str] = []
    lan_hai: list[str] = []
    _cai_dns(monkeypatch, ho_so_os, lan_hai)

    dem = {"n": 0}

    def _phan_giai(host):
        dem["n"] += 1
        return [DIA_CHI_TOT] if dem["n"] == 1 else [DIA_CHI_XAU]

    sub, dl = dang_ky
    ma = delivery_mod.send_delivery(sub, dl, require_https=False,
                                    resolver=_phan_giai)

    # Doi chung: ket noi THAT su da xay ra (nguoi nhan cong cong dong vai).
    assert ma == 200
    assert may_chu.da_nhan, "khong he gui gi"
    assert may_chu.da_nhan[-1]["host"].startswith(TEN + ":"), \
        "Host header phai giu TEN goc, neu khong virtual host va TLS deu hong"

    # PHEP DO. Moi thu tang socket nhan deu phai la dia chi da qua bo gac.
    assert ho_so_os, "socket khong he phan giai gi - phep nay khong do gi"
    for host in ho_so_os:
        dia = ipaddress.ip_address(host)   # ValueError => mot TEN da lot qua
        assert str(dia) == DIA_CHI_TOT, ho_so_os
    assert TEN not in ho_so_os, ho_so_os
    assert lan_hai == [], "DNS bi hoi LAN HAI - cua so rebinding con nguyen"
    assert dem["n"] == 1, "bo gac phan giai %d lan" % dem["n"]


# -- 3. Redirect: moi hop van phai qua bo gac --------------------------------

def test_redirect_toi_dia_chi_noi_bo_van_bi_chan(monkeypatch, may_chu, dang_ky):
    """Hop mot di toi nguoi nhan, hop hai tro ve mot ten noi bo => chan."""
    ho_so_os: list[str] = []
    _cai_dns(monkeypatch, ho_so_os, [])

    def _phan_giai(host):
        return [DIA_CHI_TOT] if host == TEN else [DIA_CHI_XAU]

    sub, dl = dang_ky
    sub.url = sub.url.replace("/hook", "/chuyen-huong")
    with pytest.raises(Exception) as loi:
        delivery_mod.send_delivery(sub, dl, require_https=False,
                                   resolver=_phan_giai)
    assert "not allowed" in str(getattr(loi.value, "detail", loi.value)).lower()
    # Doi chung: hop MOT that su da xay ra, nen phep nay do dung hop HAI.
    assert may_chu.da_nhan[-1]["duong"] == "/chuyen-huong"
