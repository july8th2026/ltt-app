"""
H3 — sổ credit + tích hợp với hàng đợi job.

Phần tiền: mỗi test ở đây khoá một tính chất mà nếu sai là mất tiền thật hoặc
mất khách. Chạy trên SQLite tạm; nghiệm thu atomic + đồng thời trên PostgreSQL
riêng.

Trọng tâm:
- số dư = tổng của sổ (append-only), không ô sửa đè;
- không đủ credit → job KHÔNG được tạo (rollback cả cụm);
- job lỗi → hoàn ĐỦ, số dư về như cũ;
- job chạy lại (retry/dedupe) → KHÔNG trừ hai lần;
- quyết toán/hoàn idempotent.
"""
from __future__ import annotations

import pytest

from tests.conftest import APP_THU_JOB, APP_THU_SLUG, bao_dam_user


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'c.db').as_posix()}"
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


# ── Sổ credit thuần ───────────────────────────────────────────────────────────

def test_so_du_la_tong_cua_so(db):
    from platform_core import credit
    assert credit.so_du(db, "u1") == 0
    credit.nap(db, "u1", 100); db.commit()
    bao_dam_user(db, "u1"); credit.cap_tay(db, "u1", 50, by="admin"); db.commit()
    assert credit.so_du(db, "u1") == 150
    bao_dam_user(db, "u1"); credit.cap_tay(db, "u1", -30, by="admin"); db.commit()
    assert credit.so_du(db, "u1") == 120


def test_nap_am_bi_tu_choi(db):
    from platform_core import credit
    with pytest.raises(ValueError):
        credit.nap(db, "u1", -10)


def test_giu_cho_thieu_credit_bi_tu_choi(db):
    from platform_core import credit
    credit.nap(db, "u1", 10); db.commit()
    with pytest.raises(credit.ThieuCreditError):
        credit.giu_cho(db, "u1", 50, "job-x")


def test_giu_cho_tru_dung(db):
    from platform_core import credit
    credit.nap(db, "u1", 100); db.commit()
    credit.giu_cho(db, "u1", 30, "job-1"); db.commit()
    assert credit.so_du(db, "u1") == 70
    assert credit.so_da_giu(db, "job-1") == 30


def test_hoan_tra_lai_du_va_idempotent(db):
    from platform_core import credit
    credit.nap(db, "u1", 100); db.commit()
    credit.giu_cho(db, "u1", 40, "job-2"); db.commit()
    assert credit.so_du(db, "u1") == 60

    credit.hoan(db, "u1", "job-2"); db.commit()
    assert credit.so_du(db, "u1") == 100, "hoan phai tra lai DU"
    credit.hoan(db, "u1", "job-2"); db.commit()
    assert credit.so_du(db, "u1") == 100, "hoan lan hai khong duoc cong them"


def test_quyet_toan_gia_that_bang_uoc_tinh(db):
    from platform_core import credit
    credit.nap(db, "u1", 100); db.commit()
    credit.giu_cho(db, "u1", 30, "job-3"); db.commit()
    credit.quyet_toan(db, "u1", "job-3", 30); db.commit()
    assert credit.so_du(db, "u1") == 70, "tru dung 30"


def test_quyet_toan_gia_that_re_hon_thi_hoan_du(db):
    from platform_core import credit
    credit.nap(db, "u1", 100); db.commit()
    credit.giu_cho(db, "u1", 30, "job-4"); db.commit()
    credit.quyet_toan(db, "u1", "job-4", 20); db.commit()   # that te chi 20
    assert credit.so_du(db, "u1") == 80, "giu 30 that 20 -> tra lai 10"


def test_quyet_toan_idempotent(db):
    from platform_core import credit
    credit.nap(db, "u1", 100); db.commit()
    credit.giu_cho(db, "u1", 30, "job-5"); db.commit()
    credit.quyet_toan(db, "u1", "job-5", 30); db.commit()
    credit.quyet_toan(db, "u1", "job-5", 30); db.commit()   # goi lai
    assert credit.so_du(db, "u1") == 70, "quyet toan hai lan khong tru hai lan"


def test_quyet_toan_khong_thu_vuot_muc_da_giu(db):
    """Provider vượt quote là chi phí nền tảng, không được làm số dư khách âm."""
    from platform_core import credit
    credit.nap(db, "u1", 30); db.commit()
    credit.giu_cho(db, "u1", 29, "job-overage"); db.commit()

    settled = credit.quyet_toan(db, "u1", "job-overage", 78); db.commit()

    assert credit.so_du(db, "u1") == 1
    assert settled.held_credit == 29
    assert settled.provider_credit == 78
    assert settled.charged_credit == 29
    assert settled.variance_credit == 49
    assert settled.capped is True


def test_hoan_va_quyet_toan_chi_mot_duong_duoc_chot(db):
    from platform_core import credit
    credit.nap(db, "u1", 50); db.commit()
    credit.giu_cho(db, "u1", 20, "job-refund-first"); db.commit()
    credit.hoan(db, "u1", "job-refund-first"); db.commit()

    settled = credit.quyet_toan(db, "u1", "job-refund-first", 20); db.commit()

    assert settled.already_final is True
    assert settled.charged_credit == 0
    assert credit.so_du(db, "u1") == 50


# ── Tích hợp submit + credit ──────────────────────────────────────────────────

