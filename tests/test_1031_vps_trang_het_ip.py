"""R24 (17/09/2026): trang /vps va luc tao may phai dung CUNG mot phep tinh con cho.

Do tren production sau khi chu du an tam dung ban VPS (tat tu mua IP OVH): IPv4
con ban = 0, nhung trang van bat nut "Tao may" cho moi goi vi `trang_chinh` chi
hoi RAM/dia. Khach chon goi, dien ten, bam tao — roi moi an "Da het cho".
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.vps import profiles, routes
from apps.vps.services import capacity

DU_RAM_DIA = capacity.SucChua(ram_mb_tong=256_000, dia_gb_tong=4_000, cpu_tong=64)


def _goi_tren_trang(monkeypatch, gioi_han):
    monkeypatch.setattr(routes, "_chu", lambda request: "khach-1")
    monkeypatch.setattr(routes, "_suc_chua", lambda db, profile=None: (DU_RAM_DIA, ""))
    monkeypatch.setattr(routes, "_gioi_han_ban", lambda db: gioi_han, raising=False)
    monkeypatch.setattr(routes, "_may_cua_toi", lambda db, user_id: [])
    monkeypatch.setattr(routes, "_thong_ke", lambda ds: {})
    monkeypatch.setattr(routes, "_menu", lambda *a, **k: [])
    monkeypatch.setattr(routes, "issue_csrf_token", lambda request: "csrf")
    monkeypatch.setattr(routes.provisioning, "vung_dang_mo", lambda db: [("sgp", "SG")])
    monkeypatch.setattr(routes.ten_may, "tu_sinh", lambda db, user_id: "vps-01")
    monkeypatch.setattr(routes.templates, "TemplateResponse",
                        lambda request, name, ctx: ctx)
    request = SimpleNamespace(query_params={})
    ctx = routes.trang_chinh(request=request, _g=None, _u="khach-1", _a=None, db=None)
    return {g["plan"].id: g["con_cho"] for g in ctx["goi"]}


def test_het_IPv4_thi_KHONG_goi_nao_con_cho_du_RAM_dia_con_nhieu(monkeypatch):
    con_cho = _goi_tren_trang(monkeypatch, gioi_han=(0, 50))
    assert con_cho and not any(con_cho.values()), con_cho


def test_het_cong_vao_thi_KHONG_goi_nao_con_cho(monkeypatch):
    con_cho = _goi_tren_trang(monkeypatch, gioi_han=(50, 0))
    assert con_cho and not any(con_cho.values()), con_cho


def test_khong_doc_duoc_gioi_han_thi_dong_ban(monkeypatch):
    con_cho = _goi_tren_trang(monkeypatch, gioi_han=None)
    assert con_cho and not any(con_cho.values()), con_cho


def test_con_IP_va_cong_thi_goi_vua_RAM_dia_van_ban_duoc(monkeypatch):
    """Doi chung: phep kiem tren khong xanh vi trang dong ban vo dieu kien."""
    con_cho = _goi_tren_trang(monkeypatch, gioi_han=(50, 50))
    assert any(con_cho.values()), con_cho


def test_khong_co_vung_mo_hoac_profile_chua_san_sang_thi_khong_co_gioi_han(monkeypatch):
    monkeypatch.setattr(routes.provisioning, "vung_dang_mo", lambda db: [])
    assert routes._gioi_han_ban(None) is None

    def chua_san_sang(db, *, region):
        raise profiles.ProfileNotReady("stale health")

    monkeypatch.setattr(routes.provisioning, "vung_dang_mo", lambda db: [("sgp", "SG")])
    monkeypatch.setattr(routes.profiles, "select_profile", chua_san_sang)
    assert routes._gioi_han_ban(None) is None


@pytest.mark.parametrize("gioi_han, ky_vong", [((0, 9), 0), ((9, 0), 0), ((3, 9), 3)])
def test_so_cho_lay_gia_tri_nho_nhat_cua_IP_cong_va_tinh_toan(gioi_han, ky_vong):
    so = routes._so_cho_ban(DU_RAM_DIA, "vps-nho", gioi_han)
    assert so == ky_vong
