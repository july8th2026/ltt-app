"""Bo gac SSRF dung chung (`platform_core/an_toan_mang.py`) - plan wf-v2 P7/T1.

VI SAO CO TEP NAY

   Truoc 24/09/2026 bo gac SSRF song **duy nhat** trong
   `platform_core/public_api/webhooks.py:145-164`, va do la duong production
   dang chay. Node `core.http` (P7/T3) can dung LAI dung bo gac ay - khong
   duoc viet ban thu hai, vi hai ban se lech nhau va ban lech se la ban co
   lo hong.

   Tep nay do MO-DUN DUNG CHUNG. Phep do rieng cho `webhooks` van o
   `test_185_public_api_webhooks.py` va phai giu nguyen xanh: T1 la mot phep
   RUT RA, khong phai mot thay doi hanh vi.

DOI CHUNG BAT BUOC (memory: "khong doi chung thi so khong khong phai phat hien")

   Mot phep kiem "dia chi X bi tu choi" se XANH ca khi no khong he goi bo gac
   (vd goi nham mot ham luon raise).
   `test_doi_chung_phep_kiem_that_su_di_qua_bo_gac` tiem loi: no THA bo tan
   cung (`cho_phep_noi_bo=True`) va doi hoi CUNG mot dia chi bay gio DI QUA.
   Neu no van bi chan, phep kiem o tren khong do bo gac.
"""
from __future__ import annotations

import ipaddress

import pytest

import platform_core.an_toan_mang as an_toan_mang


def _resolver(dia_chi: str):
    return lambda host: [dia_chi]


# -- 1. Cac dai KHONG dinh tuyen duoc tren Internet cong cong -----------------

#: 10 dai la DIEU KIEN RA cua P7/T4, va CGNAT la bat buoc trong so do.
#:
#: `100.64.0.0/10` (RFC 6598): `ipaddress.ip_address("100.64.0.1").is_private`
#: tra **False** (do 24/09/2026). Mot bo loc liet ke
#: `is_private`/`is_reserved`/`is_loopback`/... cho CGNAT DI QUA. Ha tang VPS
#: cua du an chay NAT qua WireGuard nen dai nay co that tren may.
DAI_BI_CHAN = [
    ("127.0.0.1", "loopback RFC 1122"),
    ("10.0.0.1", "RFC 1918 lop A"),
    ("172.16.0.1", "RFC 1918 lop B"),
    ("192.168.1.1", "RFC 1918 lop C"),
    ("100.64.0.1", "CGNAT RFC 6598 - is_private tra False"),
    ("100.127.255.254", "cuoi dai CGNAT RFC 6598"),
    ("169.254.169.254", "link-local RFC 3927 + metadata dam may"),
    ("0.0.0.0", "'this network' RFC 1122"),
    ("192.0.0.1", "IETF protocol assignments RFC 6890"),
    ("198.18.0.1", "benchmarking RFC 2544"),
    ("203.0.113.5", "TEST-NET-3 RFC 5737"),
    ("224.0.0.1", "multicast RFC 5771"),
    ("::1", "loopback IPv6 RFC 4291"),
    ("fd00::1", "unique-local IPv6 RFC 4193"),
    ("fe80::1", "link-local IPv6 RFC 4291"),
    ("::ffff:127.0.0.1", "IPv4-mapped IPv6 RFC 4291"),
]


@pytest.mark.parametrize("dia_chi,vi_sao",
                         DAI_BI_CHAN, ids=[d for d, _ in DAI_BI_CHAN])
def test_dai_khong_dinh_tuyen_duoc_deu_bi_tu_choi(dia_chi, vi_sao):
    with pytest.raises(an_toan_mang.LoiChanSSRF) as loi:
        an_toan_mang.kiem_url("https://khach-chon.example.com/hook",
                              resolver=_resolver(dia_chi))
    assert loi.value.ma == an_toan_mang.MA_KHONG_CHO_PHEP, vi_sao


def test_du_10_dai_that_su_duoc_do():
    """Banh coc: dieu kien ra cua P7 la **10 dai**. Xoa bot ca do cung xanh."""
    assert len(DAI_BI_CHAN) >= 10
    assert "100.64.0.1" in dict(DAI_BI_CHAN), "CGNAT la dai BAT BUOC"


def test_doi_chung_dia_chi_cong_cong_VAN_qua():
    """Siet qua tay thi moi cuoc goi HTTP that deu hong - phai co chieu nguoc."""
    assert an_toan_mang.kiem_url("https://ok.example.com/x",
                                 resolver=_resolver("93.184.216.34"))


