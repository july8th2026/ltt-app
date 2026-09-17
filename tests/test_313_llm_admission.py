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


def test_ltt_llm_khai_resource_theo_model_va_khong_lo_ra_khach():
    """Mỗi model công khai khai sức chứa CỦA NÓ, và bản chiếu mang theo.

    🔴 ĐỔI HÌNH DẠNG 11/09/2026 (dual-model 2.3). Bản cũ đòi
       `tool.admission_resource == "llm_remote"` — MỘT tên tài nguyên cho cả
       tool. Từ 2.3 `text.chat` phục vụ hai model trên hai card, nên bộ ba tĩnh
       ấy **rỗng** và câu hỏi đúng là *"model này giành tài nguyên nào"*.

       Điều phép kiểm ĐO vẫn nguyên: (a) app tự khai sức chứa, (b) số đọc từ
       `ngan_sach` chứ không gõ tay, (c) metadata vận hành không rò ra khách.
    """
    from apps.ltt_llm import ngan_sach
    from apps.ltt_llm.manifest import MANIFEST
    from platform_core.public_api.catalog import project_tool

    tool = MANIFEST.tools[0]
    projected = project_tool(MANIFEST, tool)
    cong_khai = str(projected.to_public_dict())
    for model, ten_tn, id_nb in (("ltt-3.8", ngan_sach.TAI_NGUYEN_38, "qwen38-api"),
                                 ("ltt-3.5", ngan_sach.TAI_NGUYEN_35, "qwen35-api")):
        for t in (tool, projected):
            suc = t.admission_cho(model)
            assert suc is not None and suc.resource == ten_tn
            assert suc.slots == ngan_sach.HO_SO[id_nb].seq_cap
        assert ten_tn not in cong_khai, f"ten tai nguyen {ten_tn} ro ra khach"
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
    """Thua cuộc đua giành suất ⇒ hoàn về hàng đợi, KHÔNG tiêu một lượt thử.

    ⚠️ BỐI CẢNH DỰNG ĐÃ VIẾT LẠI (Đợt 1, WF-202). Mệnh đề **không đổi**; thứ đổi
    là cách tái hiện nó.

    Bản cũ giữ sẵn suất **trước** khi worker nhặt job. Từ khi `jobs.claim()` biết
    sức chứa (`_con_cho_tai_nguyen`), bối cảnh đó không còn tới được nhánh này —
    job bị loại ngay ở câu truy vấn, worker không nhặt gì cả.

    ⭐ Nhưng nhánh này **vẫn phải sống**: bộ lọc trong `claim()` là **cơ hội,
    không phải khoá**. Hai worker vẫn có thể cùng thấy một suất trống rồi cùng
    nhặt hai job của cùng tài nguyên; kẻ thua phải hoàn job mà không mất lượt.

    ⇒ Bản mới **cướp suất ĐÚNG SAU khi claim trả về** — tái hiện chính cuộc đua
    thật, thay vì một tình huống nay đã bị chặn từ trước. Bản viết lại **khó
    xanh hơn** bản cũ: nó đòi cả `claim()` cho qua **lẫn** `defer_resource` xử lý
    đúng, chứ không chỉ đòi vế sau.
    """
    from platform_core import jobs
    from platform_core.llm import admission
    import platform_core.job_runner as runner
    from platform_core.models import JOB_QUEUED, Job
    from tests.conftest import APP_THU_JOB, APP_THU_SLUG

    job = jobs.submit(
        db, user_id="u1", app_slug=APP_THU_SLUG, job_type=APP_THU_JOB,
        params={"text": "xin chao"}, admission_resource="llm_remote",
        admission_slots=1)
    job_id = job.id
    db.commit()

    that_claim = runner.jobq.claim

    def _cuop_suat_ngay_sau_claim(db_worker, **kwargs):
        """Một tiến trình khác thắng suất giữa `claim()` và `acquire()`."""
        nhat = that_claim(db_worker, **kwargs)
        if nhat is not None:
            assert admission.acquire(
                db_worker, resource="llm_remote", slots=1, user_id="u-khac",
                mode="sync", holder_id="request-khac") is not None
        return nhat

    monkeypatch.setattr(runner.jobq, "claim", _cuop_suat_ngay_sau_claim)

    ran = []
    monkeypatch.setattr(
        runner.jobq, "resolve_handler",
        lambda _job_type: lambda _params, _ctx: ran.append(True) or {"ok": True})
    assert runner._chay_mot_job("worker-1") is True

    db.expire_all()
    postponed = db.get(Job, job_id)
    assert postponed.status == JOB_QUEUED
    assert postponed.attempts == 0
    assert postponed.admitted_at is None
    assert ran == []


