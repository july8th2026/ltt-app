"""R24 (17/09/2026): trang /vps va luc tao may phai dung CUNG mot phep tinh con cho.

Do tren production sau khi chu du an tam dung ban VPS (tat tu mua IP OVH): IPv4
con ban = 0, nhung trang van bat nut "Tao may" cho moi goi vi `trang_chinh` chi
hoi RAM/dia. Khach chon goi, dien ten, bam tao — roi moi an "Da het cho".

⭐ 23/09/2026: "cung mot phep tinh" khong con la mot giao uoc giua ba noi tu tinh
   lay nua — no la `apps/vps/services/nguon_luc.py`, va `routes` / `preflight`
   deu goi no. Cac phep duoi day nham vao `nguon_luc` thay vi vao bon ham rieng
   cu (`_suc_chua`, `_gioi_han_ban`, `_gioi_han_ip_va_cong`, `_so_cho_ban`) da
   bi go khoi `routes`. Tinh chat duoc chot KHONG doi; chi cai dich ngam doi.

   `test_phep_tinh_con_cho_khong_con_ban_sao_nao_trong_routes` la banh coc: no
   doc AST cua `routes.py` va doi rang khong ai dung lai mot phep tinh thu hai.
"""
from __future__ import annotations

import ast
import inspect
import pathlib
from types import SimpleNamespace

import pytest

from apps.vps import routes
from apps.vps.services import capacity, nguon_luc

DU_RAM_DIA = capacity.SucChua(ram_mb_tong=256_000, dia_gb_tong=4_000, cpu_tong=64)

#: Bang thong khong duoc chan trong cac phep duoi day: chung do IP va cong vao.
#: Viet cung mot con so ngan sach o day la buoc cac phep nay phu thuoc bang gia.
BANG_THONG_THOAI_MAI = 1_000_000


def _do(free_ipv4, gateway_slots, suc_chua=DU_RAM_DIA) -> nguon_luc.DoDuoc:
    return nguon_luc.DoDuoc(
        suc_chua=suc_chua, free_ipv4=free_ipv4, gateway_slots=gateway_slots,
        da_hua_bang_thong_gb=0, ngan_sach_bang_thong_gb=BANG_THONG_THOAI_MAI)


def _goi_tren_trang(monkeypatch, do: nguon_luc.DoDuoc):
    monkeypatch.setattr(routes, "_chu", lambda request: "khach-1")
    monkeypatch.setattr(routes.nguon_luc, "do_nguon_luc",
                        lambda db, profile=None: do)
    monkeypatch.setattr(routes, "_may_cua_toi", lambda db, user_id: [])
    monkeypatch.setattr(routes, "_thong_ke", lambda ds: {})
    monkeypatch.setattr(routes, "_menu", lambda *a, **k: [])
    monkeypatch.setattr(routes, "issue_csrf_token", lambda request: "csrf")
    monkeypatch.setattr(routes.provisioning, "vung_dang_mo", lambda db: [("sgp", "SG")])
    # Seam moi (23/09): trang noi truoc thoi gian cho. No doc `vps_event`, ma
    # cac phep o day chay voi `db=None` — chung do CHO BAN, khong do thoi gian.
    monkeypatch.setattr(routes.provisioning, "thoi_gian_san_sang",
                        lambda db, **k: None)
    monkeypatch.setattr(routes, "_canh_bao_chat_luong", lambda db: False)
    monkeypatch.setattr(routes.ten_may, "tu_sinh", lambda db, user_id: "vps-01")
    monkeypatch.setattr(routes.templates, "TemplateResponse",
                        lambda request, name, ctx: ctx)
    request = SimpleNamespace(query_params={})
    ctx = routes.trang_chinh(request=request, _g=None, _u="khach-1", _a=None, db=None)
    return ctx


def _con_cho(monkeypatch, do):
    ctx = _goi_tren_trang(monkeypatch, do)
    return {g["plan"].id: g["con_cho"] for g in ctx["goi"]}


def test_het_IPv4_thi_KHONG_goi_nao_con_cho_du_RAM_dia_con_nhieu(monkeypatch):
    con_cho = _con_cho(monkeypatch, _do(0, 50))
    assert con_cho and not any(con_cho.values()), con_cho


def test_het_cong_vao_thi_KHONG_goi_nao_con_cho(monkeypatch):
    con_cho = _con_cho(monkeypatch, _do(50, 0))
    assert con_cho and not any(con_cho.values()), con_cho


