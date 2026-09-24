"""Supervisor (spec §12.4) — hành động **có luật**. Plan wf-v2 P8 Task 3.

Bánh cóc *"hành động cấm không có đường gọi"* là **Task 4** (`test_2923`, đọc
AST). Tệp này đo phần còn lại: mỗi hành động ĐƯỢC PHÉP có đúng luật của nó, và
mỗi lần TỪ CHỐI **không đổi gì** ngoài một dòng nhật ký.

## Nguồn

`langchain-ai/langgraph-swarm-py` `langgraph_swarm/handoff.py` —
`create_handoff_tool(agent_name=…)` sinh **một công cụ cho mỗi đích được
phép**, và `get_handoff_destinations()` đọc ngược tập quyền **từ công cụ có
thật**. Quyền là một sự kiện về mã, không phải một bảng khai song song.
"""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.

from datetime import datetime, timedelta, timezone

import pytest

from platform_core.agent import supervisor
from platform_core.workflow.cong_cu import CongCu
from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401

CC = {"text.chat": CongCu(ten="text.chat", app_slug="ltt_llm",
                          job_type="ltt_llm.chat", type_version=1,
                          params_schema={}, side_effect="external",
                          idempotency_fields=("x",), resource={"class": "api"},
                          tinh_gia=lambda p: 3, returns={"text": "text"})}


def _bay_gio():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _nut(nid, **kw):
    # ⚠️ `settings` nằm TRONG `data` cho node kiểu `"tool"` — `bien_dich._node`
    #    đọc `n["data"]["settings"]`. Đặt nhầm lên tầng ngoài thì nó bị NUỐT
    #    im lặng, và một phép kiểm về `retry.max` sẽ đo `{max: 0}`.
    return {"id": nid, "type": "tool", "position": {"x": 0, "y": 0},
            "data": {"tool": "text.chat", "params": {}, **kw}}


@pytest.fixture()
def xuong(db, monkeypatch):
    from platform_core import credit
    from platform_core.workflow import cong_cu, dinh_nghia, tao_run
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    credit.nap(db, "u1", 10000, note="test")
    dem = {"n": 0}

    class _X:
        def chay(self, nodes, edges=()):
            dem["n"] += 1
            w = dinh_nghia.tao_workflow(db, owner_id="u1", name=f"t{dem['n']}")
            dinh_nghia.luu_draft(db, w.id, revision=0, document={
                "version": 3, "pages": [{"id": "p1", "nodes": nodes,
                                         "edges": list(edges)}]})
            v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1",
                                          cong_cu=CC)
            w.published_version_id = v.id
            db.flush()
            run, _ = tao_run.tao_run(db, workflow=w, owner_id="u1",
                                     trigger_kind="manual",
                                     idempotency_key=f"k{dem['n']}")
            from platform_core.workflow import may_trang_thai as mtt
            mtt.chuyen_run(db, run.id, sang="RUNNING")
            return run
    return _X()


def _ep_node(db, run, nid, sang, lan=1):
    """Đưa một node tới trạng thái cần đo, đi qua ĐÚNG máy trạng thái."""
    from platform_core.workflow import may_trang_thai as mtt
    assert mtt.chuyen_node(db, run.id, nid, sang="READY", mo_ta="test")
    if sang != "READY":
        assert mtt.chuyen_node(db, run.id, nid, sang=sang, mo_ta="test",
                               attempt_number=lan), sang


def _su_kien(db, run):
    from platform_core.models import WorkflowEvent
    return db.query(WorkflowEvent).filter_by(
        run_id=run.id, loai="SupervisorDecision").all()


def _tt(db, run, nid):
    from platform_core.workflow import may_trang_thai as mtt
    return mtt.trang_thai_node(db, run.id, nid)


# ── 1. Sổ hành động là ĐÓNG ─────────────────────────────────────────────────

def test_hanh_dong_ngoai_so_KHONG_co_ham_nao_lam(db, xuong):
    run = xuong.chay([_nut("a")])
    for ten in ("tang_hold", "sua_version", "gan_credential",
                "vuot_validator", "doi_model"):
        kq = supervisor.lam(db, run, hanh_dong=ten, node_id="a")
        assert kq.lam is False and kq.ma == "hanh_dong_khong_ton_tai", ten
    assert set(supervisor.HANH_DONG) == {
        "thu_lai_node", "di_nhanh_loi", "hoi_nguoi", "bo_qua_node"}