def test_worker_ghi_admitted_at_chi_khi_sap_vao_handler(db, monkeypatch):
    import platform_core.job_runner as runner
    from platform_core.models import JOB_DONE, Job

    row = _submit_worker_job(db)
    monkeypatch.setattr(
        runner.jobq, "resolve_handler",
        lambda _job_type: lambda _params, _ctx: {"ok": True})
    assert runner._chay_mot_job("worker-admitted") is True

    db.expire_all()
    done = db.get(Job, row.id)
    assert done.status == JOB_DONE
    assert done.admitted_at is not None
    assert done.admitted_at >= done.created_at


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


def test_queue_snapshot_tai_dung_tu_db_sau_restart_khong_can_gpu(db):
    from platform_core import job_metrics, jobs
    import platform_core.db as dbmod
    from platform_core.llm import admission

    now = datetime.now(timezone.utc)
    running = jobs.submit(
        db, user_id="u-running", app_slug="a", job_type="a.run", params={},
        admission_resource="llm_remote", admission_slots=1)
    running.created_at = now - timedelta(seconds=12)
    db.commit()
    claimed = jobs.claim(db, worker_id="w-observe")
    jobs.mark_admitted(db, claimed, at=now)

    queued = jobs.submit(
        db, user_id="u-queued", app_slug="a", job_type="a.run", params={},
        admission_resource="llm_remote", admission_slots=1)
    queued.created_at = now - timedelta(seconds=25)
    lease = admission.acquire(
        db, resource="llm_remote", slots=1, user_id=running.user_id,
        mode="job", holder_id=running.id, job_id=running.id)
    stale = admission.acquire(
        db, resource="stale-resource", slots=1, user_id="u-stale",
        mode="sync", holder_id="stale-holder")
    stale.heartbeat_at = now - timedelta(minutes=30)
    db.commit()
    assert lease is not None and stale is not None

    before = job_metrics.snapshot(db, now=now)
    assert before["queue_depth"] == 1
    assert before["queue_depth_by_resource"] == {"llm_remote": 1}
    assert before["oldest_queued_age_s_by_resource"]["llm_remote"] >= 25
    assert before["active_execution_leases_by_resource"] == {"llm_remote": 1}
    assert before["expired_execution_lease_candidates"] == 1
    assert before["execution_lease_rows"] == 2
    assert before["admission_delay_p50_s"] == pytest.approx(12.0, abs=0.01)

    # Mô phỏng restart process: đóng session rồi đọc lại hoàn toàn từ row bền.
    db.close()
    dbmod.reset_engine()
    sessions = dbmod.get_session(); reopened = next(sessions)
    try:
        after = job_metrics.snapshot(reopened, now=now)
        for key in (
            "queue_depth", "queue_depth_by_resource",
            "oldest_queued_age_s_by_resource",
            "active_execution_leases_by_resource", "admission_delay_p50_s",
        ):
            assert after[key] == before[key]
    finally:
        sessions.close()


def test_execution_metric_flush_con_song_sau_reset_process(db):
    from platform_core.llm import admission
    from platform_core.public_api import metrics

    metrics.reset()
    first = admission.acquire(
        db, resource="llm_remote", slots=1, user_id="u1", mode="sync",
        holder_id="h1")
    assert first is not None
    assert admission.acquire(
        db, resource="llm_remote", slots=1, user_id="u2", mode="stream",
        holder_id="h2") is None
    assert admission.release(db, first.id)
    db.commit()
    assert metrics.flush(db, process="worker:q3-restart") >= 3
    db.commit()

    metrics.reset()
    durable = metrics.aggregate(db, hours=1)["counters"]
    assert durable[metrics.ADMISSION_ACQUIRED] == 1
    assert durable[metrics.ADMISSION_REJECTED] == 1
    assert durable[metrics.ADMISSION_RELEASED] == 1


