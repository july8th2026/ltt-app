"""H30 — structured process log và lifecycle event tự động cho mọi app."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'obs.db').as_posix()}")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); session = next(gen)
    try:
        yield session
    finally:
        session.close(); dbmod.reset_engine()


def _submit(db):
    from platform_core.jobs import submit
    job = submit(db, user_id="u1", app_slug="sample", job_type="sample.run",
                 params={"prompt": "private"})
    db.commit()
    return job


def test_ctx_event_redacts_and_is_internal(db):
    from platform_core.job_runner import JobContext
    from platform_core.models import JobEvent

    job = _submit(db)
    assert JobContext(job.id).event(
        "provider_submitted", "Đã gửi provider", details={
            "provider_job_id": "p-123", "token": "secret-value",
            "email": "person@example.com",
        }, event_key="provider-submitted")
    db.expire_all()
    event = db.query(JobEvent).filter_by(
        job_id=job.id, event_code="provider_submitted").one()
    assert event.visibility == "internal"
    raw = str(event.details)
    assert "secret-value" not in raw and "person@example.com" not in raw
    assert event.details["provider_job_id"] == "p-123"


def test_runner_tu_dong_ghi_execution_lifecycle(db, monkeypatch):
    import platform_core.job_runner as runner
    from platform_core.models import JobEvent

    def handler(_params, ctx):
        ctx.progress(50, "đang chạy")
        return {"artifact_key": "opaque/key", "credit_cost": 3}

    monkeypatch.setattr(runner.jobq, "resolve_handler", lambda _kind: handler)
    job = _submit(db)
    assert runner._chay_mot_job("worker-test") is True
    db.expire_all()
    codes = [row.event_code for row in db.query(JobEvent).filter_by(
        job_id=job.id).order_by(JobEvent.sequence)]
    assert codes == [
        "submitted", "claimed", "started", "admitted", "execution_started",
        "progress", "execution_completed", "completed",
    ]
    admitted = db.query(JobEvent).filter_by(
        job_id=job.id, event_code="admitted").one()
    assert admitted.visibility == "internal"
    assert admitted.details["admission_delay_ms"] >= 0
    completed = db.query(JobEvent).filter_by(
        job_id=job.id, event_code="execution_completed").one()
    assert completed.visibility == "internal"
    assert completed.details["duration_ms"] >= 0
    assert completed.details["result_keys"] == ["artifact_key", "credit_cost"]
    assert completed.details["reported_credit_cost"] == 3


def test_process_log_jsonl_redaction_and_age_cleanup(tmp_path, monkeypatch):
    from platform_core.observability import cleanup_rotated_logs, configure_logging

    log_path = configure_logging(component="test", env={
        "LTT_LOGS_DIR": str(tmp_path), "LTT_LOG_MAX_BYTES": "65536",
        "LTT_LOG_BACKUP_COUNT": "2", "LTT_LOG_RETENTION_DAYS": "30",
    })
    assert log_path and log_path.endswith("ltt-test.jsonl")
    logging.getLogger("obs-test").warning(
        "email=person@example.com token=abc123")
    for handler in logging.getLogger().handlers:
        handler.flush()
    row = json.loads((tmp_path / "ltt-test.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert "person@example.com" not in row["message"]
    assert "abc123" not in row["message"]

    old = tmp_path / "ltt-test.jsonl.1"
    old.write_text("old\n", encoding="utf-8")
    stamp = (datetime.now(timezone.utc) - timedelta(days=31)).timestamp()
    import os
    os.utime(old, (stamp, stamp))
    assert cleanup_rotated_logs(logs_dir=str(tmp_path), retention_days=30) == 1
    assert not old.exists()
