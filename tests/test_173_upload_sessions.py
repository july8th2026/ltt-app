"""R2 — staging upload, promote-after-hold, cleanup và reconcile."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import io

import pytest

from tests.conftest import bao_dam_user


MP4 = b"\x00\x00\x00\x18ftypisom" + b"x" * 52


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'uploads.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    from platform_core.storage import LocalStorage, set_storage
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    storage = LocalStorage(str(tmp_path / "files")); set_storage(storage)
    gen = dbmod.get_session(); db = next(gen)
    try:
        bao_dam_user(db, "u1"); db.commit()
        yield db, storage
    finally:
        db.close(); dbmod.reset_engine(); set_storage(None)


def _session(db, *, size=len(MP4), now=None):
    from platform_core import upload_sessions
    return upload_sessions.create(
        db, user_id="u1", app_slug="demo", filename="source.mp4",
        content_type="video/mp4", expected_size=size, max_size=1024,
        allowed_types=("video/mp4",), now=now,
    )


def test_confirm_kiem_actual_size_va_magic(env):
    from platform_core import upload_sessions
    db, storage = env
    session = _session(db)
    storage.put(session.staging_key, io.BytesIO(MP4), content_type="video/mp4")

    upload_sessions.confirm(db, storage, session)

    assert session.status == "ready"
    assert session.actual_size == len(MP4)


def test_confirm_tu_choi_file_gia_mao_va_size_sai(env):
    from platform_core import upload_sessions
    db, storage = env
    fake = _session(db)
    storage.put(fake.staging_key, io.BytesIO(b"not-a-video"), content_type="video/mp4")
    with pytest.raises(upload_sessions.UploadSessionError, match="Kích thước"):
        upload_sessions.confirm(db, storage, fake)

    wrong_magic = _session(db, size=16)
    storage.put(wrong_magic.staging_key, io.BytesIO(b"x" * 16), content_type="video/mp4")
    with pytest.raises(upload_sessions.UploadSessionError, match="định dạng"):
        upload_sessions.confirm(db, storage, wrong_magic)


def test_chi_promote_sau_hold_va_gan_job_owner(env):
    from platform_core import credit, upload_sessions
    from platform_core.job_submit import submit_with_credit
    from platform_core.models import Job
    db, storage = env
    session = _session(db)
    storage.put(session.staging_key, io.BytesIO(MP4), content_type="video/mp4")
    no_hold = Job(user_id="u1", app_slug="demo", job_type="demo.reverse",
                  params={"text": "x"})
    db.add(no_hold); db.flush()
    with pytest.raises(upload_sessions.UploadSessionError, match="credit"):
        upload_sessions.promote(
            db, storage, session, job=no_hold, final_key=f"demo/u1/{no_hold.id}/source.mp4")
    db.rollback()

    session = _session(db)
    storage.put(session.staging_key, io.BytesIO(MP4), content_type="video/mp4")
    credit.nap(db, "u1", 10)
    job = submit_with_credit(db, user_id="u1", app_slug="demo",
                             job_type="demo.reverse", params={"text": "x"})
    final = f"demo/u1/{job.id}/source.mp4"
    key = upload_sessions.promote(db, storage, session, job=job, final_key=final)
    db.commit()

    assert key == final and storage.exists(final)
    assert not storage.exists(session.staging_key)
    assert session.status == "promoted" and session.job_id == job.id


def test_quota_va_rate_fail_closed(env, monkeypatch):
    from platform_core import upload_sessions
    db, _storage = env
    monkeypatch.setattr(upload_sessions, "MAX_ACTIVE_SESSIONS", 1)
    _session(db)
    with pytest.raises(upload_sessions.UploadSessionError, match="giới hạn"):
        _session(db)


def test_sweeper_dry_run_delete_idempotent_va_reconcile(env):
    from platform_core import upload_sessions
    db, storage = env
    start = datetime(2026, 8, 12, tzinfo=timezone.utc)
    session = _session(db, now=start)
    storage.put(session.staging_key, io.BytesIO(MP4), content_type="video/mp4")
    db.commit()
    later = start + timedelta(hours=2)

    dry = upload_sessions.sweep(db, storage, now=later, dry_run=True)
    assert dry["due"] == 1 and dry["deleted"] == 0
    assert storage.exists(session.staging_key)

    done = upload_sessions.sweep(db, storage, now=later, dry_run=False)
    db.commit()
    again = upload_sessions.sweep(db, storage, now=later, dry_run=False)
    assert done["deleted"] == 1 and again["deleted"] == 0
    assert upload_sessions.reconcile(db, storage)["missing"] == 0


def test_compensate_tra_file_ve_staging_sau_db_rollback(env):
    from platform_core import credit, upload_sessions
    from platform_core.job_submit import submit_with_credit
    db, storage = env
    session = _session(db)
    storage.put(session.staging_key, io.BytesIO(MP4), content_type="video/mp4")
    credit.nap(db, "u1", 10)
    job = submit_with_credit(db, user_id="u1", app_slug="demo",
                             job_type="demo.reverse", params={"text": "x"})
    final = f"demo/u1/{job.id}/source.mp4"
    upload_sessions.promote(db, storage, session, job=job, final_key=final)

    # Giả lập commit CSDL thất bại sau khi object storage đã move thành công.
    db.rollback()
    assert upload_sessions.compensate(
        storage, [(session.staging_key, final, session.content_type)]) == 1
    assert storage.exists(session.staging_key) and not storage.exists(final)


def test_sweeper_bo_qua_input_cua_job_dang_chay(env):
    from platform_core import credit, upload_sessions
    from platform_core.job_submit import submit_with_credit
    from platform_core.models import JOB_RUNNING
    db, storage = env
    start = datetime(2026, 8, 12, tzinfo=timezone.utc)
    session = _session(db, now=start)
    storage.put(session.staging_key, io.BytesIO(MP4), content_type="video/mp4")
    credit.nap(db, "u1", 10)
    job = submit_with_credit(db, user_id="u1", app_slug="demo",
                             job_type="demo.reverse", params={"text": "x"})
    final = f"demo/u1/{job.id}/source.mp4"
    upload_sessions.promote(db, storage, session, job=job, final_key=final,
                            now=start)
    job.status = JOB_RUNNING
    db.commit()

    report = upload_sessions.sweep(
        db, storage, now=start + timedelta(days=31), dry_run=False)
    assert report["due"] == 0 and report["skipped_active"] == 1
    assert storage.exists(final)


def test_operator_report_khong_lo_storage_key_hay_filename(env, monkeypatch):
    from platform_core import upload_sessions
    from platform_core.storage import set_storage
    from tools import upload_lifecycle
    db, storage = env
    start = datetime(2026, 8, 12, tzinfo=timezone.utc)
    session = _session(db, now=start)
    storage.put(session.staging_key, io.BytesIO(MP4), content_type="video/mp4")
    db.commit(); db.close()
    monkeypatch.setattr(upload_sessions, "_now",
                        lambda: start + timedelta(hours=2))
    set_storage(storage)

    report = upload_lifecycle.run(apply=False, reconcile=True)

    rendered = str(report)
    assert report["due"] == 1 and report["deleted"] == 0
    assert "source.mp4" not in rendered and "staging/" not in rendered
