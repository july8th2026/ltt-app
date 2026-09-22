"""Compiler draft v3 → ltt.workflow/3 (spec §4.1–4.3)."""
from __future__ import annotations

import pytest

from platform_core.workflow import bien_dich
from platform_core.workflow.cong_cu import CongCu


def _cc(ten, gia=5):
    return CongCu(ten=ten, app_slug="app_" + ten.split(".")[0],
                  job_type=ten + ".job", type_version=2, params_schema={},
                  side_effect="external", idempotency_fields=(),
                  tinh_gia=lambda p, g=gia: g)


CC = {"image.generate": _cc("image.generate"), "text.chat": _cc("text.chat", 1)}


def _doc(pages):
    return {"version": 3, "pages": pages}


def _node(nid, tool, params=None):
    return {"id": nid, "type": "tool", "position": {"x": 0, "y": 0},
            "data": {"tool": tool, "params": params or {}}}


def _canh(eid, a, b, sp="out", tp="in", kind="DATA"):
    return {"id": eid, "source_node": a, "target_node": b,
            "source_port": sp, "target_port": tp, "kind": kind}


def test_gop_moi_trang_va_doi_node_cu_sang_app():
    doc = _doc([
        {"id": "p1", "nodes": [_node("a", "text.chat")], "edges": []},
        {"id": "p2", "nodes": [_node("b", "image.generate")], "edges": []},
    ])
    g = bien_dich.bien_dich(doc, cong_cu=CC)
    assert g["schema"] == "ltt.workflow/3"
    assert {n["id"]: n["type"] for n in g["nodes"]} == {
        "a": "app.text.chat", "b": "app.image.generate"}
    assert all(n["type_version"] == 2 and n["thi_hanh"] == "job"
               for n in g["nodes"])
    assert g["settings"] == {"max_concurrency": 4, "timeout_s": 21600}


def test_tham_chieu_cu_doi_sang_bieu_thuc():
    doc = _doc([{"id": "p1", "nodes": [
        _node("a", "text.chat"),
        _node("b", "image.generate", {"prompt": "$a.text", "count": 2})],
        "edges": [_canh("e1", "a", "b", "text", "prompt")]}])
    g = bien_dich.bien_dich(doc, cong_cu=CC)
    b = next(n for n in g["nodes"] if n["id"] == "b")
    assert b["params"] == {"prompt": "{{ nodes.a.output.text }}", "count": 2}
    assert bien_dich.la_tham_chieu(b["params"]["prompt"]) == ("a", "text")
    assert g["thu_tu"] == ["a", "b"]


@pytest.mark.parametrize("pages,ma", [
    ([{"id": "p1", "nodes": [_node("a", "text.chat")], "edges": []},
      {"id": "p2", "nodes": [_node("a", "text.chat")], "edges": []}], "id_trung"),
    ([{"id": "p1", "nodes": [_node("a", "text.chat")], "edges": []},
      {"id": "p2", "nodes": [_node("b", "text.chat")],
       "edges": [_canh("e", "a", "b")]}], "canh_khac_trang"),
    ([{"id": "p1", "nodes": [_node("a", "text.chat"), _node("b", "text.chat")],
       "edges": [_canh("e1", "a", "b"), _canh("e2", "b", "a")]}], "chu_trinh"),
    ([{"id": "p1", "nodes": [_node("a", "khong.co")], "edges": []}],
     "node_khong_ton_tai"),
    ([{"id": "p1", "nodes": [_node("a", "text.chat",
                                   {"x": "Xin {{ trigger.body }}"})],
       "edges": []}], "bieu_thuc_chua_ho_tro"),
    ([{"id": "p1", "nodes": [_node("a" * 65, "text.chat")], "edges": []}],
     "id_khong_hop_le"),
    ([{"id": "p1", "nodes": [_node("a", "text.chat")],
       "edges": [_canh("e", "a", "a", kind="MAGIC")]}], "canh_khong_hop_le"),
])
def test_tu_choi_co_ma(pages, ma):
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(_doc(pages), cong_cu=CC)
    assert e.value.ma == ma


def test_do_thi_rong_bi_tu_choi():
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(_doc([{"id": "p1", "nodes": [], "edges": []}]),
                            cong_cu=CC)
    assert e.value.ma == "do_thi_rong"


def test_tham_chieu_toi_node_khong_phai_to_tien():
    doc = _doc([{"id": "p1", "nodes": [
        _node("a", "text.chat"), _node("b", "text.chat", {"q": "$a.text"})],
        "edges": []}])
    with pytest.raises(bien_dich.LoiBienDich) as e:
        bien_dich.bien_dich(doc, cong_cu=CC)
    assert e.value.ma == "tham_chieu_khong_phai_to_tien"


def test_tat_ca_tra_ve_text_chat_tu_registry_that():
    """Bảo vệ adapter khỏi trôi so với registry thật — không mock.

    `text.chat` sống ở app `ltt_llm` (`apps/ltt_llm/manifest.py`); nếu tên
    tool, job_type hay app_slug đổi mà adapter `cong_cu.tat_ca()` không theo
    kịp, phép này đỏ trước khi compiler dùng dữ liệu sai lặng lẽ.
    """
    from platform_core.workflow import cong_cu

    ra = cong_cu.tat_ca()
    assert "text.chat" in ra
    assert ra["text.chat"].app_slug == "ltt_llm"
