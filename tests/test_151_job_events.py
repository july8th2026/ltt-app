"""H26.3 — timeline job, redaction, retention và lineage dùng chung."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'events.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


def _job(db, user_id="u1"):
    from platform_core.jobs import submit
    job = submit(db, user_id=user_id, app_slug="sample", job_type="sample.run",
                 params={"prompt": "không được vào event"})
    db.commit()
    return job


def test_lifecycle_co_sequence_va_customer_timeline_khong_lo_internal(db):
    from platform_core import job_events
    from platform_core.jobs import claim, complete, set_progress
    from platform_core.models import JobEvent

    job = _job(db)
    running = claim(db, worker_id="worker-private")
    set_progress(db, running, 45, "Đang dựng kết quả")
    complete(db, running, {"video_key": "owned/out.mp4"})
    db.commit()

    all_events = db.query(JobEvent).filter_by(job_id=job.id).order_by(JobEvent.sequence).all()
    assert [event.sequence for event in all_events] == list(range(1, len(all_events) + 1))
    assert [event.event_code for event in all_events] == [
        "submitted", "claimed", "started", "progress", "completed"]
    customer = job_events.timeline(db, job.id)
    assert [event.event_code for event in customer] == [
        "submitted", "started", "progress", "completed"]
    assert all("worker-private" not in str(event.details) for event in customer)


def test_event_idempotent_va_redact_secret_pii(db):
    from platform_core import job_events
    from platform_core.models import JobEvent

    job = _job(db)
    first = job_events.append(
        db, job, "provider_debug", visibility=job_events.INTERNAL,
        details={"email": "person@example.com", "error": "token=abc123",
                 "nested": {"password": "mat-khau"}}, event_key="provider-once")
    again = job_events.append(
        db, job, "provider_debug", visibility=job_events.INTERNAL,
        details={"error": "không được ghi lần hai"}, event_key="provider-once")
    db.commit()

    assert first.id == again.id
    assert db.query(JobEvent).filter_by(job_id=job.id, event_code="provider_debug").count() == 1
    stored = str(first.details)
    assert "person@example.com" not in stored
    assert "abc123" not in stored
    assert "mat-khau" not in stored


def test_customer_metadata_deny_by_default(db):
    from platform_core import job_events

    job = _job(db)
    event = job_events.append(
        db, job, "progress", public_message="an toàn", details={
            "percent": 20, "prompt": "bí mật", "provider_payload": {"x": 1},
            "unknown_debug": "không hiện",
        })
    db.commit()
    assert event.details == {"percent": 20}


def test_retention_customer_365_internal_30_tach_biet(db):
    from platform_core import job_events
    from platform_core.models import JobEvent

    now = datetime.now(timezone.utc)
    job = _job(db)
    public = job_events.append(db, job, "old_public", public_message="cũ")
    internal = job_events.append(db, job, "old_internal", visibility=job_events.INTERNAL)
    recent = job_events.append(db, job, "recent", public_message="mới")
    public.created_at = now - timedelta(days=366)
    internal.created_at = now - timedelta(days=31)
    recent.created_at = now - timedelta(days=2)
    db.commit()

    removed = job_events.purge_expired(db, now=now)
    db.commit()
    assert removed == {"customer": 1, "internal": 1}
    assert [row.event_code for row in db.query(JobEvent).all()] == ["submitted", "recent"]


def test_retention_report_va_purge_job_terminal_khong_xoa_ledger(db):
    from platform_core import credit, job_events
    from platform_core.models import JOB_DONE, JOB_RUNNING, CreditEntry, Job, JobEvent
    from platform_core.users import tao_nguoi_dung

    now = datetime.now(timezone.utc)
    user = tao_nguoi_dung(
        db, email="retention@example.com", password="matkhau-tot-12",
        is_verified=True)
    old_done = _job(db, user.id)
    old_done.status = JOB_DONE
    old_done.created_at = now - timedelta(days=366)
    old_done.finished_at = now - timedelta(days=366)
    old_running = _job(db, user.id)
    old_running.status = JOB_RUNNING
    old_running.created_at = now - timedelta(days=400)
    credit.cap_tay(db, user.id, 7, by="retention-test")
    credit.giu_cho(db, user.id, 3, old_done.id)
    for event in db.query(JobEvent).filter_by(job_id=old_done.id).all():
        event.created_at = now - timedelta(days=366)
    db.commit()

    report = job_events.retention_report(db, now=now)
    assert report["customer_events_due"] >= 1
    assert report["terminal_jobs_due"] == 1
    assert report["active_jobs_older_than_policy"] == 1

    removed = job_events.purge_expired_jobs(db, now=now)
    db.commit()
    db.expire_all()
    assert removed == 1
    assert db.get(Job, old_done.id) is None
    assert db.get(Job, old_running.id) is not None
    assert db.query(CreditEntry).filter_by(job_id=old_done.id).count() == 1


def test_support_export_loc_payload_va_ledger(db):
    from platform_core import credit, job_events, job_history
    from platform_core.users import tao_nguoi_dung

    user = tao_nguoi_dung(
        db, email="support@example.com", password="matkhau-tot-12",
        is_verified=True)
    job = _job(db, user.id)
    credit.cap_tay(db, user.id, 9, by="support-test")
    credit.giu_cho(db, user.id, 4, job.id)
    job_events.append(
        db, job, "provider_debug", visibility=job_events.INTERNAL,
        details={"error": "token=secret-value", "prompt": "private prompt"})
    db.commit()

    payload = job_history.support_payload(db, job)
    raw = str(payload)
    assert "params" not in payload["job"]
    assert "result" not in payload["job"]
    assert "error" not in payload["job"]
    assert "secret-value" not in raw and "private prompt" not in raw
    assert payload["credit"]["hold"]["delta"] == -4


def test_retry_lineage_duoc_luu_truc_tiep_tren_job(db):
    from platform_core.jobs import submit

    original = _job(db)
    retried = submit(db, user_id="u1", app_slug="sample", job_type="sample.run",
                     params={}, retry_of_id=original.id,
                     correlation_id="12345678-1234-1234-1234-123456789012")
    db.commit()
    assert retried.retry_of_id == original.id
    assert retried.correlation_id == "12345678-1234-1234-1234-123456789012"


def test_metrics_co_success_queue_runtime_retry_refund_va_stale(db):
    from platform_core import job_events, job_metrics
    from platform_core.jobs import claim, complete

    job = _job(db)
    running = claim(db, worker_id="metrics")
    complete(db, running, {})
    job_events.append(db, running, "credit_refunded", public_message="Đã hoàn",
                      event_key="metric-refund")
    db.commit()

    metrics = job_metrics.snapshot(db)
    assert metrics["jobs_total"] == 1
    assert metrics["success_rate"] == 1.0
    assert metrics["queue_wait_p50_s"] >= 0
    assert metrics["runtime_p95_s"] >= 0
    assert metrics["refund_total"] == 1
    assert metrics["stale_jobs"] == 0
    assert job_metrics.alerts({**metrics, "stale_jobs": 1}) == [
        {"code": "job_stale", "level": "error"}]


def test_history_contract_cursor_khong_lo_payload(db):
    from platform_core import job_history
    from platform_core.jobs import submit

    ids = []
    for index in range(3):
        job = submit(db, user_id="u-history", app_slug="sample",
                     job_type="sample.run", params={"secret": index})
        job.result = {"provider_payload": "không được lộ"}
        ids.append(job.id)
    db.commit()

    first, cursor = job_history.list_owned(db, "u-history", limit=2)
    second, next_cursor = job_history.list_owned(
        db, "u-history", cursor=cursor, limit=2)
    assert len(first) == 2 and len(second) == 1 and next_cursor == ""
    assert {row.id for row in first + second} == set(ids)
    payload = job_history.customer_payload(db, first[0], with_events=True)
    assert "params" not in payload and "result" not in payload and "error" not in payload
    assert payload["events"][0]["code"] == "submitted"