def _nap(db, uid, n):
    from platform_core import credit
    credit.nap(db, uid, n); db.commit()


def test_submit_giu_cho_dung_gia(db, app_thu):
    from platform_core import credit
    from platform_core.job_submit import submit_with_credit
    _nap(db, "u1", 100)
    # gia cua app thu = max(1, len//100). text 250 ky tu -> 2 credit.
    job = submit_with_credit(db, user_id="u1", app_slug=APP_THU_SLUG,
                             job_type=APP_THU_JOB, params={"text": "x" * 250})
    db.commit()
    assert credit.so_da_giu(db, job.id) == 2
    assert credit.so_du(db, "u1") == 98


def test_submit_thieu_credit_khong_tao_job(db, app_thu):
    from platform_core import credit
    from platform_core.job_submit import submit_with_credit
    from platform_core.models import Job
    # Khong nap gi -> so du 0.
    with pytest.raises(credit.ThieuCreditError):
        submit_with_credit(db, user_id="u1", app_slug=APP_THU_SLUG,
                           job_type=APP_THU_JOB, params={"text": "abc"})
    db.rollback()
    assert db.query(Job).count() == 0, "thieu credit thi KHONG duoc tao job"
    assert credit.so_du(db, "u1") == 0


def test_submit_trung_khong_tru_hai_lan(db, app_thu):
    """Bấm lại / F5 (cùng dedupe_key khi job cũ còn chạy) → giữ chỗ MỘT lần."""
    from platform_core import credit
    from platform_core.job_submit import submit_with_credit
    _nap(db, "u1", 100)
    j1 = submit_with_credit(db, user_id="u1", app_slug=APP_THU_SLUG,
                            job_type=APP_THU_JOB, params={"text": "abc"},
                            dedupe_key="dk1")
    db.commit()
    sau_lan_1 = credit.so_du(db, "u1")
    j2 = submit_with_credit(db, user_id="u1", app_slug=APP_THU_SLUG,
                            job_type=APP_THU_JOB, params={"text": "abc"},
                            dedupe_key="dk1")
    db.commit()
    assert j1.id == j2.id
    assert credit.so_du(db, "u1") == sau_lan_1, "bam lai khong duoc tru them"


# ── Vòng đời trọn vẹn qua worker ──────────────────────────────────────────────

def test_job_thanh_cong_tru_dung_credit(db, app_thu):
    from platform_core import credit
    from platform_core.job_runner import _chay_mot_job
    from platform_core.job_submit import submit_with_credit
    from platform_core.models import Job, JOB_DONE
    _nap(db, "u1", 100)
    job = submit_with_credit(db, user_id="u1", app_slug=APP_THU_SLUG,
                             job_type=APP_THU_JOB, params={"text": "xin chao"})
    db.commit()
    jid = job.id
    held = credit.so_da_giu(db, jid)

    _chay_mot_job("w-test")

    db.expire_all()
    assert db.get(Job, jid).status == JOB_DONE
    assert credit.so_du(db, "u1") == 100 - held, "tru dung phan da giu"


def test_worker_cong_khai_so_thu_da_cap_thay_vi_gia_provider(db, monkeypatch,
                                                             app_thu):
    from platform_core import credit
    from platform_core import jobs as jobs_mod
    from platform_core.job_runner import _chay_mot_job
    from platform_core.job_submit import submit_with_credit
    from platform_core.models import Job, JobEvent

    _nap(db, "u1", 100)
    job = submit_with_credit(db, user_id="u1", app_slug=APP_THU_SLUG,
                             job_type=APP_THU_JOB, params={"text": "abc"})
    db.commit()
    held = credit.so_da_giu(db, job.id)
    # Handler báo về một giá CAO HƠN phần đã giữ. Thay handler qua
    # `resolve_handler` chứ không qua module của một app: app thử không có
    # module trên đĩa, và đó là chủ ý — xem `conftest.app_thu`.
    monkeypatch.setattr(
        jobs_mod, "resolve_handler",
        lambda jt: (lambda params, ctx=None: {"text": "cba",
                                              "credit_cost": held + 49}),
    )

    _chay_mot_job("w-cap")

    db.expire_all()
    finished = db.get(Job, job.id)
    assert finished.result["credit_cost"] == held
    event = db.query(JobEvent).filter_by(
        job_id=job.id, event_code="credit_settled").one()
    assert event.details["provider_credit"] == held + 49
    assert event.details["credit"] == held
    assert event.details["variance_credit"] == 49
    assert event.level == "warning"


def test_job_that_bai_hoan_credit(db, app_thu):
    from platform_core import credit
    from platform_core.job_runner import _chay_mot_job
    from platform_core.job_submit import submit_with_credit
    from platform_core.models import Job, JOB_ERROR
    _nap(db, "u1", 100)
    # text rong -> handler cua app thu nem loi. max_attempts=1 -> that bai la error luon.
    job = submit_with_credit(db, user_id="u1", app_slug=APP_THU_SLUG,
                             job_type=APP_THU_JOB, params={"text": "   "},
                             max_attempts=1)
    db.commit()
    jid = job.id
    assert credit.so_du(db, "u1") < 100, "da giu cho luc submit"

    _chay_mot_job("w-test")

    db.expire_all()
    assert db.get(Job, jid).status == JOB_ERROR
    assert credit.so_du(db, "u1") == 100, "job that bai phai hoan DU credit"