def test_load_harness_chi_dung_db_mock_khong_goi_provider_gpu():
    from tools.bench_llm_admission import run

    report = run(accounts=3, total_jobs=12, polls=2)
    assert report["drained"] == 12
    assert report["queue_depth_end"] == 0
    assert report["provider_calls"] == 0
    assert report["gpu_reads"] == 0
    assert report["submitted_per_s"] > 0 and report["drained_per_s"] > 0


def test_queue_cap_rejection_metrics_co_ly_do_va_ben_qua_restart(db):
    from platform_core import jobs
    from platform_core.public_api import limits, metrics
    from platform_core.public_api.config import load_public_api_config
    from platform_core.public_api.errors import ApiError

    metrics.reset()
    config = load_public_api_config({
        "LTT_PUBLIC_API_GLOBAL_QUEUE_LIMIT": "1",
        "LTT_PUBLIC_API_MAX_ACTIVE_JOBS": "0",
    })
    jobs.submit(
        db, user_id="u1", app_slug="a", job_type="a.run", params={},
        admission_resource="llm_remote", admission_slots=1)
    db.commit()
    with pytest.raises(ApiError):
        limits.enforce_job_admission(
            db, principal=_principal("u2"), config=config,
            resource="llm_remote", class_slugs=())
    assert metrics.flush(db, process="web:q3-restart") == 2
    db.commit()

    metrics.reset()
    durable = metrics.aggregate(db, hours=1)["counters"]
    assert durable[metrics.ADMISSION_REJECTED] == 1
    assert durable["admission_rejected:global_queue"] == 1


def test_worker_restart_truoc_provider_khoi_phuc_job_tu_db(db):
    from platform_core import jobs
    import platform_core.db as dbmod
    from platform_core.models import JOB_QUEUED, Job

    row = _submit_worker_job(db)
    running = jobs.claim(db, worker_id="worker-before-restart")
    running.heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db.commit()
    job_id = row.id

    db.close()
    dbmod.reset_engine()
    sessions = dbmod.get_session(); reopened = next(sessions)
    try:
        assert jobs.reclaim_orphans(reopened) == 1
        reopened.commit()
        restored = reopened.get(Job, job_id)
        assert restored.status == JOB_QUEUED
        assert restored.attempts == 1
        assert restored.provider_state == ""
    finally:
        sessions.close()


# ── Đợt 1 · WF-202 · G11 — claim phải BIẾT sức chứa trước khi nhặt ───────────
#
# 🔴 VÌ SAO PHÉP KIỂM NÀY TỒN TẠI. Đo từ log worker production 28 ngày
#    (11/08 → 07/09/2026, `docs/architecture/workflow_v2_audit/01 §A.3`):
#
#        9.833 / 10.663 = 92,2 %  lượt nhặt `ltt_llm.chat` kết thúc bằng
#                                 "hoãn Ns: tài nguyên llm_remote đang bận"
#        11.929 lượt nhặt  →  868 job hoàn tất  =  13,7 lượt nhặt / 1 job xong
#
#    Nguyên nhân kiến trúc: `claim()` nhặt job TRƯỚC, rồi `job_runner` mới giành
#    `ExecutionLease` SAU. Thất bại thì `defer_resource` xếp lại. Với
#    `llm_remote` chỉ có MỘT suất, mọi job chat loại trừ nhau — nên đây là
#    trạng thái BÌNH THƯỜNG, không phải sự cố.
#
# ⛔ Đừng "sửa" bằng cách nới `ORPHAN_TIMEOUT` hay giảm giãn cách thử lại: cả hai
#    làm vòng quay dày hơn chứ không làm nó ngắn đi. Vế phải sửa là `claim()`
#    không được nhặt việc mà tài nguyên của nó chắc chắn không có chỗ.


