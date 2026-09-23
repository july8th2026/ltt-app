"""Workflow V2 trên PostgreSQL thật: hai vòng động cơ song song, crash giữa chừng.

Chạy qua `tools/check_multiproc.py` (tự dựng CSDL scratch theo cây).
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

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
    """Hai luồng gọi `dong_co.mot_vong` THẬT SỰ cùng chạm vào cùng một hàng
    run tại cùng một thời điểm (review round 1, Important #2): riêng lệch
    khởi động luồng của hệ điều hành đủ để hai luồng không bao giờ thực sự
    tranh chấp — phép kiểm khi đó xanh dù khoá đúng hay sai, vì mỗi luồng chỉ
    thấy hàng đã bị dọn dẹp bởi luồng kia TỪ TRƯỚC (khoá không được thử thật).
    `threading.Barrier(2)` ép cả hai gọi `mot_vong` cùng một nhịp; sleep bên
    trong đoạn ĐÃ KHOÁ (`xu_ly_run`, chạy sau `FOR UPDATE SKIP LOCKED`, trước
    `commit`) cho vài lần gọi đầu kéo dài cửa sổ tranh chấp đủ để luồng thua
    thật sự chạm đúng hàng đang bị khoá — buộc `SKIP LOCKED` phải bỏ qua
    (không chờ), đúng cơ chế đang được kiểm.

    Also review round 1, Important #1: `threading.Thread` + `join()` nuốt mọi
    exception ném trong luồng (in traceback ra stderr rồi im lặng chết) — một
    lỗi thật trong `mot_vong` sẽ không làm phép kiểm này đỏ. Dùng
    `ThreadPoolExecutor` + `future.result()` để lỗi của luồng được ném lại ở
    luồng chính (sibling: `tests/test_214_multi_process_runtime.py:335` kiểm
    exit code của worker process vì cùng lý do)."""
    from platform_core.models import Job, WorkflowRun
    from platform_core.workflow import dong_co

    ids = _chuan_bi(pg, monkeypatch)

    goc_xu_ly = dong_co.xu_ly_run
    dem = {"n": 0}
    khoa_dem = threading.Lock()

    def _xu_ly_cham(db, rid, **kw):
        with khoa_dem:
            can_cham = dem["n"] < 6
            dem["n"] += 1
        if can_cham:
            time.sleep(0.08)   # keo dai cua so da khoa de ep tranh chap that
        return goc_xu_ly(db, rid, **kw)

    monkeypatch.setattr(dong_co, "xu_ly_run", _xu_ly_cham)

    for vong in range(3):
        rao = threading.Barrier(2)

        def _chay(rao=rao, vong=vong):
            # `wait()` khong timeout se treo VINH VIEN ca luong nay lan luong
            # kia (roi ca `future.result()` o luong chinh) neu mot worker
            # khong bao gio toi duoc rao (kiet thread/tai nguyen, scheduler
            # doi khi chay duoi quyen nang - review round 2, Important). Gioi
            # han 30s + bao loi ro rang, thay vi treo im lang.
            try:
                rao.wait(timeout=30)
            except threading.BrokenBarrierError:
                raise AssertionError(
                    f"vong {vong}: luong thu hai khong toi rao trong 30s - "
                    "khong ep duoc tranh chap that") from None
            dong_co.mot_vong(_mo(pg))

        with ThreadPoolExecutor(max_workers=2) as pool:
            futs = [pool.submit(_chay) for _ in range(2)]
            for f in futs:
                f.result()   # nem lai loi that cua luong - khong nuot
        _hoan_tat_job(pg)
    dong_co.mot_vong(_mo(pg))

    db = _mo(pg)()
    for rid in ids:
        viec = db.query(Job).filter_by(plan_id=rid).all()
        assert len(viec) == 2, (
            f"run {rid}: {len(viec)} job, ky vong dung 2 (a va b, khong doi)")
        khoa_ids = [j.dedupe_key for j in viec]
        assert len(khoa_ids) == len(set(khoa_ids)), (
            f"dedupe_key trung cho run {rid}: {khoa_ids} - da nop doi")
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
