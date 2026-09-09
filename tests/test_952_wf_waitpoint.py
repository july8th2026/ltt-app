"""LTT WORKFLOW V2 · Đợt 2.3 — waitpoint: barrier N-of-M và `sealed`.

Nguồn thiết kế: `docs/architecture/workflow_v2_audit/23_24 §4.3`.

🔴 Ba quyết định ở đây đều đến từ một khiếm khuyết ĐO ĐƯỢC ở kho khác, không
   phải từ sở thích:

   nhiều-nhiều   `WF-204`: 20 node ForEach cùng chờ MỘT job GPU. Mô hình
                 một-waitpoint-một-bước của Activepieces không biểu đạt nổi.
   `sealed`      không có nó thì `ALL` **không định nghĩa được** khi số nhánh
                 là động — "đủ tất cả" so với cái gì?
   `NOT_DISPATCHED`  tín hiệu lẽ ra phải gửi mà chưa bao giờ gửi. Thiếu nó,
                 một nhánh chết treo barrier **vĩnh viễn**.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'wf3.db').as_posix()}")
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
    from platform_core.workflow import dinh_nghia, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="Thu")
    db.commit()
    v = dinh_nghia.xuat_ban(db, wf.id, {"schema_version": 1, "nodes": [],
                                        "edges": []}, created_by="u1")
    db.commit()
    r = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                         owner_id="u1", trigger_kind="manual")
    db.commit()
    return r


# ── Nhiều-nhiều ───────────────────────────────────────────────────────────────

def test_MOT_waitpoint_chan_duoc_NHIEU_node(db, run):
    """⭐ `WF-204`: 20 node ForEach cùng chờ một job GPU."""
    from platform_core.workflow import cho_doi

    wp = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1", kind="JOB")
    for i in range(20):
        cho_doi.chan_node(db, run_id=run.id, node_id=f"n{i}", waitpoint_id=wp.id)
    db.commit()

    assert sorted(cho_doi.node_dang_bi_chan(db, wp.id)) == [
        f"n{i}" for i in sorted(range(20), key=str)]


def test_MOT_node_cho_duoc_NHIEU_waitpoint(db, run):
    """Chiều ngược lại của nhiều-nhiều: một node chờ hai thứ khác nhau."""
    from platform_core.workflow import cho_doi

    a = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1", kind="JOB")
    b = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1", kind="HUMAN")
    cho_doi.chan_node(db, run_id=run.id, node_id="n0", waitpoint_id=a.id)
    cho_doi.chan_node(db, run_id=run.id, node_id="n0", waitpoint_id=b.id)
    db.commit()

    assert sorted(cho_doi.waitpoint_cua_node(db, run.id, "n0")) == sorted(
        [a.id, b.id])


def test_chan_cung_mot_cap_HAI_LAN_khong_tao_hang_thu_hai(db, run):
    """Khoá chính (run, node, waitpoint) — chặn lại là phép luỹ đẳng."""
    from platform_core.workflow import cho_doi

    wp = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1", kind="JOB")
    cho_doi.chan_node(db, run_id=run.id, node_id="n0", waitpoint_id=wp.id)
    cho_doi.chan_node(db, run_id=run.id, node_id="n0", waitpoint_id=wp.id)
    db.commit()

    assert cho_doi.node_dang_bi_chan(db, wp.id) == ["n0"]


# ── Barrier N-of-M ────────────────────────────────────────────────────────────

def test_barrier_chua_du_thi_CHUA_mo(db, run):
    from platform_core.workflow import cho_doi

    wp = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1",
                               kind="BARRIER", required_successes=3)
    for i in range(2):
        cho_doi.ghi_tin_hieu(db, wp.id, seq=i, status="SUCCEEDED")
    db.commit()

    assert cho_doi.da_mo(db, wp.id) is False
    assert wp.status == "PENDING"


def test_barrier_DU_thi_mo(db, run):
    from platform_core.workflow import cho_doi

    wp = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1",
                               kind="BARRIER", required_successes=3)
    for i in range(3):
        cho_doi.ghi_tin_hieu(db, wp.id, seq=i, status="SUCCEEDED")
    db.commit()

    assert cho_doi.da_mo(db, wp.id) is True


def test_tin_hieu_THAT_BAI_khong_tinh_vao_so_thanh_cong(db, run):
    from platform_core.workflow import cho_doi

    wp = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1",
                               kind="BARRIER", required_successes=2)
    cho_doi.ghi_tin_hieu(db, wp.id, seq=0, status="SUCCEEDED")
    cho_doi.ghi_tin_hieu(db, wp.id, seq=1, status="FAILED")
    db.commit()

    assert cho_doi.da_mo(db, wp.id) is False


def test_release_on_first_failure_mo_ngay_khi_co_mot_that_bai(db, run):
    """Chính sách khác: hỏng một nhánh thì thả ngay, đừng bắt chờ hết."""
    from platform_core.workflow import cho_doi

    wp = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1",
                               kind="BARRIER", required_successes=5,
                               release_on_first_failure=True)
    cho_doi.ghi_tin_hieu(db, wp.id, seq=0, status="FAILED")
    db.commit()

    assert cho_doi.da_mo(db, wp.id) is True


def test_tin_hieu_trung_seq_bi_CSDL_tu_choi(db, run):
    """`UNIQUE(waitpoint_id, seq)` — hai lần gửi cùng nhánh không cộng đôi."""
    import sqlalchemy.exc
    from platform_core.workflow import cho_doi

    wp = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1",
                               kind="BARRIER", required_successes=2)
    cho_doi.ghi_tin_hieu(db, wp.id, seq=0, status="SUCCEEDED")
    db.commit()
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        cho_doi.ghi_tin_hieu(db, wp.id, seq=0, status="SUCCEEDED")
        db.commit()
    db.rollback()


# ── `sealed` ──────────────────────────────────────────────────────────────────

def test_ALL_khi_CHUA_niem_phong_thi_KHONG_the_ket_luan(db, run):
    """⭐ Không có `sealed` thì "đủ TẤT CẢ" là một câu không có nghĩa.

    `required_successes=0` nghĩa là ALL. Chừng nào còn có thể xuất hiện nhánh
    mới, "tất cả" chưa xác định — trả `False` ở đây **không** phải "chưa đủ",
    mà là "chưa biết".
    """
    from platform_core.workflow import cho_doi

    wp = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1",
                               kind="BARRIER", required_successes=0)
    cho_doi.ghi_tin_hieu(db, wp.id, seq=0, status="SUCCEEDED")
    cho_doi.ghi_tin_hieu(db, wp.id, seq=1, status="SUCCEEDED")
    db.commit()

    assert wp.sealed is False
    assert cho_doi.da_mo(db, wp.id) is False


def test_ALL_sau_khi_NIEM_PHONG_thi_ket_luan_duoc(db, run):
    from platform_core.workflow import cho_doi

    wp = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1",
                               kind="BARRIER", required_successes=0)
    cho_doi.ghi_tin_hieu(db, wp.id, seq=0, status="SUCCEEDED")
    cho_doi.ghi_tin_hieu(db, wp.id, seq=1, status="SUCCEEDED")
    cho_doi.niem_phong(db, wp.id)
    db.commit()

    assert wp.sealed is True
    assert cho_doi.da_mo(db, wp.id) is True


def test_NOT_DISPATCHED_khong_treo_barrier_vinh_vien(db, run):
    """⭐ Một nhánh chết: tín hiệu lẽ ra phải gửi mà không bao giờ gửi.

    Không có trạng thái này thì `ALL` sau khi niêm phong vẫn đứng mãi, vì
    nhánh ấy không SUCCEEDED cũng không FAILED — nó **vắng mặt**. Ghi nó ra
    biến một treo vô hạn thành một kết luận.
    """
    from platform_core.workflow import cho_doi

    wp = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1",
                               kind="BARRIER", required_successes=0)
    cho_doi.ghi_tin_hieu(db, wp.id, seq=0, status="SUCCEEDED")
    cho_doi.ghi_tin_hieu(db, wp.id, seq=1, status="NOT_DISPATCHED")
    cho_doi.niem_phong(db, wp.id)
    db.commit()

    assert cho_doi.da_mo(db, wp.id) is True, (
        "nhanh khong bao gio gui phai duoc ket luan, khong duoc treo")


# ── Idempotency ───────────────────────────────────────────────────────────────

def test_idempotency_key_trung_bi_tu_choi(db, run):
    import sqlalchemy.exc
    from platform_core.workflow import cho_doi

    cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1", kind="HUMAN",
                          idempotency_key="k1")
    db.commit()
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1", kind="HUMAN",
                              idempotency_key="k1")
        db.commit()
    db.rollback()


def test_idempotency_key_RONG_khong_bi_chan(db, run):
    """Phần lớn waitpoint không dùng khoá — UNIQUE đầy đủ sẽ chặn cái thứ hai."""
    from platform_core.workflow import cho_doi

    a = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1", kind="JOB")
    b = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id="u1", kind="JOB")
    db.commit()
    assert a.id != b.id