def test_claim_bo_qua_job_co_tai_nguyen_da_het_suat(db):
    """Tài nguyên hết suất ⇒ job của nó KHÔNG được nhặt; job khác vẫn chạy."""
    from platform_core import jobs
    from platform_core.llm import admission

    # Một suất duy nhất của `llm_remote`, đã bị một tiến trình khác giữ.
    giu = admission.acquire(
        db, resource="llm_remote", slots=1, user_id="u_khac",
        mode="sync", holder_id="request-dang-chay")
    assert giu is not None

    # Job cần đúng tài nguyên đó.
    bi_chan = jobs.submit(
        db, user_id="u1", app_slug="ltt_llm", job_type="ltt_llm.chat",
        params={}, admission_resource="llm_remote", admission_slots=1)
    # Job không cần tài nguyên chia sẻ nào.
    tu_do = jobs.submit(
        db, user_id="u1", app_slug="thumbnail", job_type="thumbnail.render",
        params={})
    db.commit()

    nhat = jobs.claim(db, worker_id="w1")

    assert nhat is not None, "phải nhặt được job không vướng tài nguyên"
    assert nhat.id == tu_do.id, (
        f"nhặt nhầm job đang bị chặn tài nguyên: {nhat.job_type}")
    assert bi_chan.status == "queued"


def test_claim_nhat_lai_ngay_khi_suat_duoc_nha(db):
    """Nhả lease ⇒ job vừa bị bỏ qua phải được nhặt ở lượt kế tiếp."""
    from platform_core import jobs
    from platform_core.llm import admission

    giu = admission.acquire(
        db, resource="llm_remote", slots=1, user_id="u_khac",
        mode="sync", holder_id="request-dang-chay")
    assert giu is not None
    cho = jobs.submit(
        db, user_id="u1", app_slug="ltt_llm", job_type="ltt_llm.chat",
        params={}, admission_resource="llm_remote", admission_slots=1)
    db.commit()

    assert jobs.claim(db, worker_id="w1") is None

    admission.release(db, giu.id)
    db.commit()

    nhat = jobs.claim(db, worker_id="w1")
    assert nhat is not None and nhat.id == cho.id


def test_claim_bo_qua_lease_da_het_han_chu_khong_coi_la_ban(db):
    """Lease mồ côi KHÔNG được tính là đang chiếm suất."""
    from platform_core import jobs
    from platform_core.llm import admission

    cu = admission.acquire(
        db, resource="llm_remote", slots=1, user_id="u_khac",
        mode="job", holder_id="worker-da-chet")
    assert cu is not None
    cu.heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    cho = jobs.submit(
        db, user_id="u1", app_slug="ltt_llm", job_type="ltt_llm.chat",
        params={}, admission_resource="llm_remote", admission_slots=1)
    db.commit()

    nhat = jobs.claim(db, worker_id="w1")
    assert nhat is not None and nhat.id == cho.id


# ── Đợt 1 · WF-302 · G24 — khử trùng bằng RÀNG BUỘC, không bằng SELECT-rồi-INSERT
#
# 🔴 `jobs.submit()` chống double-submit bằng cách `SELECT` job cùng `dedupe_key`
#    chưa kết thúc, rồi mới `INSERT` nếu không thấy. Giữa hai câu đó là một **cửa
#    sổ tranh chấp thật**: hai request song song (F5, hai tab, script gọi API)
#    cùng thấy "chưa có", cùng chèn, và khách bị trừ tiền hai lần cho một yêu cầu.
#
# ⭐ Ba hệ độc lập đã hội tụ về cùng lời giải — cưỡng chế bằng CSDL, không bằng mã
#    cẩn thận: Activepieces `UNIQUE(flowRunId, stepName)` ·
#    n8n `UNIQUE(deduplicationKey) WHERE NOT NULL` ·
#    Trigger.dev `UNIQUE(environmentId, idempotencyKey)`.
#    (`docs/architecture/workflow_v2_audit/12_19 §16`)
#
# ⚠️ Chỉ mục phải là **BỘ PHẬN**: `dedupe_key` mặc định là chuỗi rỗng và phần lớn
#    job không dùng nó — một UNIQUE đầy đủ sẽ chặn mọi job thứ hai của một người.