def test_khong_doc_duoc_gioi_han_thi_dong_ban(monkeypatch):
    con_cho = _con_cho(monkeypatch, _do(None, None))
    assert con_cho and not any(con_cho.values()), con_cho


def test_con_IP_va_cong_thi_goi_vua_RAM_dia_van_ban_duoc(monkeypatch):
    """Doi chung: phep kiem tren khong xanh vi trang dong ban vo dieu kien."""
    con_cho = _con_cho(monkeypatch, _do(50, 50))
    assert any(con_cho.values()), con_cho


def test_khong_co_vung_mo_hoac_profile_chua_san_sang_thi_khong_do_duoc(monkeypatch):
    from apps.vps import profiles

    monkeypatch.setattr(nguon_luc, "_gioi_han_ip_va_cong",
                        lambda db, profile: (9, 9))
    monkeypatch.setattr("apps.vps.services.provisioning.vung_dang_mo",
                        lambda db: [])
    assert nguon_luc.do_nguon_luc(None).free_ipv4 is None

    def chua_san_sang(db, *, region):
        raise profiles.ProfileNotReady("stale health")

    monkeypatch.setattr("apps.vps.services.provisioning.vung_dang_mo",
                        lambda db: [("sgp", "SG")])
    monkeypatch.setattr(profiles, "select_profile", chua_san_sang)
    assert nguon_luc.do_nguon_luc(None).suc_chua is None


# ── suc khoe do KHONG duoc noi thanh "het cho" (su co 23/09) ─────────────────

def test_profile_chua_san_sang_thi_cau_cho_khach_la_bao_tri_chu_khong_phai_het_cho(
        monkeypatch):
    """🔴 Chinh ca 23/09: ca ba goi in "Het cho" trong khi con 14/9/6 cho."""
    ctx = _goi_tren_trang(monkeypatch, _do(None, None))
    for g in ctx["goi"]:
        assert g["rang_buoc"] == nguon_luc.RANG_BUOC_SUC_KHOE
        assert "hết chỗ" not in g["cau_het"].lower()


def test_het_compute_van_noi_het_cho_vi_do_moi_that_su_la_het_cho(monkeypatch):
    het = capacity.SucChua(ram_mb_tong=1024, dia_gb_tong=10, cpu_tong=1)
    ctx = _goi_tren_trang(monkeypatch, _do(50, 50, suc_chua=het))
    assert all(g["rang_buoc"] == nguon_luc.RANG_BUOC_COMPUTE for g in ctx["goi"])


@pytest.mark.parametrize("gioi_han, ky_vong", [((0, 9), 0), ((9, 0), 0), ((3, 9), 3)])
def test_so_cho_lay_gia_tri_nho_nhat_cua_IP_cong_va_tinh_toan(gioi_han, ky_vong):
    free_ipv4, cong = gioi_han
    assert nguon_luc.danh_gia(_do(free_ipv4, cong), "vps-nho").so_cho == ky_vong


# ── banh coc: mot phep tinh, khong phai mot giao uoc ────────────────────────

def test_phep_tinh_con_cho_khong_con_ban_sao_nao_trong_routes():
    """`routes` khong duoc tu tinh con cho — no PHAI hoi `nguon_luc`.

    Ba noi tung tu tinh lay va DA lech nhau that: `preflight` goi
    `effective_ipv4_slots` khong tru `promised_without_ip` trong khi `routes`
    thi co, nen thanh phan `capacity` bao xanh luc trang hien 0 cho. Mot giao
    uoc khong ai kiem duoc thi se lech lai; phep nay kiem no bang co hoc.
    """
    cay = ast.parse(pathlib.Path(inspect.getfile(routes)).read_text(encoding="utf-8"))
    goi = {n.func.id if isinstance(n.func, ast.Name) else
           getattr(n.func, "attr", "")
           for n in ast.walk(cay) if isinstance(n, ast.Call)}
    for cam in ("sellable_slots", "effective_ipv4_slots",
                "available_gateway_slots", "cho_phep_ban", "suc_chua_hien_tai"):
        assert cam not in goi, (
            f"routes.py goi thang {cam!r} — phep tinh con cho phai di qua "
            f"nguon_luc, neu khong ba noi se lech nhau lan nua")
