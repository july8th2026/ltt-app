"""LTT WORKFLOW V2 · Đợt 2.2 — thi hành: `node_run` + `node_run_snapshot`.

Mô hình **C** (`12_19 §16.2`, chốt `Q3`): trạng thái mỗi node là một **chuỗi ảnh
chụp BẤT BIẾN**, không phải một khối JSON sửa tại chỗ.

🔴 Ngưỡng `M1` là lý do tồn tại của cả đợt này. Cách cũ (`agent/executor.tick`)
đọc cả `checkpoint`, sửa, ghi lại — `O(31+N)` cho mỗi lượt tiến, dù chỉ một node
đổi. Cách mới: `INSERT` đúng những node vừa đổi + `UPDATE` con trỏ.

Nguồn thiết kế: `docs/architecture/workflow_v2_audit/23_24 §4.2`.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'wf2.db').as_posix()}")
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


@pytest.fixture()
def run(db):
    """Một `workflow_run` đã ghim version, sẵn sàng cho các bài dưới."""
    from platform_core.workflow import dinh_nghia, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="Thu")
    db.commit()
    graph = {"schema_version": 1,
             "nodes": [{"id": f"n{i}", "type": "llm.chat", "params": {}}
                       for i in range(3)],
             "edges": []}
    v = dinh_nghia.xuat_ban(db, wf.id, graph, created_by="u1")
    db.commit()
    r = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                         owner_id="u1", trigger_kind="manual")
    db.commit()
    return r


# ── Chuỗi ảnh chụp ────────────────────────────────────────────────────────────

def test_ghi_chuyen_trang_thai_sinh_MOT_anh_chup_moi(db, run):
    from platform_core.models import NodeRunSnapshot
    from platform_core.workflow import thi_hanh

    thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="running",
                        description="bat dau")
    db.commit()

    rows = db.query(NodeRunSnapshot).filter_by(run_id=run.id).all()
    assert len(rows) == 1
    assert rows[0].execution_status == "running"
    assert rows[0].previous_snapshot_id == ""


def test_anh_chup_cu_KHONG_BAO_GIO_bi_sua(db, run):
    """⭐ Trái tim của mô hình C: chỉ thêm, không sửa."""
    from platform_core.models import NodeRunSnapshot
    from platform_core.workflow import thi_hanh

    a = thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="running",
                            description="bat dau")
    db.commit()
    a_id, a_status, a_luc = a.id, a.execution_status, a.created_at

    thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="succeeded",
                        description="xong")
    db.commit()

    cu = db.get(NodeRunSnapshot, a_id)
    assert (cu.execution_status, cu.created_at) == (a_status, a_luc)
    assert db.query(NodeRunSnapshot).filter_by(run_id=run.id).count() == 2


def test_anh_chup_noi_thanh_CHUOI_qua_previous_snapshot_id(db, run):
    from platform_core.workflow import thi_hanh

    a = thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="running",
                            description="1")
    db.commit()
    b = thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="succeeded",
                            description="2")
    db.commit()

    assert b.previous_snapshot_id == a.id


def test_con_tro_node_run_tro_toi_anh_chup_MOI_NHAT(db, run):
    from platform_core.models import NodeRun
    from platform_core.workflow import thi_hanh

    thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="running",
                        description="1")
    db.commit()
    b = thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="succeeded",
                            description="2")
    db.commit()

    con_tro = db.get(NodeRun, (run.id, "n0"))
    assert con_tro.latest_snapshot_id == b.id


def test_lan_chuyen_BI_TU_CHOI_van_duoc_GHI_LAI(db, run):
    """⭐ `is_valid=False` — điều tra được chuyển trạng thái tranh chấp (`G19`).

    Cách cũ vứt lần chuyển bị từ chối đi, nên khi hai worker cùng tiến một node
    thì **không còn dấu vết** để biết ai thua và vì sao. Ghi lại thì tốn một
    hàng; không ghi thì tốn một buổi điều tra không kết luận được.
    """
    from platform_core.models import NodeRunSnapshot
    from platform_core.workflow import thi_hanh

    thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="succeeded",
                        description="xong")
    db.commit()
    thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="running",
                        description="worker cham chan chay lai",
                        is_valid=False)
    db.commit()

    rows = (db.query(NodeRunSnapshot).filter_by(run_id=run.id)
            .order_by(NodeRunSnapshot.created_at).all())
    assert [r.is_valid for r in rows] == [True, False]


def test_lan_chuyen_bi_tu_choi_KHONG_doi_con_tro(db, run):
    """Ghi lại **không** có nghĩa là chấp nhận."""
    from platform_core.models import NodeRun
    from platform_core.workflow import thi_hanh

    ok = thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="succeeded",
                             description="xong")
    db.commit()
    thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="running",
                        description="bi tu choi", is_valid=False)
    db.commit()

    assert db.get(NodeRun, (run.id, "n0")).latest_snapshot_id == ok.id


# ── Ngưỡng M1 ─────────────────────────────────────────────────────────────────

def test_M1_tien_MOT_node_chi_ghi_MOT_hang_du_run_co_31_node(db):
    """🔴 `M1`: `O(node đổi)`, KHÔNG phải `O(31+N)`.

    Đây là ngưỡng số, không phải một nhận định về kiểu dáng. Đo bằng cách đếm
    hàng `node_run_snapshot` sinh ra, vì đó chính là thứ cách cũ làm nở ra.
    """
    from platform_core.models import NodeRunSnapshot
    from platform_core.workflow import dinh_nghia, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="To")
    db.commit()
    graph = {"schema_version": 1,
             "nodes": [{"id": f"n{i}", "type": "llm.chat", "params": {}}
                       for i in range(31)],
             "edges": []}
    v = dinh_nghia.xuat_ban(db, wf.id, graph, created_by="u1")
    db.commit()
    r = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                         owner_id="u1", trigger_kind="manual")
    db.commit()

    truoc = db.query(NodeRunSnapshot).filter_by(run_id=r.id).count()
    thi_hanh.ghi_chuyen(db, r.id, "n7", execution_status="running",
                        description="mot node")
    db.commit()
    sau = db.query(NodeRunSnapshot).filter_by(run_id=r.id).count()

    assert sau - truoc == 1, (
        f"tien 1 node trong run 31 node ghi {sau - truoc} hang - phai la 1")


# ── Ghim version · idempotency · tiền ─────────────────────────────────────────

def test_run_GHIM_version_id_khong_doi_theo_workflow(db):
    """Sửa workflow lúc 10:00 KHÔNG được đổi lượt chạy bắt đầu 09:58."""
    from platform_core.workflow import dinh_nghia, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="Thu")
    db.commit()
    g1 = {"schema_version": 1, "nodes": [{"id": "a", "type": "t", "params": {}}],
          "edges": []}
    v1 = dinh_nghia.xuat_ban(db, wf.id, g1, created_by="u1")
    db.commit()
    r = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v1.id,
                         owner_id="u1", trigger_kind="manual")
    db.commit()

    g2 = {"schema_version": 1, "nodes": [{"id": "a", "type": "t",
                                          "params": {"x": 1}}], "edges": []}
    v2 = dinh_nghia.xuat_ban(db, wf.id, g2, created_by="u1")
    db.commit()

    db.refresh(r)
    assert r.version_id == v1.id != v2.id


def test_idempotency_key_trung_bi_CSDL_tu_choi(db):
    """⭐ Ràng buộc, không phải SELECT-rồi-INSERT (`23_24 §4.2`)."""
    import sqlalchemy.exc
    from platform_core.workflow import dinh_nghia, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="Thu")
    db.commit()
    g = {"schema_version": 1, "nodes": [], "edges": []}
    v = dinh_nghia.xuat_ban(db, wf.id, g, created_by="u1")
    db.commit()

    thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id, owner_id="u1",
                     trigger_kind="api", idempotency_key="k1")
    db.commit()

    # ⚠️ Loi noi len o `flush()` BEN TRONG `tao_run`, khong phai o `commit()`.
    #    `tao_run` phai `flush()` de co `id`, va `flush()` la luc INSERT cham
    #    CSDL. Ban dau bai nay chi boc `db.commit()` va do la mot chan doan sai
    #    ve NOI loi xuat hien - docstring cua `tao_run` cung noi sai y het, va
    #    da sua theo.
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                         owner_id="u1", trigger_kind="api",
                         idempotency_key="k1")
        db.commit()
    db.rollback()


def test_idempotency_key_trung_nhung_KHAC_CHU_thi_duoc(db):
    """Ràng buộc là (owner_id, idempotency_key) — không phải khoá toàn cục."""
    from platform_core.workflow import dinh_nghia, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="Thu")
    db.commit()
    v = dinh_nghia.xuat_ban(db, wf.id, {"schema_version": 1, "nodes": [],
                                        "edges": []}, created_by="u1")
    db.commit()

    a = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                         owner_id="u1", trigger_kind="api",
                         idempotency_key="k1")
    b = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                         owner_id="u2", trigger_kind="api",
                         idempotency_key="k1")
    db.commit()
    assert a.id != b.id


def test_idempotency_key_RONG_khong_bi_chan(db):
    """Phần lớn run không dùng khoá; một UNIQUE đầy đủ sẽ chặn run thứ hai."""
    from platform_core.workflow import dinh_nghia, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="Thu")
    db.commit()
    v = dinh_nghia.xuat_ban(db, wf.id, {"schema_version": 1, "nodes": [],
                                        "edges": []}, created_by="u1")
    db.commit()

    a = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                         owner_id="u1", trigger_kind="manual")
    b = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                         owner_id="u1", trigger_kind="manual")
    db.commit()
    assert a.id != b.id


def test_cost_credit_ghi_LUC_KET_THUC_khong_tinh_lai(db, run):
    """Chi phí theo attempt (`G21`): mỗi ảnh chụp giữ con số của LƯỢT ĐÓ."""
    from platform_core.workflow import thi_hanh

    a = thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="failed",
                            description="lan 1", attempt_number=1,
                            cost_credit=12)
    b = thi_hanh.ghi_chuyen(db, run.id, "n0", execution_status="succeeded",
                            description="lan 2", attempt_number=2,
                            cost_credit=30)
    db.commit()

    assert (a.cost_credit, a.attempt_number) == (12, 1)
    assert (b.cost_credit, b.attempt_number) == (30, 2)


def test_output_ref_chi_giu_THAM_CHIEU_khong_giu_bytes(db, run):
    """⛔ Ảnh chụp là siêu dữ liệu. Bytes ở artifact store, không ở CSDL."""
    from platform_core.workflow import thi_hanh

    s = thi_hanh.ghi_chuyen(
        db, run.id, "n0", execution_status="succeeded", description="xong",
        output_ref={"artifact_id": "a-123", "kind": "image", "bytes": 91234})
    db.commit()
    assert s.output_ref["artifact_id"] == "a-123"
    assert "data" not in s.output_ref and "content" not in s.output_ref