def test_moi_luot_deu_ghi_SupervisorDecision_ke_ca_khi_TU_CHOI(db, xuong):
    run = xuong.chay([_nut("a")])
    supervisor.lam(db, run, hanh_dong="khong_co_that", node_id="a")
    supervisor.lam(db, run, hanh_dong="hoi_nguoi", node_id="a")
    ev = _su_kien(db, run)
    assert [e.du_lieu["lam"] for e in ev] == [False, True]
    assert ev[0].du_lieu["ma"] == "hanh_dong_khong_ton_tai"


# ── 2. Không đụng run ĐÃ KẾT SỔ (thu hẹp §12.4, xem docstring supervisor) ───

def test_run_da_ket_so_thi_moi_hanh_dong_deu_bi_tu_choi(db, xuong):
    from platform_core.workflow import may_trang_thai as mtt
    run = xuong.chay([_nut("a")])
    mtt.chuyen_run(db, run.id, sang="FAILED")
    for ten in supervisor.HANH_DONG:
        kq = supervisor.lam(db, run, hanh_dong=ten, node_id="a")
        assert kq.lam is False and kq.ma == "run_da_ket_so", ten


def test_quet_chi_lay_run_CHUA_ket_so_va_da_treo_lau(db, xuong):
    from platform_core.workflow import may_trang_thai as mtt
    cu = xuong.chay([_nut("a")])
    moi = xuong.chay([_nut("a")])
    xong = xuong.chay([_nut("a")])
    mtt.chuyen_run(db, xong.id, sang="SUCCEEDED")
    lau = _bay_gio() - timedelta(hours=3)
    cu.started_at = lau
    xong.started_at = lau
    db.flush()
    ra = [r.id for r in supervisor.quet(db, tre_s=3600)]
    assert cu.id in ra
    assert moi.id not in ra            # chua treo du lau
    assert xong.id not in ra           # 🔑 doi chung: da ket so


# ── 3. thu_lai_node — trong `retry.max` CÒN LẠI ─────────────────────────────

def test_thu_lai_node_trong_retry_max_con_lai(db, xuong):
    run = xuong.chay([_nut("a", settings={"retry": {"max": 2}})])
    _ep_node(db, run, "a", "FAILED", lan=1)
    kq = supervisor.lam(db, run, hanh_dong="thu_lai_node", node_id="a")
    assert kq.lam is True
    assert _tt(db, run, "a") == "RETRY_SCHEDULED"


def test_het_luot_thi_TU_CHOI_va_KHONG_doi_trang_thai(db, xuong):
    run = xuong.chay([_nut("a", settings={"retry": {"max": 1}})])
    _ep_node(db, run, "a", "FAILED", lan=2)      # lan 2 > retry.max 1
    kq = supervisor.lam(db, run, hanh_dong="thu_lai_node", node_id="a")
    assert kq.lam is False and kq.ma == "het_luot_thu_lai"
    assert _tt(db, run, "a") == "FAILED"


def test_retry_max_MAC_DINH_0_thi_khong_thu_lai_duoc(db, xuong):
    """🔑 Đối chứng: không khai `retry` ⇒ `{max: 0}` ⇒ hành động vô hiệu."""
    run = xuong.chay([_nut("a")])
    _ep_node(db, run, "a", "FAILED", lan=1)
    kq = supervisor.lam(db, run, hanh_dong="thu_lai_node", node_id="a")
    assert kq.lam is False and kq.ma == "het_luot_thu_lai"


@pytest.mark.parametrize("sang", ["ABANDONED", "CANCELLED", "SUCCEEDED"])
def test_KHONG_thu_lai_node_ABANDONED_du_con_luot(db, xuong, sang):
    """§12.4 cấm thử lại node `irreversible` `ABANDONED` — provider CÓ THỂ đã
    nhận. `retry.max = 3` vẫn không mở được cửa ấy."""
    run = xuong.chay([_nut("a", settings={"retry": {"max": 3}})])
    _ep_node(db, run, "a", "QUEUED")
    from platform_core.workflow import may_trang_thai as mtt
    assert mtt.chuyen_node(db, run.id, "a", sang=sang, mo_ta="test")
    kq = supervisor.lam(db, run, hanh_dong="thu_lai_node", node_id="a")
    assert kq.lam is False and kq.ma == "khong_thu_lai_duoc"
    assert _tt(db, run, "a") == sang


