"""Workflow V2 trên PostgreSQL thật: hai vòng động cơ song song, crash giữa chừng.

Chạy qua `tools/check_multiproc.py` (tự dựng CSDL scratch theo cây).
"""
from __future__ import annotations

import threading

import pytest

from tests import pg_scratch

pytestmark = pg_scratch.skip_without_postgres()


@pytest.fixture()
def pg(monkeypatch):
    url = pg_scratch.scratch_url()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.drop_all(dbmod.get_engine())
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    yield dbmod
    dbmod.reset_engine()


def _mo(dbmod):
    return lambda: next(dbmod.get_session())


def _chuan_bi(dbmod, monkeypatch, so_run=10):
    from platform_core import credit
    from platform_core.workflow import cong_cu, dinh_nghia, tao_run
    from tests.test_1716_wf_xuat_ban_va_bao_gia_api import CC, _draft
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    db = _mo(dbmod)()
    w = _draft(db)
    v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
    w.published_version_id = v.id
    credit.nap(db, "u1", 10_000, ly_do="test")
    ids = []
    import platform_core.workflow.tao_run as tr
    monkeypatch.setattr(tr, "MAX_RUN_DONG_THOI", 1000)
    for i in range(so_run):
        r, _ = tao_run.tao_run(db, workflow=w, owner_id="u1",
                               trigger_kind="manual", idempotency_key=f"k{i}")
        ids.append(r.id)
    db.commit()
    db.close()
    return ids


def _hoan_tat_job(dbmod):
    from platform_core import jobs
    from platform_core.job_scheduler import ORIGIN_WORKFLOW
    from platform_core.models import JOB_QUEUED, Job
    from platform_core.workflow import tao_run
    db = _mo(dbmod)()
    for j in db.query(Job).filter(Job.origin == ORIGIN_WORKFLOW,
                                  Job.job_type != tao_run.DONG_CO_JOB,
                                  Job.status == JOB_QUEUED).all():
        jobs.complete(db, j, {"text": "x"})
    db.commit()
    db.close()


def test_hai_vong_song_song_khong_nop_doi(pg, monkeypatch):
    from platform_core.models import Job
    from platform_core.workflow import dong_co
    ids = _chuan_bi(pg, monkeypatch)
    for _ in range(3):
        t = [threading.Thread(target=dong_co.mot_vong, args=(_mo(pg),))
             for _ in range(2)]
        [x.start() for x in t]
        [x.join() for x in t]
        _hoan_tat_job(pg)
    dong_co.mot_vong(_mo(pg))
    db = _mo(pg)()
    for rid in ids:
        assert db.query(Job).filter_by(plan_id=rid).count() == 2   # a và b, không đôi
    from platform_core.models import WorkflowRun
    assert {r.status for r in db.query(WorkflowRun).all()} == {"SUCCEEDED"}
    db.close()


def test_crash_giua_chung_resume_dung(pg, monkeypatch):
    """FLOW H: vòng động cơ chết sau khi nộp job, trước commit ⇒ không job ma."""
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, dong_co
    ids = _chuan_bi(pg, monkeypatch, so_run=1)
    goc = cau_noi.nop_job

    def chet(*a, **k):
        goc(*a, **k)
        raise SystemExit("worker bi giet")
    monkeypatch.setattr(cau_noi, "nop_job", chet)
    with pytest.raises(SystemExit):
        dong_co.mot_vong(_mo(pg))
    monkeypatch.setattr(cau_noi, "nop_job", goc)
    db = _mo(pg)()
    assert db.query(Job).filter_by(plan_id=ids[0]).count() == 0   # đã rollback
    db.close()
    dong_co.mot_vong(_mo(pg))
    _hoan_tat_job(pg)
    dong_co.mot_vong(_mo(pg))
    _hoan_tat_job(pg)
    dong_co.mot_vong(_mo(pg))
    db = _mo(pg)()
    assert db.query(Job).filter_by(plan_id=ids[0]).count() == 2
    db.close()
