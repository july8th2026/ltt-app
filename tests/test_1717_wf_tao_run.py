"""tao_run: ghim version, giữ tiền một lần, QUEUED + wakeup + sự kiện + job động cơ."""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401
from tests.test_1716_wf_xuat_ban_va_bao_gia_api import CC, _draft


@pytest.fixture()
def wf(db):
    from platform_core import credit
    from platform_core.workflow import dinh_nghia
    w = _draft(db)
    v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
    w.published_version_id = v.id
    credit.nap(db, "u1", 100, note="test")   # dùng đúng hàm nạp của credit.py
    db.flush()
    return w


def test_tao_run_day_du(db, wf):
    from platform_core.models import Job, Wakeup
    from platform_core.workflow import su_kien, tao_run
    run, moi = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                               trigger_kind="manual", idempotency_key="k1")
    assert moi and run.status == "QUEUED" and run.hold_id == run.id
    assert run.estimated_max == 6
    assert db.query(Wakeup).filter_by(run_id=run.id, kind="start").count() == 1
    assert [e.loai for e in su_kien.doc(db, run.id)] == ["WorkflowStarted"]
    dc = db.query(Job).filter_by(job_type=tao_run.DONG_CO_JOB).all()
    assert len(dc) == 1 and dc[0].origin == "workflow"


def test_job_dong_co_dung_slug_registry_bao(db, wf):
    """F2 (final-review.md): `Job.app_slug` của job động cơ phải khớp ĐÚNG
    app registry báo sở hữu `DONG_CO_JOB` — không phải một chuỗi viết tay
    (trước fix: luôn `"agent"`, bất kể registry nói gì)."""
    from platform_core import registry
    from platform_core.models import Job
    from platform_core.workflow import tao_run

    run, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                             trigger_kind="manual", idempotency_key="k2")
    dc = db.query(Job).filter_by(job_type=tao_run.DONG_CO_JOB).all()
    assert len(dc) == 1
    slug_that = registry.job_type_owners()[tao_run.DONG_CO_JOB]
    assert dc[0].app_slug == slug_that == tao_run.chu_dong_co()


def test_cung_khoa_tra_run_cu(db, wf):
    from platform_core.workflow import tao_run
    a, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                           trigger_kind="manual", idempotency_key="k1")
    b, moi = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                             trigger_kind="manual", idempotency_key="k1")
    assert a.id == b.id and moi is False


def test_chua_publish_bi_tu_choi(db):
    from platform_core.workflow import dinh_nghia, tao_run
    w = dinh_nghia.tao_workflow(db, owner_id="u1")
    with pytest.raises(tao_run.KhongCoBanPublish):
        tao_run.tao_run(db, workflow=w, owner_id="u1", trigger_kind="manual",
                        idempotency_key="k")


def test_qua_han_muc_run_dong_thoi(db, wf, monkeypatch):
    from platform_core.workflow import tao_run
    monkeypatch.setattr(tao_run, "MAX_RUN_DONG_THOI", 1)
    tao_run.tao_run(db, workflow=wf, owner_id="u1", trigger_kind="manual",
                    idempotency_key="a")
    with pytest.raises(tao_run.QuaHanMuc):
        tao_run.tao_run(db, workflow=wf, owner_id="u1", trigger_kind="manual",
                        idempotency_key="b")


def test_trung_khoa_khac_workflow(db, wf):
    """Cùng `idempotency_key`, hai `workflow` khác nhau của cùng chủ ⇒ XUNG
    ĐỘT (409 ở route), không lặng lẽ trả run của workflow kia."""
    from platform_core.workflow import dinh_nghia, tao_run
    a, moi = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                             trigger_kind="manual", idempotency_key="cung-khoa")
    assert moi

    w2 = _draft(db)
    v2 = dinh_nghia.xuat_ban_draft(db, w2.id, created_by="u1", cong_cu=CC)
    w2.published_version_id = v2.id
    db.flush()

    with pytest.raises(tao_run.TrungKhoaKhacWorkflow):
        tao_run.tao_run(db, workflow=w2, owner_id="u1", trigger_kind="manual",
                        idempotency_key="cung-khoa")


def test_thieu_credit_khong_con_run_mo_coi(db):
    """Thiếu tiền: `ThieuCreditError` ném ra, và savepoint gộp cả chuỗi cuộn
    sạch — không `WorkflowRun` mồ côi, không bút toán `CreditEntry` nào."""
    from platform_core import credit
    from platform_core.models import CreditEntry, WorkflowRun
    from platform_core.workflow import dinh_nghia, tao_run

    w = _draft(db)
    v = dinh_nghia.xuat_ban_draft(db, w.id, created_by="u1", cong_cu=CC)
    w.published_version_id = v.id
    db.flush()  # KHÔNG nạp credit — số dư 0, trần (estimated_max) là 6

    truoc_run = db.query(WorkflowRun).count()
    truoc_ce = db.query(CreditEntry).count()
    with pytest.raises(credit.ThieuCreditError):
        tao_run.tao_run(db, workflow=w, owner_id="u1", trigger_kind="manual",
                        idempotency_key="thieu-tien")
    assert db.query(WorkflowRun).count() == truoc_run
    assert db.query(CreditEntry).count() == truoc_ce


def test_khoa_rong_loi_that_khong_bi_nuot(db, wf, monkeypatch):
    """Khoá rỗng (`idempotency_key == ""`): một `IntegrityError` ở một bước
    SAU insert (giả lập ở `su_kien.ghi`) KHÔNG được đọc nhầm thành "trùng
    khoá, trả run cũ" — vì `_tim(owner_id, "")` khớp BẤT KỲ run nào trước đó
    của owner này cũng dùng khoá rỗng (`trigger_kind != "api"` không đòi
    khoá). Nuốt lỗi thật ở đây là mất dấu một lần chuyển đã hỏng."""
    from sqlalchemy.exc import IntegrityError

    from platform_core.models import WorkflowRun
    from platform_core.workflow import su_kien, tao_run

    # Một run KHÔNG LIÊN QUAN trước đó, cùng owner, cũng khoá rỗng.
    cu, moi_cu = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                                 trigger_kind="manual", idempotency_key="")
    assert moi_cu
    db.flush()
    truoc = db.query(WorkflowRun).count()

    def _no(*_a, **_k):
        raise IntegrityError("x", {}, Exception("gia lap loi khac"))
    monkeypatch.setattr(su_kien, "ghi", _no)

    with pytest.raises(IntegrityError):
        tao_run.tao_run(db, workflow=wf, owner_id="u1", trigger_kind="manual",
                        idempotency_key="")
    assert db.query(WorkflowRun).count() == truoc, (
        "loi that o su_kien.ghi khong duoc nuot bang cach tra ve run cu")
