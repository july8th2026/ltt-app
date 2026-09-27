"""UI-0 Task 2 — canh roi mot cong CONTROL phai mang kind + ten nhanh.

`frontend/agent-canvas/src/workflowApi.ts::edgeToV3()` dong cung `kind:'DATA'`
va KHONG gui `condition`. Dong co (`dong_co.py::_kich_hoat`) xu:

    dk = str(e.get("condition") or "")
    if not dk:
        return True          # <- khong co condition => LUON kich hoat

=> ca hai nhanh cua `core.if` deu chay. Nguoi dung ve mot re nhanh va nhan mot
PHAN DOI — tren tien that, vi nhanh le ra khong chay van sinh job va but toan.
Do tren trinh duyet 27/09/2026: hai canh roi `core.if` co class giong het nhau
va `edgeLabels: [null, null]`.

## ⭐ Vi sao suy o MAY CHU chu khong gui tu client

May chu SO HUU luat: no biet `core.if` khai hai cong ra kieu `control` ten
`true`/`false`. Client khong co bang kieu cong, va mot ban cai dat thu hai thi
lech im lang — dung bai hoc cua `he_kieu.xuat_luat_noi_day()`.
Suy o may chu con co nghia moi ban nhap dang nam tren production tu dung, khong
can mot buoc di tru nao.

## 🔴 CHI suy khi node nguon co >= 2 cong ra kieu control

Do bang `nut_loi.tat_ca()` ngay 27/09:

    core.if      cong_ra = [('true','control'), ('false','control')]   2 cong
    core.switch  cong_ra = [('nhanh','control')]                       1 cong

Ten cac nhanh cua `core.switch` nam trong THAM SO `nhanh: array`, khong phai
ten cong. Suy `condition='nhanh'` cho no thi dong co so
`_nhanh_da_chon(...) == "nhanh"` — ham do tra GIA TRI nhanh that ('a','b') —
nen khong bao gio khop, va MOI nhanh cua switch chet. Hom nay switch chay ca
cac nhanh (sai nhung chay); mot ban suy bua bien no thanh KHONG CHAY GI, te hon
hien trang. `test_core_switch_KHONG_bi_suy_bua` giu dung cho nay.

⚠️ Khoang trong con lai: `core.switch` van chay moi nhanh. Sua no can mot cua
giao dien dat ten nhanh len canh — thuoc UI-4, khong thuoc pha nay.
"""
from __future__ import annotations

from platform_core.workflow import bien_dich


def _node(nid: str, tool: str, params: dict, x: int = 0, y: int = 0) -> dict:
    """Hinh dang `editorState.nextNode()` sinh."""
    return {"id": nid, "type": "tool", "position": {"x": x, "y": y},
            "data": {"tool": tool, "params": params}}


def _trang(nodes: list, edges: list) -> dict:
    return {"version": 3, "goal": "", "active_page_id": "p1",
            "pages": [{"id": "p1", "name": "Page 1",
                       "nodes": nodes, "edges": edges}]}


def _tai_lieu_if() -> dict:
    """core.if --true--> core.set ; core.if --false--> core.stop."""
    return _trang(
        [_node("n-if", "core.if", {"dieu_kien": "1 == 1"}),
         _node("n-set", "core.set", {"bien": {}}, x=300),
         _node("n-stop", "core.stop", {}, x=300, y=200)],
        [{"id": "e1", "source_node": "n-if", "target_node": "n-set",
          "source_port": "true", "target_port": "in", "kind": "DATA"},
         {"id": "e2", "source_node": "n-if", "target_node": "n-stop",
          "source_port": "false", "target_port": "in", "kind": "DATA"}])


def test_canh_tu_cong_control_mang_kind_va_ten_nhanh():
    ct = bien_dich.cau_truc(_tai_lieu_if())
    theo_id = {e["id"]: e for e in ct.edges}
    assert theo_id["e1"]["kind"] == "CONTROL"
    assert theo_id["e1"]["condition"] == "true"
    assert theo_id["e2"]["kind"] == "CONTROL"
    assert theo_id["e2"]["condition"] == "false"


def test_canh_du_lieu_thuong_khong_bi_doi():
    """Canh roi mot cong DU LIEU phai giu DATA va condition rong."""
    ct = bien_dich.cau_truc(_trang(
        [_node("a", "image.generate", {"prompt": "x"}),
         _node("b", "core.set", {"bien": {}}, x=300)],
        [{"id": "e", "source_node": "a", "target_node": "b",
          "source_port": "image_keys", "target_port": "in", "kind": "DATA"}]))
    assert ct.edges[0]["kind"] == "DATA"
    assert ct.edges[0]["condition"] == ""


def test_core_switch_KHONG_bi_suy_bua():
    """🔴 Hoi quy: `core.switch` co DUNG MOT cong control ten chung `nhanh`.

    Suy `condition='nhanh'` se lam MOI nhanh cua switch chet. Canh cua switch
    phai di qua NGUYEN VEN (condition rong => dong co van kich hoat nhu hom
    nay), cho toi khi UI-4 co cua dat ten nhanh that.
    """
    ct = bien_dich.cau_truc(_trang(
        [_node("n-sw", "core.switch", {"bieu_thuc": "1", "nhanh": ["a", "b"]}),
         _node("n-set", "core.set", {"bien": {}}, x=300)],
        [{"id": "e", "source_node": "n-sw", "target_node": "n-set",
          "source_port": "nhanh", "target_port": "in", "kind": "DATA"}]))
    assert ct.edges[0]["condition"] == "", "da suy bua cho core.switch"


def test_tai_lieu_KHAI_TUONG_MINH_thi_giu_nguyen_khong_suy():
    """Tai lieu da khai `condition`/`kind` thi may chu KHONG duoc ghi de."""
    doc = _tai_lieu_if()
    doc["pages"][0]["edges"][0]["kind"] = "ERROR"
    doc["pages"][0]["edges"][0]["condition"] = "tu_khai"
    ct = bien_dich.cau_truc(doc)
    theo_id = {e["id"]: e for e in ct.edges}
    assert theo_id["e1"]["kind"] == "ERROR"
    assert theo_id["e1"]["condition"] == "tu_khai"
