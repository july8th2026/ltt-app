"""Trần chi phí của thân `foreach` — `max_items × Σ trần thân` (spec §7.2).

🔴 NỢ ĐÃ ĐO (plan wf-v2 §4 P3)

`bao_gia._gia_node` trả **0** cho mọi node không `thi_hanh == "job"`, và tổng
của đồ thị là một phép cộng phẳng. Một node app **trong thân** một `foreach`
`max_items=1000` vì vậy được báo giá **một** lần và chạy **một nghìn** lần.
Trần chi phí khi đó không chặn gì — nó chỉ làm người đọc yên tâm, đúng thứ
`KhongBaoGiaDuoc` được viết ra để từ chối.

Spec §7.2 nói thẳng: *"ForEach: `max_items × trần thân`"*, và §5.9 đã chặn
`max_items ≤ 1000` nên con số này **tất định**, không phải phỏng đoán —
không cần vay cơ chế của ai. (Đối chứng ngành: `bao_gia.py` đầu tệp ghi bảy
kho đã khảo sát, **không kho nào** có trần chi phí; đây là chỗ ta đi một mình.)

## Phép này KHÔNG phủ cái gì

Nó chạy trên **đồ thị đã biên dịch dựng tay**: `bien_dich` chưa biết nhận
`core.foreach` (Task 4–5). Nó phủ **luật giá**, không phủ **đường publish**.
"""
from __future__ import annotations

import pytest

from platform_core.workflow.cong_cu import CongCu

CC = {"text.chat": CongCu(ten="text.chat", app_slug="ltt_llm",
                          job_type="ltt_llm.chat", type_version=1,
                          params_schema={}, side_effect="external",
                          idempotency_fields=(), tinh_gia=lambda p: 3,
                          returns={"text": "text"})}


def _app(nid: str) -> dict:
    return {"id": nid, "type": "app.text.chat", "type_version": 1,
            "params": {}, "credential_ref": "", "settings": {},
            "thi_hanh": "job"}


def _foreach(nid: str, *, max_items: int = 5) -> dict:
    return {"id": nid, "type": "core.foreach", "type_version": 1,
            "params": {"max_items": max_items}, "credential_ref": "",
            "settings": {}, "thi_hanh": "inline"}


def _foreach_end(nid: str, *, cua: str) -> dict:
    return {"id": nid, "type": "core.foreach_end", "type_version": 1,
            "params": {"foreach": cua}, "credential_ref": "", "settings": {},
            "thi_hanh": "inline"}


def _canh(a: str, b: str) -> dict:
    return {"id": f"{a}->{b}", "source_node": a, "target_node": b,
            "source_port": "out", "target_port": "in", "kind": "DATA",
            "condition": ""}


def _do_thi(nodes: list[dict], edges: list[dict]) -> dict:
    return {"schema": "ltt.workflow/3", "inputs": [], "outputs": [],
            "settings": {"max_concurrency": 4, "timeout_s": 600},
            "nodes": nodes, "edges": edges,
            "thu_tu": [n["id"] for n in nodes]}


# ── ĐỐI CHỨNG: đồ thị KHÔNG có foreach phải giữ nguyên con số cũ ────────────

def test_doi_chung_do_thi_phang_khong_bi_nhan():
    """Nếu phép này đỏ thì luật mới đang nhân cả những chỗ không có vòng lặp."""
    from platform_core.workflow.bao_gia import bao_gia_do_thi

    g = _do_thi([_app("a"), _app("b")], [_canh("a", "b")])
    assert bao_gia_do_thi(g, cong_cu=CC).toi_da == 6


# ── LUẬT MỚI ────────────────────────────────────────────────────────────────

def test_than_foreach_duoc_nhan_theo_max_items():
    from platform_core.workflow.bao_gia import bao_gia_do_thi

    g = _do_thi(
        [_foreach("f", max_items=5), _app("x"), _foreach_end("fe", cua="f")],
        [_canh("f", "x"), _canh("x", "fe")])
    assert bao_gia_do_thi(g, cong_cu=CC).toi_da == 15      # 5 x 3


def test_gia_tran_TUNG_NODE_khong_bi_nhan():
    """⛔ `cau_noi.nop_job` so `gia_that > node['gia_tran']` cho MỖI LƯỢT chạy.

    Nhân `gia_tran` lên `max_items` là nới cái cổng ấy ra `max_items` lần: một
    node đắt gấp năm lần dự kiến vẫn đi lọt trong mọi lượt. Hệ số lặp thuộc về
    TỔNG của run, không thuộc về trần của một lượt.
    """
    from platform_core.workflow.bao_gia import bao_gia_do_thi

    g = _do_thi(
        [_foreach("f", max_items=5), _app("x"), _foreach_end("fe", cua="f")],
        [_canh("f", "x"), _canh("x", "fe")])
    bao_gia_do_thi(g, cong_cu=CC)
    node_x = next(n for n in g["nodes"] if n["id"] == "x")
    assert node_x["gia_tran"] == 3 and g["bang_gia"]["x"] == 3
    assert g["he_so_lap"] == {"f": 1, "x": 5, "fe": 1}


