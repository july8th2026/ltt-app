"""Workflow V2 trên PostgreSQL thật: hai vòng động cơ song song, crash giữa chừng.

Chạy qua `tools/check_multiproc.py` (tự dựng CSDL scratch theo cây).
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import sqlalchemy as sa

from tests import pg_scratch

pytestmark = pg_scratch.skip_without_postgres()

#: Khoa advisory Postgres (muc phien) giu SUOT tep nay dang chay mot test —
#: xem ly do o fixture `pg`. So bat ky, chi can khong dung so nao khac trong
#: kho (khong phoi hop bang dat ten dep, phoi hop bang mot hang co dinh).
_KHOA_LOCK_KEY = 172012001720   # tuy y, gan voi ten tep "1720" de de nhan dien


@pytest.fixture()
def pg(monkeypatch):
    url = pg_scratch.scratch_url()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    # `pytest-xdist -n 2` (hoac hon) phan hai test CUA CHINH TEP NAY cho hai
    # worker KHAC NHAU, va ca hai tro ve CUNG MOT CSDL scratch (`scratch_url`
    # doc cung mot bien moi truong). Khong co gi ngan hai worker goi
    # `drop_all`/`create_all` CUNG LUC — da thay that (23/09): hai `CREATE
    # TABLE` dung ten dua nhau tren catalog he thong Postgres, nem
    # `UniqueViolation` ngay o buoc dung fixture. Ke ca khong dung DDL, hai
    # bai test chay THAT SU song song tren CUNG schema se ghi de du lieu cua
    # nhau (vd `WorkflowRun` cua bai nay lo vao truy van "moi run SUCCEEDED"
    # cua bai kia). `xdist_group` KHONG giai duoc: no chi co hieu luc voi
    # `--dist=loadgroup`, va khong noi goi lenh nao o day dam bao co co.
    # Khoa advisory cua chinh Postgres thi dung bat ke `-n` bao nhieu hay
    # `--dist` gi: worker thua vao SAU se doi tai `pg_advisory_lock` cho toi
    # khi worker truoc giai phong (fixture teardown), nen hai test trong tep
    # nay luon chay TUAN TU voi nhau tren cung mot CSDL - it hai worker khac
    # (vd tu `test_214`) van chay song song binh thuong.
    khoa_engine = sa.create_engine(url, future=True)
    khoa_conn = khoa_engine.connect()
    khoa_conn.execute(sa.text("SELECT pg_advisory_lock(:k)"), {"k": _KHOA_LOCK_KEY})

    try:
        dbmod.Base.metadata.drop_all(dbmod.get_engine())
        dbmod.Base.metadata.create_all(dbmod.get_engine())
        yield dbmod
    finally:
        dbmod.reset_engine()
        khoa_conn.execute(sa.text("SELECT pg_advisory_unlock(:k)"), {"k": _KHOA_LOCK_KEY})
        khoa_conn.close()
        khoa_engine.dispose()


def _mo(dbmod):
    return lambda: next(dbmod.get_session())


def _chuan_bi(dbmod, monkeypatch, so_run=10):
    from platform_core import credit
    from platform_core.workflow import cong_cu, dinh_nghia, tao_run
    from tests.conftest import bao_dam_user
    from tests.test_1716_wf_xuat_ban_va_bao_gia_api import CC, _draft
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    db = _mo(dbmod)()
    w = _draft(db)
    v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
    w.published_version_id = v.id
    # `credit.nap` ghi vao `credit_entries`, cot `user_id` mang khoa ngoai
    # tham chieu `users.id` (F-01, audit 2026-08-07) — Postgres THAT SU thi
    # ep FK nay (SQLite mac dinh KHONG, nen cac test cung dong cua tren
    # SQLite khong bao gio bat duoc thieu buoc nay). `bao_dam_user` la
    # helper dung chung cua kho (`tests/conftest.py`), tao mot user gia mang
    # dung id neu chua co.
    bao_dam_user(db, "u1")
    credit.nap(db, "u1", 10_000, note="test")
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