def test_dedupe_key_trung_khi_dang_chay_bi_CSDL_tu_choi(db):
    """Hai job cùng `dedupe_key` chưa kết thúc ⇒ CSDL từ chối, không phải mã."""
    from sqlalchemy.exc import IntegrityError
    from platform_core.models import JOB_QUEUED, Job

    db.add(Job(user_id="u1", app_slug="a", job_type="t", params={},
               dedupe_key="cung-mot-yeu-cau", status=JOB_QUEUED))
    db.flush()

    db.add(Job(user_id="u1", app_slug="a", job_type="t", params={},
               dedupe_key="cung-mot-yeu-cau", status=JOB_QUEUED))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_dedupe_key_rong_khong_bi_chan(db):
    """Phần lớn job không dùng `dedupe_key` — chỉ mục bộ phận phải bỏ qua chúng."""
    from platform_core.models import JOB_QUEUED, Job

    for _ in range(3):
        db.add(Job(user_id="u1", app_slug="a", job_type="t", params={},
                   dedupe_key="", status=JOB_QUEUED))
    db.flush()
    db.commit()


def test_dedupe_key_dung_lai_duoc_sau_khi_job_cu_ket_thuc(db):
    """Xong rồi thì gửi lại cùng yêu cầu là hợp lệ — chỉ mục không được chặn."""
    from platform_core.models import JOB_DONE, JOB_QUEUED, Job

    db.add(Job(user_id="u1", app_slug="a", job_type="t", params={},
               dedupe_key="lam-lai", status=JOB_DONE))
    db.flush()
    db.add(Job(user_id="u1", app_slug="a", job_type="t", params={},
               dedupe_key="lam-lai", status=JOB_QUEUED))
    db.flush()
    db.commit()


def test_dedupe_key_trung_nhung_khac_nguoi_dung_thi_duoc(db):
    """Khử trùng theo TỪNG người dùng, không phải toàn hệ thống."""
    from platform_core.models import JOB_QUEUED, Job

    db.add(Job(user_id="u1", app_slug="a", job_type="t", params={},
               dedupe_key="trung-chuoi", status=JOB_QUEUED))
    db.add(Job(user_id="u2", app_slug="a", job_type="t", params={},
               dedupe_key="trung-chuoi", status=JOB_QUEUED))
    db.flush()
    db.commit()


# ---------------------------------------------------------------------------
# `co_job_dang_cho_tai_nguyen` — phân biệt "hết việc" với "tài nguyên bận"
#
# `claim()` trả `None` cho HAI nguyên nhân khác nhau kể từ khi bộ lọc suất được
# thêm vào: hàng đợi rỗng, và hàng đợi có việc nhưng tài nguyên chia sẻ đã hết
# suất. Vòng worker thật ngủ rồi thử lại nên nó không quan tâm; nhưng mọi bên
# gọi khác (`tools/h26_queue_soak.py`, `tools/bench_llm_admission.py`, các phép
# kiểm E2E) đều viết `if job is None: break` — tức chúng DỪNG ở một trạng thái
# chỉ là tạm.
#
# ⛔ Bản vá sai là bắt các bên đó ngủ mỗi khi thấy `None`: như vậy phạt cả những
#    lượt chạy tốt (hàng đợi rỗng thật) bằng đúng số giây ấy.
# ⇒ Bên gọi cần hỏi được theo Ý NGHĨA, không theo HÌNH DẠNG của giá trị trả về.
# ---------------------------------------------------------------------------


def test_co_job_dang_cho_tai_nguyen_bao_False_khi_hang_doi_trong(db):
    from platform_core import jobs

    assert jobs.co_job_dang_cho_tai_nguyen(db) is False


