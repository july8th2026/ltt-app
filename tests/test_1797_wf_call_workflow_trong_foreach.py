"""`core.call_workflow` **trong thân `foreach`** — một lỗ TIỀN, đã đo.

## Số đo (24/09, trước bản sửa)

Cùng một workflow con, chạy qua hai đồ thị khác nhau đúng **một** điểm:

| Đồ thị | run | node | số run con | `ket_so_luc` |
|---|---|---|---|---|
| `call_workflow` **trong** `foreach` (2 vòng) | `RUNNING` | `f:0/g` **WAITING** · `f:1/g` **WAITING** | 2 | `NULL` |
| **ĐỐI CHỨNG** — cùng thứ, **ngoài** `foreach` | `SUCCEEDED` | `g` `SUCCEEDED` | 1 | có |

Cả hai run con **đã chạy xong**. Cha vẫn đứng `WAITING` tới `TRAN_RUN` 20 giờ,
và `ket_so_luc IS NULL` nghĩa là **khoản giữ chỗ credit vẫn bị giam**. Không
ném, không log — đúng hạng lỗi bốn lỗ tiền của phase gốc 4.

⚠️ **Vế đối chứng là bắt buộc**, không phải trang trí: không có nó, một phép
   kiểm "node đứng WAITING" chỉ chứng minh rằng phép đo hỏng ở đâu đó, chứ
   không chứng minh điều gì về `vong`.

## Nguyên nhân

`run_con.ap_ket_qua_con` duyệt `graph["nodes"]` và tra ảnh chụp với `vong=()`.
Sau khi `node_run` đổi sang khoá **đường thi hành** (P3 task C), ảnh chụp của
node thân nằm ở `f:0/g` — lần tra khoá trần **không thấy gì**, và node bị
`continue` bỏ qua. Cùng hạng lỗi với `wakeup` / `node_run` / `dedupe_key`: khoá
thiếu ngữ cảnh vòng lặp.

## Và một lỗ thứ hai cùng họ, cũng vá ở đây

`run_con.bao_cha` hẹn wakeup theo `duong_thi_hanh(parent_node_id)`. Với
`parent_node_id` là id **trần**, hai vòng cùng gọi một node con sinh **cùng**
`node_run_id` ⇒ `uq_wakeup_khu_trung` ném, hoặc vòng 2 nhận wakeup của vòng 1.
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401


def _core(nid: str, loai: str, **params) -> dict:
    return {"id": nid, "type": f"core.{loai}", "position": {"x": 0, "y": 0},
            "params": params}


def _canh(a: str, b: str) -> dict:
    return {"id": f"{a}-{b}", "source_node": a, "target_node": b,
            "source_port": "out", "target_port": "in", "kind": "DATA",
            "condition": ""}


@pytest.fixture()
def moi_truong(db, monkeypatch):
    from platform_core import credit
    from platform_core.workflow import cong_cu, dinh_nghia
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: {})
    credit.nap(db, "u1", 100_000, note="test")
    dem = {"n": 0}

    def _pub(ten, nodes, edges=()):
        dem["n"] += 1
        w = dinh_nghia.tao_workflow(db, owner_id="u1", name=f"{ten}{dem['n']}")
        dinh_nghia.luu_draft(db, w.id, revision=0, document={
            "version": 3, "pages": [{"id": "p1", "nodes": nodes,
                                     "edges": list(edges)}]})
        v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu={})
        w.published_version_id = v.id
        db.flush()
        return w, v
    return _pub


def _chay_het(db, run, lan: int = 12):
    from platform_core.models import WorkflowRun
    from platform_core.workflow import dong_co
    for _ in range(lan):
        dong_co.xu_ly_run(db, run.id, cong_cu={})
        for con in db.query(WorkflowRun).filter_by(parent_run_id=run.id).all():
            dong_co.xu_ly_run(db, con.id, cong_cu={})
        db.flush()


def _dung(db, moi_truong, *, trong_foreach: bool):
    from platform_core.workflow import tao_run

    con_w, con_v = moi_truong("con", [
        _core("s", "set", bien={"x": "1"}),
        _core("o", "output", ten="r", gia_tri="vars.x")], [_canh("s", "o")])
    goi = _core("g", "call_workflow", workflow_id=con_w.id,
                version_id=con_v.id, inputs={})
    if trong_foreach:
        nodes = [_core("f", "foreach", items="[1, 2]", max_items=5,
                       parallelism=2), goi,
                 _core("fe", "foreach_end", foreach="f")]
        edges = [_canh("f", "g"), _canh("g", "fe")]
    else:
        nodes, edges = [goi], []
    w, _v = moi_truong("cha", nodes, edges)
    run, _ = tao_run.tao_run(db, workflow=w, owner_id="u1",
                             trigger_kind="manual",
                             idempotency_key=f"cw-{trong_foreach}")
    db.flush()
    _chay_het(db, run)
    return run


def _tt(db, run, nid, vong=()):
    from platform_core.workflow import may_trang_thai as mtt
    return mtt.trang_thai_node(db, run.id, nid, vong)


# ── ĐỐI CHỨNG: cùng đồ thị, `call_workflow` NGOÀI `foreach` ─────────────────

def test_doi_chung_call_workflow_NGOAI_foreach_chot_binh_thuong(db, moi_truong):
    """Không có vế này thì phép dưới chỉ chứng minh "phép đo hỏng ở đâu đó"."""
    run = _dung(db, moi_truong, trong_foreach=False)
    assert _tt(db, run, "g") == "SUCCEEDED"
    assert run.status == "SUCCEEDED"
    assert run.ket_so_luc is not None, "khoan giu cho phai duoc ket so"


# ── Ca thật: TRONG `foreach` ───────────────────────────────────────────────

def test_call_workflow_TRONG_foreach_moi_vong_duoc_chot(db, moi_truong):
    from platform_core.models import WorkflowRun

    run = _dung(db, moi_truong, trong_foreach=True)
    assert _tt(db, run, "g", (("f", 0),)) == "SUCCEEDED"
    assert _tt(db, run, "g", (("f", 1),)) == "SUCCEEDED"
    assert run.status == "SUCCEEDED"
    # ⭐ Đây là vế TIỀN: `ket_so_luc IS NULL` nghĩa là khoản giữ chỗ còn giam.
    assert run.ket_so_luc is not None
    con = db.query(WorkflowRun).filter_by(parent_run_id=run.id).all()
    assert len(con) == 2, "moi vong mot run con"


def test_moi_vong_mot_parent_node_id_RIENG_theo_duong_thi_hanh(db, moi_truong):
    """Lỗ thứ hai: `bao_cha` hẹn wakeup theo `parent_node_id`."""
    from platform_core.models import Wakeup, WorkflowRun

    run = _dung(db, moi_truong, trong_foreach=True)
    con = db.query(WorkflowRun).filter_by(parent_run_id=run.id).all()
    assert {c.parent_node_id for c in con} == {"f:0/g", "f:1/g"}, \
        [c.parent_node_id for c in con]
    duong = {w.node_run_id for w in db.query(Wakeup).filter_by(run_id=run.id)
             if w.kind == "child_run"}
    assert duong == {"f:0/g", "f:1/g"}, duong


# ── Quyền sở hữu điểm chờ ──────────────────────────────────────────────────

def test_cho_py_KHONG_nhan_vo_diem_cho_cua_run_con(db):
    """🔴 Một hồi quy đã đo (24/09) khi dựng `core.delay`.

    `nut_loi/cho.la_node_cho` từng trả `True` cho **mọi** node có `cho` khác
    rỗng. `core.call_workflow` khai `cho=("run_con",)` — điểm chờ của nó do
    `run_con.ap_ket_qua_con` chốt — nên `tiep_cho` nhặt nó lên, `tiep_mot`
    không tìm thấy hàng `waitpoint` nào và trả `FAILED loi_he_thong`. **Mọi**
    run có `core.call_workflow` hỏng ngay ở lượt động cơ kế tiếp.

    ⇒ Quyền sở hữu phải là một tập ĐÓNG, và một phép kiểm phải nói ra nó.
    """
    from platform_core.workflow.nut_loi import cho

    assert cho.la_node_cho({"type": "core.delay"}) is True
    assert cho.la_node_cho({"type": "core.wait"}) is True
    assert cho.la_node_cho({"type": "core.human"}) is True
    assert cho.la_node_cho({"type": "core.call_workflow"}) is False
    assert cho.la_node_cho({"type": "core.if"}) is False
    assert "run_con" not in {k.lower() for k in cho.KIND_CUA_TOI}
