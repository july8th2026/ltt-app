"""Q114/H41.9 — admission cap/metadata không cần GPU thật."""
from __future__ import annotations

from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'admission.db').as_posix()}")
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


def _principal(user_id: str):
    return SimpleNamespace(user_id=user_id)


def test_ltt_llm_khai_resource_remote_mot_slot():
    from apps.ltt_llm.manifest import MANIFEST
    from platform_core.public_api.catalog import project_tool

    tool = MANIFEST.tools[0]
    assert tool.admission_resource == "llm_remote"
    assert tool.admission_slots == 1
    projected = project_tool(MANIFEST, tool)
    assert projected.admission_resource == "llm_remote"
    assert projected.admission_slots == 1
    assert "admission_resource" not in projected.to_public_dict()


def test_queue_config_co_global_cap_va_resource_cap():
    from platform_core.public_api.config import load_public_api_config

    config = load_public_api_config({
        "LTT_PUBLIC_API_GLOBAL_QUEUE_LIMIT": "7",
        "LTT_PUBLIC_API_RESOURCE_QUEUE_LIMITS": "llm_remote:3,gpu:5",
    })
    assert config.global_queue_limit == 7
    assert config.resource_queue_limits == {"llm_remote": 3, "gpu": 5}


def test_job_luu_resource_de_dem_cap_khong_suy_tu_slug(db):
    from platform_core import jobs

    row = jobs.submit(
        db, user_id="u1", app_slug="ten-app-khong-quan-trong",
        job_type="sample.run", params={}, admission_resource="llm_remote",
        admission_slots=1,
    )
    db.commit()
    assert row.admission_resource == "llm_remote"
    assert row.admission_slots == 1


def test_global_queue_cap_tu_choi_truoc_khi_insert_job_thu_hai(db):
    from platform_core import jobs
    from platform_core.public_api import limits
    from platform_core.public_api.config import load_public_api_config
    from platform_core.public_api.errors import ApiError

    config = load_public_api_config({
        "LTT_PUBLIC_API_GLOBAL_QUEUE_LIMIT": "1",
        "LTT_PUBLIC_API_MAX_ACTIVE_JOBS": "0",
    })
    limits.enforce_job_admission(
        db, principal=_principal("u1"), config=config,
        resource="llm_remote", class_slugs=())
    jobs.submit(
        db, user_id="u1", app_slug="a", job_type="a.run", params={},
        admission_resource="llm_remote", admission_slots=1)
    db.commit()

    with pytest.raises(ApiError) as caught:
        limits.enforce_job_admission(
            db, principal=_principal("u2"), config=config,
            resource="llm_remote", class_slugs=())
    assert caught.value.status == 429
    assert caught.value.extra["scope"] == "global_queue"
    from platform_core.models import Job
    assert db.query(Job).count() == 1


def test_resource_queue_cap_khong_chan_resource_khac(db):
    from platform_core import jobs
    from platform_core.public_api import limits
    from platform_core.public_api.config import load_public_api_config
    from platform_core.public_api.errors import ApiError

    config = load_public_api_config({
        "LTT_PUBLIC_API_GLOBAL_QUEUE_LIMIT": "20",
        "LTT_PUBLIC_API_MAX_ACTIVE_JOBS": "0",
        "LTT_PUBLIC_API_RESOURCE_QUEUE_LIMITS": "llm_remote:1",
    })
    jobs.submit(
        db, user_id="u1", app_slug="a", job_type="a.run", params={},
        admission_resource="llm_remote", admission_slots=1)
    db.commit()

    with pytest.raises(ApiError) as caught:
        limits.enforce_job_admission(
            db, principal=_principal("u2"), config=config,
            resource="llm_remote", class_slugs=())
    assert caught.value.extra["scope"] == "resource_queue"

    # Một tài nguyên độc lập không bị burst của LLM chặn.
    limits.enforce_job_admission(
        db, principal=_principal("u2"), config=config,
        resource="gpu", class_slugs=())