def test_co_job_dang_cho_tai_nguyen_bao_False_khi_job_khong_can_tai_nguyen(db):
    """Job claim được ngay ⇒ không phải "đang chờ tài nguyên"."""
    from platform_core import jobs

    jobs.submit(db, user_id="u1", app_slug="thumbnail",
                job_type="thumbnail.render", params={})
    db.commit()

    assert jobs.co_job_dang_cho_tai_nguyen(db) is False


def test_co_job_dang_cho_tai_nguyen_bao_True_khi_suat_da_het(db):
    """Đây là trạng thái mà `claim()` trả `None` NHƯNG việc vẫn còn đó."""
    from platform_core import jobs
    from platform_core.llm import admission

    giu = admission.acquire(
        db, resource="llm_remote", slots=1, user_id="u_khac",
        mode="sync", holder_id="request-dang-chay")
    assert giu is not None
    jobs.submit(db, user_id="u1", app_slug="ltt_llm", job_type="ltt_llm.chat",
                params={}, admission_resource="llm_remote", admission_slots=1)
    db.commit()

    assert jobs.claim(db, worker_id="w1") is None, "tiền đề: claim phải trả None"
    assert jobs.co_job_dang_cho_tai_nguyen(db) is True


def test_co_job_dang_cho_tai_nguyen_bao_False_ngay_sau_khi_nha_suat(db):
    from platform_core import jobs
    from platform_core.llm import admission

    giu = admission.acquire(
        db, resource="llm_remote", slots=1, user_id="u_khac",
        mode="sync", holder_id="request-dang-chay")
    jobs.submit(db, user_id="u1", app_slug="ltt_llm", job_type="ltt_llm.chat",
                params={}, admission_resource="llm_remote", admission_slots=1)
    db.commit()
    assert jobs.co_job_dang_cho_tai_nguyen(db) is True

    admission.release(db, giu.id)
    db.commit()

    assert jobs.co_job_dang_cho_tai_nguyen(db) is False, (
        "suất đã nhả ⇒ job nhặt được ngay, không còn là 'đang chờ'")


def test_co_job_dang_cho_tai_nguyen_bo_qua_lease_da_het_han(db):
    """Lease chết (heartbeat cũ) không được tính là đang giữ suất.

    Cùng một mệnh đề với `claim()`: `reclaim_orphans` sẽ dọn nó, nên coi nó
    là "đang bận" khiến hàng đợi đứng vĩnh viễn sau một worker chết.
    """
    from platform_core import jobs
    from platform_core.llm import admission
    from platform_core.llm.admission import ORPHAN_TIMEOUT
    from platform_core.models import ExecutionLease

    giu = admission.acquire(
        db, resource="llm_remote", slots=1, user_id="u_khac",
        mode="sync", holder_id="worker-da-chet")
    assert giu is not None
    lease = db.get(ExecutionLease, giu.id)
    lease.heartbeat_at = (
        datetime.now(timezone.utc).replace(tzinfo=None)
        - ORPHAN_TIMEOUT - timedelta(minutes=1))
    jobs.submit(db, user_id="u1", app_slug="ltt_llm", job_type="ltt_llm.chat",
                params={}, admission_resource="llm_remote", admission_slots=1)
    db.commit()

    assert jobs.co_job_dang_cho_tai_nguyen(db) is False


def test_co_job_dang_cho_tai_nguyen_ton_trong_capabilities(db):
    """Worker không phục vụ được app đó thì job đó không phải việc CỦA NÓ.

    Nếu bỏ qua `capabilities`, một worker chuyên GPU sẽ báo "đang chờ tài
    nguyên" vì một job của app nó không bao giờ được nhặt — và ngủ mãi.
    """
    from platform_core import jobs
    from platform_core.llm import admission

    admission.acquire(
        db, resource="llm_remote", slots=1, user_id="u_khac",
        mode="sync", holder_id="request-dang-chay")
    jobs.submit(db, user_id="u1", app_slug="ltt_llm", job_type="ltt_llm.chat",
                params={}, admission_resource="llm_remote", admission_slots=1)
    db.commit()

    assert jobs.co_job_dang_cho_tai_nguyen(db, capabilities={"api"}) is True
    assert jobs.co_job_dang_cho_tai_nguyen(db, capabilities=set()) is False