def test_doi_chung_phep_kiem_that_su_di_qua_bo_gac():
    """Tiem loi: tha bo tan cung thi CHINH dia chi do phai DI QUA.

    Neu no van bi chan, `test_dai_khong_dinh_tuyen_duoc_deu_bi_tu_choi` dang
    xanh vi mot ly do khac - khong phai vi bo gac lam viec.
    """
    tha = an_toan_mang.ChinhSach(so_do_cho_phep=frozenset({"http", "https"}),
                                 cho_phep_noi_bo=True)
    assert an_toan_mang.kiem_url("http://localhost:1/x", chinh_sach=tha,
                                 resolver=_resolver("127.0.0.1"))
    # ... trong khi chinh sach mac dinh van chan no.
    with pytest.raises(an_toan_mang.LoiChanSSRF):
        an_toan_mang.kiem_url("https://localhost/x",
                              resolver=_resolver("127.0.0.1"))


def test_MOI_dia_chi_phan_giai_duoc_deu_phai_cong_cong():
    """Mot ten tra ve mot dia chi cong cong + mot rieng tu -> tu choi.

    Client nao noi toi dia chi nao khong phai thu ma cho nay dieu khien.
    """
    with pytest.raises(an_toan_mang.LoiChanSSRF):
        an_toan_mang.kiem_url(
            "https://lap-lung.example.com/x",
            resolver=lambda host: ["93.184.216.34", "127.0.0.1"])


# -- 2. Hinh dang URL --------------------------------------------------------

@pytest.mark.parametrize("url,ma", [
    ("", an_toan_mang.MA_RONG),
    ("   ", an_toan_mang.MA_RONG),
    ("https://" + "a" * 3000 + ".example.com/x", an_toan_mang.MA_QUA_DAI),
    ("ftp://ok.example.com/x", an_toan_mang.MA_SO_DO),
    ("http://ok.example.com/x", an_toan_mang.MA_SO_DO),   # mac dinh https-only
    ("file:///C:/Windows/win.ini", an_toan_mang.MA_SO_DO),
    ("https://user:pw@ok.example.com/x", an_toan_mang.MA_THONG_TIN_DANG_NHAP),
    ("https:///duong-dan", an_toan_mang.MA_KHONG_CO_HOST),
])
def test_url_sai_hinh_dang_bi_tu_choi_dung_ma(url, ma):
    with pytest.raises(an_toan_mang.LoiChanSSRF) as loi:
        an_toan_mang.kiem_url(url, resolver=_resolver("93.184.216.34"))
    assert loi.value.ma == ma


def test_host_khong_phan_giai_duoc():
    def _hong(host):
        raise OSError("nxdomain")

    with pytest.raises(an_toan_mang.LoiChanSSRF) as loi:
        an_toan_mang.kiem_url("https://khong-ton-tai.example.com/x",
                              resolver=_hong)
    assert loi.value.ma == an_toan_mang.MA_KHONG_PHAN_GIAI_DUOC

    with pytest.raises(an_toan_mang.LoiChanSSRF) as rong:
        an_toan_mang.kiem_url("https://rong.example.com/x",
                              resolver=lambda host: [])
    assert rong.value.ma == an_toan_mang.MA_KHONG_PHAN_GIAI_DUOC


def test_dia_chi_IP_thang_khong_can_phan_giai():
    """Literal IP -> dung no, khong hoi DNS (mot ten co the tro cho khac)."""

    def _khong_duoc_goi(host):
        raise AssertionError("literal IP khong duoc di qua DNS")

    assert an_toan_mang.kiem_url("https://93.184.216.34/x",
                                 resolver=_khong_duoc_goi)
    with pytest.raises(an_toan_mang.LoiChanSSRF):
        an_toan_mang.kiem_url("https://100.64.0.1/x", resolver=_khong_duoc_goi)


# -- 3. `webhooks` goi VAO mo-dun nay, khong giu ban sao ----------------------

def test_webhooks_dung_CHUNG_mot_bo_gac(monkeypatch):
    """Banh coc chong "hai ban lech nhau".

    Neu ai do chep lai phep kiem vao `webhooks.py`, phep nay do: thay doi bo
    gac dung chung PHAI doi hanh vi cua `webhooks.validate_target`.
    """
    from platform_core.public_api import webhooks

    goi = []

    def _gia(dia_chi, chinh_sach=None):
        goi.append(str(dia_chi))

    monkeypatch.setattr(an_toan_mang, "kiem_dia_chi", _gia)
    # Bo gac gia cho MOI thu qua -> `validate_target` cung phai cho qua.
    assert webhooks.validate_target("https://x.example.com/hook",
                                    resolver=_resolver("127.0.0.1"))
    assert goi == ["127.0.0.1"], "webhooks khong goi vao bo gac dung chung"


