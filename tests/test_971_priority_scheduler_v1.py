"""H44 — Scheduler V1: strict priority, fairness, queue truth and ETA."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'scheduler.db').as_posix()}")
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


def _submit(db, *, user: str, priority: str = "external",
            resource: str = "gpu", job_type: str = "sample.run",
            slots: int = 0):
    from platform_core.jobs import submit

    job = submit(
        db, user_id=user, app_slug="sample", job_type=job_type, params={},
        admission_resource=resource, admission_slots=slots,
        origin="internal_runtime" if priority == "internal" else "public_api",
        priority_class=priority,
    )
    db.commit()
    return job


def test_metadata_thieu_hoac_la_deu_fail_closed_external(db):
    from platform_core.job_scheduler import normalize_origin, normalize_priority
    from platform_core.jobs import submit

    legacy = submit(db, user_id="legacy", app_slug="sample",
                    job_type="sample.run", params={})
    strange = _submit(db, user="strange", priority="super-admin")
    assert (legacy.origin, legacy.priority_class) == ("unknown", "external")
    assert (strange.origin, strange.priority_class) == ("public_api", "external")
    assert normalize_origin("forged") == "unknown"
    assert normalize_priority(None) == normalize_priority("forged") == "external"


def test_chi_trusted_scope_moi_nang_job_mac_dinh_len_internal(db):
    from platform_core.job_ingress import current, trusted_scope
    from platform_core.jobs import submit

    assert current() == ("unknown", "external")
    with trusted_scope("web", "internal"):
        web_job = submit(db, user_id="web-user", app_slug="sample",
                         job_type="sample.run", params={})
        assert (web_job.origin, web_job.priority_class) == ("web", "internal")
    assert current() == ("unknown", "external")


def test_http_middleware_phan_loai_web_va_public_api_tu_path_tin_cay():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from platform_core.job_ingress import current
    from server.job_ingress_middleware import JobIngressMiddleware

    app = FastAPI()
    app.add_middleware(JobIngressMiddleware)

    @app.get("/{path:path}")
    def inspect_context(path: str):
        return {"classification": current(), "path": path}

    with TestClient(app) as client:
        assert client.get("/taoanh/api/run").json()["classification"] == [
            "web", "internal"]
        assert client.get("/api/v1/jobs").json()["classification"] == [
            "public_api", "external"]


def test_internal_den_sau_van_duoc_claim_truoc_external(db):
    from platform_core import job_metrics
    from platform_core.jobs import claim

    external = _submit(db, user="customer", priority="external")
    internal = _submit(db, user="product", priority="internal")
    claimed = claim(db, worker_id="w-priority")
    db.commit()
    assert claimed.id == internal.id
    assert external.status == "queued"
    metrics = job_metrics.snapshot(db)
    assert metrics["scheduler_priority_override_total"] == 1
    assert metrics["lifecycle_by_priority"]["internal"]["started"] == 1
    assert metrics["queue_wait_s_by_resource_priority"]["gpu"]["external"][
        "p95"] >= 0


def test_external_da_aging_khong_vuot_qua_internal(db):
    from platform_core.jobs import FAIR_AGING, claim

    external = _submit(db, user="customer", priority="external")
    external.created_at = datetime.now(timezone.utc) - FAIR_AGING - timedelta(hours=1)
    db.commit()
    internal = _submit(db, user="product", priority="internal")
    assert claim(db, worker_id="w-aged").id == internal.id


def test_fair_share_trong_cung_priority_cho_account_khac_mot_luot(db):
    from platform_core.jobs import claim, complete

    first_a = _submit(db, user="account-a", priority="internal")
    second_a = _submit(db, user="account-a", priority="internal")
    first_b = _submit(db, user="account-b", priority="internal")

    claimed_a = claim(db, worker_id="w1")
    assert claimed_a.id == first_a.id
    complete(db, claimed_a, {})
    db.commit()
    assert claim(db, worker_id="w2").id == first_b.id
    db.commit()
    assert second_a.status == "queued"
    from platform_core import job_metrics
    assert job_metrics.snapshot(db)["scheduler_fair_rotation_total"] == 1


def test_priority_khong_preempt_job_dang_chay(db):
    from platform_core.jobs import claim

    external = _submit(db, user="customer", priority="external")
    assert claim(db, worker_id="w-external").id == external.id
    db.commit()
    internal = _submit(db, user="product", priority="internal")

    assert external.status == "running"
    assert external.worker_id == "w-external"
    assert claim(db, worker_id="w-internal").id == internal.id
    assert external.status == "running"


def test_external_chay_sau_khi_internal_da_duoc_rut_can(db):
    from platform_core.jobs import claim, complete

    external = _submit(db, user="customer", priority="external")
    internal = _submit(db, user="product", priority="internal")
    first = claim(db, worker_id="w1")
    assert first.id == internal.id
    complete(db, first, {})
    db.commit()
    assert claim(db, worker_id="w2").id == external.id


def test_snapshot_dong_tang_vi_tri_khi_internal_moi_den(db):
    from platform_core.job_scheduler import queue_snapshot

    external = _submit(db, user="customer", priority="external")
    before = queue_snapshot(db, external)
    internal = _submit(db, user="product", priority="internal")
    after = queue_snapshot(db, external)
    internal_view = queue_snapshot(db, internal)

    assert before["position"] == 1
    assert after["position"] == 2 and after["higher_priority_ahead"] == 1
    assert after["same_priority_ahead"] == 0
    assert internal_view["position"] == 1


def test_snapshot_chi_dem_job_cung_resource(db):
    from platform_core.job_scheduler import queue_snapshot

    gpu_external = _submit(db, user="customer", priority="external", resource="gpu")
    _submit(db, user="product", priority="internal", resource="llm_remote")
    view = queue_snapshot(db, gpu_external)
    assert view["position"] == 1 and view["jobs_ahead"] == 0


def test_snapshot_tach_job_chua_den_han_khoi_job_co_the_claim(db):
    from platform_core.job_scheduler import queue_snapshot

    future_internal = _submit(db, user="product", priority="internal")
    future_internal.next_run_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()
    external = _submit(db, user="customer", priority="external")

    future_view = queue_snapshot(db, future_internal)
    external_view = queue_snapshot(db, external)
    assert future_view["eligible"] is False and future_view["retry_at"]
    assert external_view["eligible"] is True and external_view["position"] == 1


def test_eta_dung_median_lich_su_cho_job_dung_truoc(db):
    from platform_core.job_scheduler import queue_snapshot
    from platform_core.models import JOB_DONE, Job

    now = datetime.now(timezone.utc)
    for seconds in (10, 20, 30):
        db.add(Job(
            user_id=f"history-{seconds}", app_slug="sample",
            job_type="sample.run", params={}, status=JOB_DONE,
            admission_resource="gpu", admission_slots=1,
            started_at=now - timedelta(seconds=seconds),
            admitted_at=now - timedelta(seconds=seconds), finished_at=now,
        ))
    db.commit()
    _submit(db, user="ahead", resource="gpu", slots=1)
    subject = _submit(db, user="subject", resource="gpu", slots=1)
    view = queue_snapshot(db, subject, now=now)
    assert view["position"] == 2
    assert view["estimated_wait_seconds"] == 20.0
    assert view["estimated_start_at"] is not None


def test_eta_khong_biet_thi_tra_null_thay_vi_bia_so(db):
    from platform_core.job_scheduler import queue_snapshot

    _submit(db, user="ahead", job_type="never-measured")
    subject = _submit(db, user="subject")
    view = queue_snapshot(db, subject)
    assert view["position"] == 2
    assert view["estimated_wait_seconds"] is None
    assert view["estimated_start_at"] is None


def test_cancel_loai_job_khoi_ranking_va_canh_bao_external_starvation(db):
    from platform_core import job_metrics
    from platform_core.job_scheduler import queue_snapshot
    from platform_core.jobs import cancel

    old = _submit(db, user="old", priority="external")
    old.created_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    subject = _submit(db, user="subject", priority="external")
    db.commit()
    assert queue_snapshot(db, subject)["position"] == 2
    assert cancel(db, old)
    db.commit()
    assert queue_snapshot(db, subject)["position"] == 1

    second_old = _submit(db, user="waiting", priority="external")
    second_old.created_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db.commit()
    metrics = job_metrics.snapshot(db)
    assert metrics["queue_depth_by_resource_priority"]["gpu"]["external"] == 2
    assert any(alert["code"] == "external_queue_starvation"
               for alert in job_metrics.alerts(metrics))


def test_snapshot_1000_job_khong_bac_hai_va_van_dung(db):
    """Ngưỡng rộng chỉ bắt hồi quy độ phức tạp, không chấm tốc độ máy."""
    import time
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import insert, select

    from platform_core.job_scheduler import queue_snapshot
    from platform_core.models import JOB_QUEUED, Job

    now = datetime.now(timezone.utc)
    rows = []
    for index in range(1000):
        rows.append({
            "user_id": f"load-{index % 100}", "app_slug": "sample",
            "job_type": "sample.run", "params": {}, "status": JOB_QUEUED,
            "origin": "public_api", "priority_class": "external",
            "admission_resource": "load", "admission_slots": 4,
            "created_at": now - timedelta(milliseconds=1000 - index),
            "next_run_at": now - timedelta(seconds=1),
        })
    db.execute(insert(Job), rows)
    db.commit()
    subject = db.execute(select(Job).where(
        Job.admission_resource == "load").order_by(
            Job.created_at.desc())).scalars().first()
    assert subject is not None
    started = time.monotonic()
    view = queue_snapshot(db, subject, now=now)
    elapsed = time.monotonic() - started
    assert view["position"] == 1000
    assert elapsed < 5.0, f"snapshot 1k mat {elapsed:.3f}s: nghi O(n^2)"


def test_priority_va_origin_song_sot_qua_khoi_dong_lai(db):
    import platform_core.db as dbmod
    from platform_core.models import Job

    queued = _submit(db, user="durable", priority="internal")
    job_id = queued.id
    db.close()
    dbmod.reset_engine()

    reopened_gen = dbmod.get_session()
    reopened = next(reopened_gen)
    try:
        restored = reopened.get(Job, job_id)
        assert restored is not None
        assert (restored.origin, restored.priority_class) == (
            "internal_runtime", "internal")
    finally:
        reopened.close()
