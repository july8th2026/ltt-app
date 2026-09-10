"""LTT WORKFLOW V2 · Đợt 2.4 — bảng `wakeup`: nguồn chân lý của việc đánh thức.

Chốt `Q4` (`23_24 §3`): bảng là **nguồn chân lý**, `LISTEN/NOTIFY` chỉ **rút
ngắn độ trễ**. Lý do chọn bảng chứ không chọn `NOTIFY` là một con số đo được:

    worker restart 13,6 lan/ngay   (`01 §A.6`)

Một `NOTIFY` phát đúng lúc worker đang khởi động lại **biến mất không dấu vết**.
Bảng thì không. Đây chính là *"polling như dự phòng, không phải cơ chế chính"*
mà `WF-402` yêu cầu.

🔴 Ngưỡng `M2`: một run chờ 60 phút phát sinh **0 câu SQL** trong 60 phút đó, và
bộ quét hỏi *"có hàng nào tới hạn chưa"* bằng **MỘT** truy vấn cho **toàn hệ
thống** — không phải một truy vấn mỗi run.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


def _bay_gio():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'wf4.db').as_posix()}")
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


# ── Nguồn chân lý ─────────────────────────────────────────────────────────────

def test_hen_roi_quet_thi_lay_duoc(db, run):
    from platform_core.workflow import danh_thuc

    danh_thuc.hen(db, run_id=run.id, kind="waitpoint_due",
                  due_at=_bay_gio() - timedelta(seconds=1))
    db.commit()

    assert [w.run_id for w in danh_thuc.den_han(db)] == [run.id]


def test_CHUA_toi_han_thi_KHONG_lay(db, run):
    from platform_core.workflow import danh_thuc

    danh_thuc.hen(db, run_id=run.id, kind="waitpoint_due",
                  due_at=_bay_gio() + timedelta(minutes=60))
    db.commit()

    assert danh_thuc.den_han(db) == []


def test_da_nhat_roi_thi_KHONG_lay_lai(db, run):
    """`claimed_at` là thứ giữ cho hai worker không cùng đánh thức một run."""
    from platform_core.workflow import danh_thuc

    danh_thuc.hen(db, run_id=run.id, kind="job_done",
                  due_at=_bay_gio() - timedelta(seconds=1))
    db.commit()

    lan1 = danh_thuc.nhat(db, gioi_han=10)
    db.commit()
    lan2 = danh_thuc.nhat(db, gioi_han=10)
    db.commit()

    assert len(lan1) == 1 and lan2 == []


# ── Khử trùng bằng RÀNG BUỘC ──────────────────────────────────────────────────

def test_hen_TRUNG_bi_CSDL_tu_choi(db, run):
    """⭐ `UNIQUE(run_id, node_run_id, kind, due_at)` — khử trùng bằng ràng buộc.

    Hai đường cùng hẹn một lần đánh thức (bảng **và** `NOTIFY`, hoặc hai worker
    cùng thấy một job xong) là trạng thái **bình thường**, không phải sự cố.
    Chốt `Q4` nói rõ hai đường phải cùng luỹ đẳng — chỗ cưỡng chế điều đó là
    đây, không phải một `SELECT` cẩn thận ở tầng trên.
    """
    import sqlalchemy.exc
    from platform_core.workflow import danh_thuc

    luc = _bay_gio() + timedelta(minutes=5)
    danh_thuc.hen(db, run_id=run.id, kind="job_done", due_at=luc)
    db.commit()
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        danh_thuc.hen(db, run_id=run.id, kind="job_done", due_at=luc)
        db.commit()
    db.rollback()


def test_khac_kind_thi_khong_coi_la_trung(db, run):
    from platform_core.workflow import danh_thuc

    luc = _bay_gio() + timedelta(minutes=5)
    a = danh_thuc.hen(db, run_id=run.id, kind="job_done", due_at=luc)
    b = danh_thuc.hen(db, run_id=run.id, kind="waitpoint_due", due_at=luc)
    db.commit()
    assert a.id != b.id


def test_khac_node_run_id_thi_khong_coi_la_trung(db, run):
    from platform_core.workflow import danh_thuc

    luc = _bay_gio() + timedelta(minutes=5)
    a = danh_thuc.hen(db, run_id=run.id, node_run_id="n0", kind="job_done",
                      due_at=luc)
    b = danh_thuc.hen(db, run_id=run.id, node_run_id="n1", kind="job_done",
                      due_at=luc)
    db.commit()
    assert a.id != b.id


# ── Ngưỡng M2 ─────────────────────────────────────────────────────────────────

def test_M2_mot_run_cho_60_phut_chi_ton_MOT_hang(db, run):
    """🔴 `M2`: chờ lâu không tốn thêm gì. Một hàng, `due_at = +60 phút`."""
    from platform_core.models import Wakeup
    from platform_core.workflow import danh_thuc

    danh_thuc.hen(db, run_id=run.id, kind="waitpoint_due",
                  due_at=_bay_gio() + timedelta(minutes=60))
    db.commit()

    assert db.query(Wakeup).filter_by(run_id=run.id).count() == 1


def test_M2_bo_quet_hoi_MOT_cau_cho_TOAN_HE_THONG(db):
    """🔴 Bộ quét **không** hỏi từng run. 200 run chờ = vẫn một truy vấn.

    Đo bằng cách đếm câu SQL thật qua `before_cursor_execute`, không bằng cách
    đọc mã và tin — một vòng lặp ẩn trong `den_han()` sẽ hiện ra ở con số này.
    """
    from sqlalchemy import event
    from platform_core.workflow import danh_thuc, dinh_nghia, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="To")
    db.commit()
    v = dinh_nghia.xuat_ban(db, wf.id, {"schema_version": 1, "nodes": [],
                                        "edges": []}, created_by="u1")
    db.commit()
    qua_han = _bay_gio() - timedelta(seconds=1)
    for _ in range(200):
        r = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                             owner_id="u1", trigger_kind="manual")
        danh_thuc.hen(db, run_id=r.id, kind="waitpoint_due", due_at=qua_han)
    db.commit()

    dem = []
    bind = db.get_bind()

    def _ghi(conn, cursor, statement, parameters, context, executemany):
        dem.append(statement)

    event.listen(bind, "before_cursor_execute", _ghi)
    try:
        ra = danh_thuc.den_han(db, gioi_han=500)
    finally:
        event.remove(bind, "before_cursor_execute", _ghi)

    assert len(ra) == 200
    assert len(dem) == 1, (
        f"bo quet chay {len(dem)} cau SQL cho 200 run - phai la 1")


def test_den_han_ton_trong_gioi_han(db, run):
    """Một lượt quét không được kéo cả hàng đợi vào bộ nhớ."""
    from platform_core.workflow import danh_thuc, dinh_nghia, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="To")
    db.commit()
    v = dinh_nghia.xuat_ban(db, wf.id, {"schema_version": 1, "nodes": [],
                                        "edges": []}, created_by="u1")
    db.commit()
    qua_han = _bay_gio() - timedelta(seconds=1)
    for _ in range(30):
        r = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                             owner_id="u1", trigger_kind="manual")
        danh_thuc.hen(db, run_id=r.id, kind="waitpoint_due", due_at=qua_han)
    db.commit()

    assert len(danh_thuc.den_han(db, gioi_han=10)) == 10


def test_lay_som_nhat_truoc(db):
    """Đến hạn lâu nhất được phục vụ trước — không để một run đói mãi."""
    from platform_core.workflow import danh_thuc, dinh_nghia, thi_hanh

    wf = dinh_nghia.tao_workflow(db, owner_id="u1", name="To")
    db.commit()
    v = dinh_nghia.xuat_ban(db, wf.id, {"schema_version": 1, "nodes": [],
                                        "edges": []}, created_by="u1")
    db.commit()
    ids = []
    for phut in (30, 10, 20):
        r = thi_hanh.tao_run(db, workflow_id=wf.id, version_id=v.id,
                             owner_id="u1", trigger_kind="manual")
        danh_thuc.hen(db, run_id=r.id, kind="waitpoint_due",
                      due_at=_bay_gio() - timedelta(minutes=phut))
        ids.append((phut, r.id))
    db.commit()

    ra = [w.run_id for w in danh_thuc.den_han(db, gioi_han=3)]
    mong = [i for _, i in sorted(ids, key=lambda x: -x[0])]
    assert ra == mong