def test_execution_lease_mot_slot_gianh_nguyen_tu_va_nha_idempotent(db):
    from platform_core.llm import admission

    first = admission.acquire(
        db, resource="llm_remote", slots=1, user_id="u1",
        mode="sync", holder_id="request-1")
    assert first is not None
    db.commit()

    assert admission.acquire(
        db, resource="llm_remote", slots=1, user_id="u2",
        mode="stream", holder_id="request-2") is None
    db.rollback()

    admission.release(db, first.id)
    db.commit()
    second = admission.acquire(
        db, resource="llm_remote", slots=1, user_id="u2",
        mode="stream", holder_id="request-2")
    assert second is not None and second.slot == 0


def test_execution_lease_het_han_tu_duoc_thu_hoi(db):
    from platform_core.llm import admission

    old = admission.acquire(
        db, resource="llm_remote", slots=1, user_id="u1",
        mode="job", holder_id="job-1")
    assert old is not None
    old.heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    db.commit()

    replacement = admission.acquire(
        db, resource="llm_remote", slots=1, user_id="u2",
        mode="sync", holder_id="request-2",
        timeout=timedelta(minutes=20))
    assert replacement is not None
    assert replacement.id != old.id


def test_worker_hoan_job_khi_execution_slot_ban_khong_tinh_attempt(db, monkeypatch):
    from platform_core import jobs
    from platform_core.llm import admission
    import platform_core.job_runner as runner
    from platform_core.models import JOB_QUEUED, Job
    from tests.conftest import APP_THU_JOB, APP_THU_SLUG

    blocker = admission.acquire(
        db, resource="llm_remote", slots=1, user_id="u-khac",
        mode="sync", holder_id="request-khac")
    assert blocker is not None
    job = jobs.submit(
        db, user_id="u1", app_slug=APP_THU_SLUG, job_type=APP_THU_JOB,
        params={"text": "xin chao"}, admission_resource="llm_remote",
        admission_slots=1)
    job_id = job.id
    db.commit()

    ran = []
    monkeypatch.setattr(
        runner.jobq, "resolve_handler",
        lambda _job_type: lambda _params, _ctx: ran.append(True) or {"ok": True})
    assert runner._chay_mot_job("worker-1") is True

    db.expire_all()
    postponed = db.get(Job, job_id)
    assert postponed.status == JOB_QUEUED
    assert postponed.attempts == 0
    assert ran == []


def test_fair_claim_khong_de_burst_mot_account_doc_chiem_resource(db):
    from platform_core import jobs

    def submit(user_id: str):
        row = jobs.submit(
            db, user_id=user_id, app_slug="a", job_type="a.run", params={},
            admission_resource="llm_remote", admission_slots=1)
        db.commit()
        return row

    a1, a2, _a3 = submit("account-a"), submit("account-a"), submit("account-a")
    b1 = submit("account-b")

    first = jobs.claim(db, worker_id="w1")
    assert first.id == a1.id
    jobs.complete(db, first, {"ok": True})
    db.commit()

    second = jobs.claim(db, worker_id="w1")
    assert second.id == b1.id, "burst account A da doc chiem luot thu hai"
    jobs.complete(db, second, {"ok": True})
    db.commit()

    third = jobs.claim(db, worker_id="w1")
    assert third.id == a2.id, "FIFO trong chinh account A bi dao"


def test_aging_uu_tien_account_da_cho_qua_lau_truoc_account_moi(db):
    from platform_core import jobs

    old = datetime.now(timezone.utc) - timedelta(hours=1)
    a1 = jobs.submit(
        db, user_id="account-a", app_slug="a", job_type="a.run", params={},
        admission_resource="llm_remote", admission_slots=1)
    a2 = jobs.submit(
        db, user_id="account-a", app_slug="a", job_type="a.run", params={},
        admission_resource="llm_remote", admission_slots=1)
    a1.created_at = old
    a2.created_at = old + timedelta(seconds=1)
    db.commit()

    served = jobs.claim(db, worker_id="w1")
    assert served.id == a1.id
    jobs.complete(db, served, {"ok": True})
    db.commit()

    newcomer = jobs.submit(
        db, user_id="account-b", app_slug="a", job_type="a.run", params={},
        admission_resource="llm_remote", admission_slots=1)
    db.commit()
    selected = jobs.claim(db, worker_id="w1")
    assert selected.id == a2.id, (
        f"job da aging bi account moi vuot: selected={selected.id}, new={newcomer.id}")


