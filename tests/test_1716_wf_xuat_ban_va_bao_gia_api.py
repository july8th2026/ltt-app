"""Publish = biên dịch + báo giá; quote công khai = estimated_max của version."""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401  (fixture)
from platform_core.workflow.cong_cu import CongCu

# `returns` phai khai: validator publish (spec 6.2, `bien_dich`) kiem
# `nodes.<id>.output.<cong>` bang chinh tap nay, nen mot `CongCu` gia khong
# khai `returns` la mot node KHONG co cong ra nao va `$a.text` duoi kia bi tu
# choi -- dung hanh vi mong muon.
CC = {"text.chat": CongCu(ten="text.chat", app_slug="ltt_llm",
                          job_type="ltt_llm.chat", type_version=1,
                          params_schema={}, side_effect="external",
                          idempotency_fields=(), tinh_gia=lambda p: 3,
                          returns={"text": "text"})}


def _draft(db):
    from platform_core.workflow import dinh_nghia
    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="t")
    doc = {"version": 3, "pages": [{"id": "p1", "nodes": [
        {"id": "a", "type": "tool", "position": {"x": 0, "y": 0},
         "data": {"tool": "text.chat", "params": {}}},
        {"id": "b", "type": "tool", "position": {"x": 0, "y": 0},
         "data": {"tool": "text.chat", "params": {"q": "$a.text"}}}],
        "edges": [{"id": "e", "source_node": "a", "target_node": "b",
                   "source_port": "text", "target_port": "q", "kind": "DATA"}]}]}
    dinh_nghia.luu_draft(db, wf.id, document=doc, revision=0)
    return wf


def test_xuat_ban_draft_luu_do_thi_bien_dich_va_gia(db):
    from platform_core.models import WorkflowVersionNode
    from platform_core.workflow import dinh_nghia
    wf = _draft(db)
    v = dinh_nghia.xuat_ban_draft(db, wf.id, created_by="u1", cong_cu=CC)
    assert v.graph["schema"] == "ltt.workflow/3"
    assert v.estimated_max == 6 and v.graph["bang_gia"] == {"a": 3, "b": 3}
    # Chỉ mục dẫn xuất nay sinh được (trước đây rỗng với đồ thị `pages`).
    assert db.query(WorkflowVersionNode).filter_by(version_id=v.id).count() == 2


def test_xuat_ban_lai_cung_noi_dung_tra_version_cu(db):
    from platform_core.workflow import dinh_nghia
    wf = _draft(db)
    v1 = dinh_nghia.xuat_ban_draft(db, wf.id, created_by="u1", cong_cu=CC)
    v2 = dinh_nghia.xuat_ban_draft(db, wf.id, created_by="u1", cong_cu=CC)
    assert v1.id == v2.id