def test_node_ngoai_than_khong_bi_nhan():
    from platform_core.workflow.bao_gia import bao_gia_do_thi

    g = _do_thi(
        [_app("truoc"), _foreach("f", max_items=4), _app("x"),
         _foreach_end("fe", cua="f"), _app("sau")],
        [_canh("truoc", "f"), _canh("f", "x"), _canh("x", "fe"),
         _canh("fe", "sau")])
    assert bao_gia_do_thi(g, cong_cu=CC).toi_da == 3 + 4 * 3 + 3


def test_foreach_long_nhau_nhan_don():
    from platform_core.workflow.bao_gia import bao_gia_do_thi

    g = _do_thi(
        [_foreach("f1", max_items=3), _foreach("f2", max_items=4), _app("x"),
         _foreach_end("fe2", cua="f2"), _foreach_end("fe1", cua="f1")],
        [_canh("f1", "f2"), _canh("f2", "x"), _canh("x", "fe2"),
         _canh("fe2", "fe1")])
    assert bao_gia_do_thi(g, cong_cu=CC).toi_da == 3 * 4 * 3


# ── TỪ CHỐI, KHÔNG ĐOÁN ─────────────────────────────────────────────────────

def test_foreach_khong_co_foreach_end_bi_tu_choi():
    """Không biết thân kết thúc ở đâu ⇒ không có chặn trên ⇒ từ chối."""
    from platform_core.workflow.bao_gia import KhongBaoGiaDuoc, bao_gia_do_thi

    g = _do_thi([_foreach("f"), _app("x")], [_canh("f", "x")])
    with pytest.raises(KhongBaoGiaDuoc):
        bao_gia_do_thi(g, cong_cu=CC)


def test_foreach_end_tro_vao_node_khong_phai_foreach_bi_tu_choi():
    from platform_core.workflow.bao_gia import KhongBaoGiaDuoc, bao_gia_do_thi

    g = _do_thi([_app("x"), _foreach_end("fe", cua="x")], [_canh("x", "fe")])
    with pytest.raises(KhongBaoGiaDuoc):
        bao_gia_do_thi(g, cong_cu=CC)


@pytest.mark.parametrize("xau", [0, -1, 1001, None, "nhieu"])
def test_max_items_khong_hop_le_bi_tu_choi(xau):
    """§5.9: bắt buộc và ≤ 1000. Thiếu chặn trên thì trần là một lời nói suông."""
    from platform_core.workflow.bao_gia import KhongBaoGiaDuoc, bao_gia_do_thi

    f = _foreach("f")
    f["params"] = {} if xau is None else {"max_items": xau}
    g = _do_thi([f, _app("x"), _foreach_end("fe", cua="f")],
                [_canh("f", "x"), _canh("x", "fe")])
    with pytest.raises(KhongBaoGiaDuoc):
        bao_gia_do_thi(g, cong_cu=CC)


def test_than_rong_van_bao_gia_duoc():
    """`foreach` trên một thân rỗng tốn 0 — không phải một lỗi."""
    from platform_core.workflow.bao_gia import bao_gia_do_thi

    g = _do_thi([_foreach("f"), _foreach_end("fe", cua="f")], [_canh("f", "fe")])
    assert bao_gia_do_thi(g, cong_cu=CC).toi_da == 0


def test_ba_tang_foreach_day_bi_tu_choi():
    """Tích `max_items` vượt trần ⇒ từ chối, không in ra một con số vô nghĩa.

    1000 × 1000 = 10⁶ vừa khít (`HE_SO_LAP_TOI_DA`); tầng thứ ba thì "trần"
    báo cho khách là 10⁹ lượt — một lời từ chối viết bằng chữ số. Nói thẳng ra
    trung thực hơn.
    """
    from platform_core.workflow.bao_gia import KhongBaoGiaDuoc, bao_gia_do_thi

    ns = [_foreach(f"f{i}", max_items=1000) for i in range(3)]
    es = [_foreach_end(f"fe{i}", cua=f"f{i}") for i in range(3)]
    nodes = ns + [_app("x")] + es[::-1]
    edges = ([_canh("f0", "f1"), _canh("f1", "f2"), _canh("f2", "x"),
              _canh("x", "fe2"), _canh("fe2", "fe1"), _canh("fe1", "fe0")])
    with pytest.raises(KhongBaoGiaDuoc):
        bao_gia_do_thi(_do_thi(nodes, edges), cong_cu=CC)
    # Đối chứng: HAI tầng đầy vẫn báo giá được.
    nodes2 = ns[:2] + [_app("x")] + [es[1], es[0]]
    edges2 = [_canh("f0", "f1"), _canh("f1", "x"), _canh("x", "fe1"),
              _canh("fe1", "fe0")]
    assert bao_gia_do_thi(_do_thi(nodes2, edges2), cong_cu=CC).toi_da == 3_000_000
