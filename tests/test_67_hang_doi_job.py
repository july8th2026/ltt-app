"""
H2 — hàng đợi job (Q26: bảng jobs tự quản).

Chạy trên SQLite tạm cho logic; concurrency thật (SKIP LOCKED) nghiệm thu riêng
trên PostgreSQL. SQLite bỏ qua clause FOR UPDATE nên vẫn chạy được phần logic
đơn luồng ở đây.

Trọng tâm:
- dedupe chặn tạo job trùng khi job cũ còn chạy (chống double-submit / F5);
- claim chuyển job sang running, tôn trọng next_run_at;
- fail retry có giới hạn rồi mới thành error;
- reclaim_orphans nhặt lại job của worker đã chết;
- chạy trọn một job demo end-to-end qua worker loop.
"""
from __future__ import annotations

from datetime import timedelta

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'j.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


def _submit(db, **kw):
    from platform_core.jobs import submit
    kw.setdefault("user_id", "u1")
    kw.setdefault("app_slug", "demo")
    kw.setdefault("job_type", "demo.reverse")
    kw.setdefault("params", {"text": "abc"})
    j = submit(db, **kw)
    db.commit()
    return j


# ── Nộp + dedupe ──────────────────────────────────────────────────────────────

def test_submit_tao_job_queued(db):
    from platform_core.models import JOB_QUEUED
    j = _submit(db)
    assert j.id and j.status == JOB_QUEUED and j.progress == 0


def test_dedupe_tra_lai_job_cu_khi_con_chay(db):
    j1 = _submit(db, dedupe_key="k1")
    j2 = _submit(db, dedupe_key="k1")
    assert j1.id == j2.id, "cung dedupe_key khi job cu con chay -> tra lai job cu"


def test_dedupe_khong_anh_huong_khi_job_cu_da_xong(db):
    from platform_core.jobs import complete
    j1 = _submit(db, dedupe_key="k2")
    complete(db, j1, {"ok": True}); db.commit()
    j2 = _submit(db, dedupe_key="k2")
    assert j1.id != j2.id, "job cu da xong -> dedupe cho tao job moi"


def test_khong_dedupe_khi_khong_co_key(db):
    j1 = _submit(db)
    j2 = _submit(db)
    assert j1.id != j2.id


# ── Claim ─────────────────────────────────────────────────────────────────────

def test_claim_chuyen_running_va_gan_worker(db):
    from platform_core.jobs import claim
    from platform_core.models import JOB_RUNNING
    _submit(db)
    j = claim(db, worker_id="w1"); db.commit()
    assert j is not None and j.status == JOB_RUNNING
    assert j.worker_id == "w1" and j.started_at is not None


def test_claim_tra_none_khi_trong(db):
    from platform_core.jobs import claim
    assert claim(db, worker_id="w1") is None


def test_claim_khong_nhat_job_hen_tuong_lai(db):
    from platform_core.jobs import claim, _bay_gio
    j = _submit(db)
    j.next_run_at = _bay_gio() + timedelta(hours=1)  # hen sau
    db.commit()
    assert claim(db, worker_id="w1") is None, "job hen tuong lai chua duoc nhat"


def test_cancel_chi_huy_job_chua_ket_thuc_va_khong_the_claim_lai(db):
    """Job bị hủy không được worker nhặt lại; lời gọi lặp là idempotent."""
    from platform_core.jobs import cancel, claim
    from platform_core.models import JOB_CANCELLED
    j = _submit(db)
    assert cancel(db, j) is True
    db.commit()
    assert j.status == JOB_CANCELLED and j.finished_at is not None
    assert cancel(db, j) is False
    assert claim(db, worker_id="w1") is None


def test_worker_khong_fail_hoac_retry_job_da_cancel(db, monkeypatch):
    """Race cancel-vs-handler exception must preserve cancelled permanently."""
    import platform_core.db as dbmod
    from platform_core import jobs as jobq
    from platform_core.job_runner import _chay_mot_job
    from platform_core.models import JOB_CANCELLED, Job

    queued = _submit(db, max_attempts=3)
    job_id = queued.id

    def handler(_params, _ctx):
        gen = dbmod.get_session(); other = next(gen)
        try:
            running = other.get(Job, job_id)
            assert jobq.cancel(other, running)
            other.commit()
        finally:
            try: next(gen)
            except StopIteration: pass
        raise RuntimeError("subprocess stopped after cancel")

    monkeypatch.setattr(jobq, "resolve_handler", lambda _job_type: handler)
    assert _chay_mot_job("w-cancel-race") is True
    db.expire_all()
    result = db.get(Job, job_id)
    assert result.status == JOB_CANCELLED
    assert result.attempts == 0 and result.next_run_at is not None


def test_job_context_bao_cancel_o_checkpoint(db):
    from platform_core import jobs as jobq
    from platform_core.job_runner import JobCancelled, JobContext
    j = _submit(db)
    assert jobq.cancel(db, j); db.commit()
    ctx = JobContext(j.id)
    assert ctx.is_cancelled() is True
    with pytest.raises(JobCancelled):
        ctx.progress(50, "khong duoc ghi de trang thai cancel")


# ── Fail / retry ──────────────────────────────────────────────────────────────

