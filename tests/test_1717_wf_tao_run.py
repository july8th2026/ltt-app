"""tao_run: ghim version, giữ tiền một lần, QUEUED + wakeup + sự kiện + job động cơ."""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401
from tests.test_1716_wf_xuat_ban_va_bao_gia_api import CC, _draft


@pytest.fixture()
def wf(db, monkeypatch):
    from platform_core import credit
    from platform_core.workflow import dinh_nghia
    w = _draft(db)
    v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
    w.published_version_id = v.id
    credit.nap(db, "u1", 100, note="test")   # dùng đúng hàm nạp của credit.py
    db.flush()
    return w


def test_tao_run_day_du(db, wf):
    from platform_core.models import Job, Wakeup
    from platform_core.workflow import su_kien, tao_run
    run, moi = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                               trigger_kind="manual", idempotency_key="k1")
    assert moi and run.status == "QUEUED" and run.hold_id == run.id
    assert run.estimated_max == 6
    assert db.query(Wakeup).filter_by(run_id=run.id, kind="start").count() == 1
    assert [e.loai for e in su_kien.doc(db, run.id)] == ["WorkflowStarted"]
    dc = db.query(Job).filter_by(job_type=tao_run.DONG_CO_JOB).all()
    assert len(dc) == 1 and dc[0].origin == "workflow"


def test_cung_khoa_tra_run_cu(db, wf):
    from platform_core.workflow import tao_run
    a, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                           trigger_kind="manual", idempotency_key="k1")
    b, moi = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                             trigger_kind="manual", idempotency_key="k1")
    assert a.id == b.id and moi is False


def test_chua_publish_bi_tu_choi(db):
    from platform_core.workflow import dinh_nghia, tao_run
    w = dinh_nghia.tao_workflow(db, owner_id="u1")
    with pytest.raises(tao_run.KhongCoBanPublish):
        tao_run.tao_run(db, workflow=w, owner_id="u1", trigger_kind="manual",
                        idempotency_key="k")


def test_qua_han_muc_run_dong_thoi(db, wf, monkeypatch):
    from platform_core.workflow import tao_run
    monkeypatch.setattr(tao_run, "MAX_RUN_DONG_THOI", 1)
    tao_run.tao_run(db, workflow=wf, owner_id="u1", trigger_kind="manual",
                    idempotency_key="a")
    with pytest.raises(tao_run.QuaHanMuc):
        tao_run.tao_run(db, workflow=wf, owner_id="u1", trigger_kind="manual",
                        idempotency_key="b")