def test_webhooks_system_resolver_van_con_cam_duoc_vao(monkeypatch):
    """Banh coc chong FAIL-OPEN IM LANG do chinh phep rut ra nay tao ra.

    `tests/test_202_webhook_console.py:42` thay `webhooks._system_resolver`
    de ca cum test khong di ra DNS that. Neu `validate_target` truyen
    `resolver=None` xuong `an_toan_mang` thi `an_toan_mang` dung bo phan giai
    CUA NO, lan thay kia thanh vo hieu, va test_202 se xanh trong khi that su
    dang goi DNS that. Phep nay bat dung tinh huong do.
    """
    from platform_core.public_api import webhooks

    monkeypatch.setattr(webhooks, "_system_resolver",
                        lambda host: ["10.0.0.7"])
    with pytest.raises(Exception) as loi:
        webhooks.validate_target("https://bat-ky.example.com/hook")
    assert "not allowed" in str(getattr(loi.value, "detail", loi.value))


def test_ma_loi_khong_ta_mang_noi_bo():
    """Thong bao mot kieu cho moi lop bi chan - khong ve ban do mang."""
    ds = set()
    for dia_chi, _ in DAI_BI_CHAN:
        with pytest.raises(an_toan_mang.LoiChanSSRF) as loi:
            an_toan_mang.kiem_url("https://x.example.com/h",
                                  resolver=_resolver(dia_chi))
        ds.add(str(loi.value))
    assert len(ds) == 1, f"loi ta ra nhieu lop khac nhau: {ds}"


# -- 4. HAI khac biet CO Y so voi ban production truoc 24/09 ------------------
#
# T1 la phep RUT RA, nen moi khac biet phai duoc KHAI RA va do duoc. Ca hai
# deu **chat hon**, khong long hon.

@pytest.mark.parametrize("dia_chi", [
    "239.255.255.250",  # SSDP/UPnP - ban dap SSRF trong mang LAN
    "224.0.0.1",        # all-hosts
    "233.252.0.1",      # MCAST-TEST-NET RFC 5771
    "ff02::1",          # all-nodes link-local IPv6
])
def test_KHAC_BIET_1_multicast_bi_chan_du_is_global_tra_True(dia_chi):
    """`is_global` MOT MINH cho multicast di lot - do tren CPython 3.13.12.

    Docstring `webhooks.py` truoc 24/09 khai `is_global` phu multicast. Phep
    do nay la doi chung cho thay loi khai do SAI, va vi tu moi vá no.
    """
    assert ipaddress.ip_address(dia_chi).is_global is True, \
        "neu CPython doi nghia is_global, ca phep kiem duoi khong con y nghia"
    with pytest.raises(an_toan_mang.LoiChanSSRF):
        an_toan_mang.kiem_url("https://x.example.com/h",
                              resolver=_resolver(dia_chi))


def test_KHAC_BIET_2_NAT64_boc_dia_chi_noi_bo_bi_go_ra():
    """`64:ff9b::/96` (RFC 6052) boc 127.0.0.1 co `is_global == True`.

    Port `_extract_embedded_ipv4` cua `langchain_core/_security/_policy.py`
    (commit 7622d3dce760ac4be6d9aef4c653277e06064aea).
    """
    nat64 = "64:ff9b::7f00:1"
    assert ipaddress.ip_address(nat64).is_global is True
    assert str(an_toan_mang.go_ipv4_long_trong_ipv6(
        ipaddress.ip_address(nat64))) == "127.0.0.1"
    with pytest.raises(an_toan_mang.LoiChanSSRF):
        an_toan_mang.kiem_url("https://x.example.com/h",
                              resolver=_resolver(nat64))
    # Doi chung: NAT64 boc mot dia chi CONG CONG thi VAN qua.
    assert an_toan_mang.kiem_url(
        "https://x.example.com/h", resolver=_resolver("64:ff9b::5db8:d822"))


def test_METADATA_ADDRESSES_giu_nguyen_nhu_production():
    """T1 la phep RUT RA: tap dia chi metadata phai y het ban webhooks cu."""
    from platform_core.public_api import webhooks

    assert an_toan_mang.METADATA_ADDRESSES == webhooks.METADATA_ADDRESSES
    for s in an_toan_mang.METADATA_ADDRESSES:
        ipaddress.ip_address(s)  # phai la dia chi hop le