def test_thu_lai_node_khi_node_chua_FAILED_bi_tu_choi(db, xuong):
    run = xuong.chay([_nut("a", settings={"retry": {"max": 2}})])
    _ep_node(db, run, "a", "READY")
    kq = supervisor.lam(db, run, hanh_dong="thu_lai_node", node_id="a")
    assert kq.lam is False and kq.ma == "trang_thai_node_sai"


# ── 4. di_nhanh_loi — nhánh `error` phải ĐÃ KHAI ────────────────────────────

def test_di_nhanh_loi_chi_khi_co_canh_ERROR(db, xuong):
    canh = {"id": "e1", "source_node": "a", "target_node": "b",
            "source_port": "out", "target_port": "in", "kind": "ERROR"}
    run = xuong.chay([_nut("a"), _nut("b")], [canh])
    _ep_node(db, run, "a", "FAILED")
    assert supervisor.lam(db, run, hanh_dong="di_nhanh_loi",
                          node_id="a").lam is True


def test_khong_co_canh_ERROR_thi_TU_CHOI(db, xuong):
    canh = {"id": "e1", "source_node": "a", "target_node": "b",
            "source_port": "out", "target_port": "in", "kind": "DATA"}
    run = xuong.chay([_nut("a"), _nut("b")], [canh])
    _ep_node(db, run, "a", "FAILED")
    kq = supervisor.lam(db, run, hanh_dong="di_nhanh_loi", node_id="a")
    assert kq.lam is False and kq.ma == "khong_co_nhanh_error"


# ── 5. hoi_nguoi — waitpoint HUMAN ──────────────────────────────────────────

def test_hoi_nguoi_mo_waitpoint_HUMAN(db, xuong):
    from platform_core.models import Waitpoint
    run = xuong.chay([_nut("a")])
    assert supervisor.lam(db, run, hanh_dong="hoi_nguoi", node_id="a",
                          cau_hoi="chay tiep khong?").lam is True
    wp = db.query(Waitpoint).filter_by(run_id=run.id).all()
    assert [w.kind for w in wp] == ["HUMAN"]


# ── 6. bo_qua_node — CHỈ node khai `khong_quan_trong` ───────────────────────

def test_bo_qua_node_khong_quan_trong(db, xuong):
    run = xuong.chay([_nut("a", settings={"khong_quan_trong": True})])
    _ep_node(db, run, "a", "FAILED")
    assert supervisor.lam(db, run, hanh_dong="bo_qua_node",
                          node_id="a").lam is True
    assert _tt(db, run, "a") == "SKIPPED"


def test_node_KHONG_khai_khong_quan_trong_thi_khong_bo_qua_duoc(db, xuong):
    run = xuong.chay([_nut("a")])
    _ep_node(db, run, "a", "FAILED")
    kq = supervisor.lam(db, run, hanh_dong="bo_qua_node", node_id="a")
    assert kq.lam is False and kq.ma == "node_van_quan_trong"
    assert _tt(db, run, "a") == "FAILED"


def test_co_KHONG_PHAI_true_thi_van_la_quan_trong(db, xuong):
    """🔑 `"true"`, `1`, `"yes"` đều KHÔNG mở cửa — `is True`, không truthy."""
    run = xuong.chay([_nut("a", settings={"khong_quan_trong": "true"})])
    _ep_node(db, run, "a", "FAILED")
    assert supervisor.lam(db, run, hanh_dong="bo_qua_node",
                          node_id="a").ma == "node_van_quan_trong"


def test_node_khong_co_trong_do_thi_bi_tu_choi(db, xuong):
    run = xuong.chay([_nut("a")])
    for ten in ("thu_lai_node", "di_nhanh_loi", "bo_qua_node"):
        kq = supervisor.lam(db, run, hanh_dong=ten, node_id="khong_co")
        assert kq.lam is False and kq.ma == "node_khong_ton_tai", ten
