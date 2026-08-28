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