def _submit_worker_job(db, *, max_attempts: int = 3):
    from platform_core import jobs
    from tests.conftest import APP_THU_JOB, APP_THU_SLUG
    row = jobs.submit(
        db, user_id="u1", app_slug=APP_THU_SLUG, job_type=APP_THU_JOB,
        params={"text": "xin chao"}, max_attempts=max_attempts,
        admission_resource="llm_remote", admission_slots=1)
    db.commit()
    return row


def test_timeout_sau_provider_dispatch_thanh_ambiguous_khong_retry(db, monkeypatch):
    import platform_core.job_runner as runner
    from platform_core.models import JOB_ERROR, Job

    def timed_out(_params, ctx):
        ctx.provider_dispatched()
        raise TimeoutError("mat ket noi sau khi gui request")

    monkeypatch.setattr(runner.jobq, "resolve_handler", lambda _jt: timed_out)
    job_id = _submit_worker_job(db).id
    runner._chay_mot_job("w1")

    db.expire_all()
    row = db.get(Job, job_id)
    assert row.status == JOB_ERROR
    assert row.provider_state == "ambiguous"
    assert row.attempts == 1


def test_429_sau_dispatch_chi_resource_wait_khong_ton_attempt(db, monkeypatch):
    import platform_core.job_runner as runner
    from platform_core.llm.cong_vlm import BanError
    from platform_core.models import JOB_QUEUED, Job

    def busy(_params, ctx):
        ctx.provider_dispatched()
        raise BanError("gateway busy", retry_after_s=17)

    monkeypatch.setattr(runner.jobq, "resolve_handler", lambda _jt: busy)
    job_id = _submit_worker_job(db).id
    runner._chay_mot_job("w1")

    db.expire_all()
    row = db.get(Job, job_id)
    assert row.status == JOB_QUEUED
    assert row.provider_state == "rejected"
    assert row.attempts == 0


def test_413_va_oom_sau_dispatch_la_terminal_khong_retry(db, monkeypatch):
    import platform_core.job_runner as runner
    from platform_core.llm.cong_vlm import ProviderOomError, VuotNganSachError
    from platform_core.models import JOB_ERROR, Job

    for error in (VuotNganSachError("qua ngu canh"), ProviderOomError("oom")):
        def rejected(_params, ctx, failure=error):
            ctx.provider_dispatched()
            raise failure

        monkeypatch.setattr(runner.jobq, "resolve_handler", lambda _jt: rejected)
        job_id = _submit_worker_job(db).id
        runner._chay_mot_job("w1")
        db.expire_all()
        row = db.get(Job, job_id)
        assert row.status == JOB_ERROR
        assert row.provider_state == "rejected"
        assert row.attempts == 1


def test_reclaim_worker_chet_sau_dispatch_khong_chay_lai_side_effect(db):
    from platform_core import jobs
    from platform_core.models import JOB_ERROR

    row = _submit_worker_job(db)
    claimed = jobs.claim(db, worker_id="w-dead")
    jobs.mark_provider_dispatched(db, claimed)
    claimed.heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db.commit()

    terminal = []
    assert jobs.reclaim_orphans(
        db, on_terminal=lambda _db, job: terminal.append(job.id)) == 1
    db.commit()
    assert row.status == JOB_ERROR
    assert row.provider_state == "ambiguous"
    assert row.attempts == 1
    assert jobs.reclaim_orphans(
        db, on_terminal=lambda _db, job: terminal.append(job.id)) == 0
    assert terminal == [row.id], "terminal callback/refund khong duoc lap lai"