def test_fail_con_luot_thi_hen_chay_lai(db):
    from platform_core.jobs import claim, fail
    from platform_core.models import JOB_QUEUED
    _submit(db, max_attempts=3)
    j = claim(db, worker_id="w1"); db.commit()
    fail(db, j, "loi tam thoi"); db.commit()
    assert j.status == JOB_QUEUED and j.attempts == 1
    assert j.worker_id == "", "hen chay lai thi nha worker cu"


def test_fail_het_luot_thi_thanh_error(db):
    from platform_core.jobs import claim, fail, _bay_gio
    from platform_core.models import JOB_ERROR
    _submit(db, max_attempts=2)
    for _ in range(2):
        # ep next_run_at ve qua khu de claim lai duoc ngay
        from platform_core.models import Job
        for job in db.query(Job).all():
            job.next_run_at = _bay_gio() - timedelta(seconds=1)
        db.commit()
        j = claim(db, worker_id="w1"); db.commit()
        assert j is not None
        fail(db, j, "loi"); db.commit()
    assert j.status == JOB_ERROR and j.attempts == 2
    assert j.finished_at is not None


def test_fail_loc_bi_mat_va_email_truoc_khi_ghi_db(db):
    """Lỗi provider là dữ liệu không tin cậy, không được biến Job thành kho secret."""
    from platform_core.jobs import claim, fail

    _submit(db, max_attempts=1)
    job = claim(db, worker_id="w-private"); db.commit()
    fail(db, job, "token=provider-secret customer@example.com"); db.commit()

    assert "provider-secret" not in job.error
    assert "customer@example.com" not in job.error
    assert "[Filtered]" in job.error


# ── Job mồ côi ────────────────────────────────────────────────────────────────

def test_reclaim_orphan_nhat_lai_job_worker_chet(db):
    from platform_core.jobs import claim, reclaim_orphans, _bay_gio
    from platform_core.models import JOB_QUEUED
    _submit(db, max_attempts=3)
    j = claim(db, worker_id="w-chet"); db.commit()
    # Gia lap worker chet: heartbeat lui ve qua khu xa.
    j.heartbeat_at = _bay_gio() - timedelta(minutes=10)
    db.commit()

    n = reclaim_orphans(db); db.commit()
    assert n == 1
    assert j.status == JOB_QUEUED and j.attempts == 1, \
        "job mo coi ve queued va tinh mot luot da tieu"


def test_reclaim_khong_dung_job_dang_song(db):
    from platform_core.jobs import claim, reclaim_orphans
    from platform_core.models import JOB_RUNNING
    _submit(db)
    j = claim(db, worker_id="w1"); db.commit()  # heartbeat = bay gio
    n = reclaim_orphans(db); db.commit()
    assert n == 0 and j.status == JOB_RUNNING


# ── Tra handler + chạy trọn một job ───────────────────────────────────────────

def test_resolve_handler_demo(db):
    from platform_core.jobs import resolve_handler
    h = resolve_handler("demo.reverse")
    assert callable(h)
    assert h({"text": "abc"}, None)["output"] == "cba"


def test_resolve_handler_job_type_la(db):
    from platform_core.jobs import JobError, resolve_handler
    with pytest.raises(JobError):
        resolve_handler("khong-ai-nhan.xyz")


def test_chay_tron_mot_job_demo(db, monkeypatch):
    """Worker loop nhặt job demo → chạy handler → complete với kết quả đúng."""
    from platform_core.job_runner import _chay_mot_job
    from platform_core.models import Job, JOB_DONE

    j = _submit(db, params={"text": "xin chao"})
    jid = j.id

    co_viec = _chay_mot_job("w-test")
    assert co_viec is True

    db.expire_all()
    job = db.get(Job, jid)
    assert job.status == JOB_DONE
    assert job.result["output"] == "oahc nix"   # "xin chao" dao nguoc
    assert job.progress == 100


def test_chay_job_loi_thi_fail(db):
    """Handler ném lỗi (text rỗng) → job fail, không complete."""
    from platform_core.job_runner import _chay_mot_job
    from platform_core.models import Job, JOB_QUEUED, JOB_ERROR

    j = _submit(db, params={"text": "   "}, max_attempts=1)  # demo nem loi khi rong
    jid = j.id
    _chay_mot_job("w-test")

    db.expire_all()
    job = db.get(Job, jid)
    assert job.status == JOB_ERROR       # max_attempts=1 -> that bai la error luon
    assert "error" not in (job.result or {}), "job loi khong duoc co result"
    assert job.error, "phai ghi ly do loi"


def test_worker_khong_ghi_bi_mat_cua_provider_vao_log(db, monkeypatch, caplog):
    """Trace phục vụ debug nhưng payload bí mật phải bị lọc trước khi log."""
    import logging
    from platform_core import jobs as jobq
    from platform_core.job_runner import _chay_mot_job

    _submit(db, max_attempts=1)

    def provider_down(_params, _ctx):
        raise RuntimeError("api_key=provider-secret customer@example.com")

    monkeypatch.setattr(jobq, "resolve_handler", lambda _job_type: provider_down)
    with caplog.at_level(logging.WARNING, logger="platform_core.job_runner"):
        assert _chay_mot_job("w-private-log") is True

    assert "provider-secret" not in caplog.text
    assert "customer@example.com" not in caplog.text
    assert "[Filtered]" in caplog.text
