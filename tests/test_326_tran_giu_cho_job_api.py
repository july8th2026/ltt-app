"""H35.10b — bao gia da ky cua khach API la mot TRAN, khong phai mot uoc luong.

`quyet_toan` von da khong bao gio thu qua `held`. Nen lo hong that KHONG nam o
luc quyet toan — no nam o cho worker **nang** `held` len giua chung
(`_dam_bao_giu_cho`). Nang xong thi quyet toan thu dung so moi, va khach tra
nhieu hon con so ho bam dong y. Do la Q84, su co Seedance giu 29 thu 78.

H35.10a lam bao gia DUNG (may chu do thoi luong). No khong lam bao gia KHONG
THE SAI: worker chay ffprobe cua rieng no, va `math.ceil` trong cong thuc gia
co the lech mot credit chi vi mot khac biet lam tron. Mot credit thi nho; mot
loi hua khong giu duoc thi khong.

⭐ Bat bien o day co MOT nua de bi bo sot, va no quan trong ngang nua kia:
   duong GIAO DIEN WEB van phai nang giu cho duoc. O do co nguoi ngoi, ho chon
   tep ho nhin thay, va ho duoc hoi lai. Chan ca hai duong la sua dung mot nua
   va pha mot nua.
"""
from __future__ import annotations

import pytest

from platform_core import credit
from platform_core.models import Job


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'tran.db').as_posix()}"
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


@pytest.fixture()
def bao_dam_user():
    from tests.conftest import bao_dam_user as goc
    return goc


def _job(db, user_id: str, *, tu_api: bool) -> Job:
    params: dict = {"video_key": "k"}
    if tu_api:
        params["_api"] = {"tool": "video.upscale", "key_id": "key_1"}
    job = Job(user_id=user_id, app_slug="upscalevideo",
              job_type="upscalevideo.render", params=params, status="queued")
    db.add(job)
    db.flush()
    return job


# ── Nua thu nhat: job API — tran cung ────────────────────────────────────────

def test_job_API_khong_the_bi_nang_giu_cho_qua_bao_gia(db, bao_dam_user):
    bao_dam_user(db, "u_api")
    credit.cap_tay(db, "u_api", 500, by="test")
    job = _job(db, "u_api", tu_api=True)

    credit.giu_cho(db, "u_api", 30, job.id)          # bao gia da ky
    assert credit.so_da_giu(db, job.id) == 30

    credit.giu_cho(db, "u_api", 1, job.id)           # worker doi nang them
    assert credit.so_da_giu(db, job.id) == 30, "bao gia da ky bi vuot"


def test_tran_khong_lam_hong_job_cua_khach(db, bao_dam_user):
    """Hap thu chenh lech, KHONG nem loi.

    Nem o day se giet job vi mot khac biet lam tron mot credit — te hon han thu
    no dinh bao ve. Cung logic ma `quyet_toan` da dung khi provider dat hon bao
    gia: phan vuot la variance noi bo cua nen tang.
    """
    bao_dam_user(db, "u_api2")
    credit.cap_tay(db, "u_api2", 500, by="test")
    job = _job(db, "u_api2", tu_api=True)
    credit.giu_cho(db, "u_api2", 30, job.id)

    credit.giu_cho(db, "u_api2", 999, job.id)        # khong duoc nem
    assert credit.so_da_giu(db, job.id) == 30


def test_khach_khong_bi_thu_qua_so_da_ky_khi_quyet_toan(db, bao_dam_user):
    """Bat bien tan cung — do bang SO DU, khong bang so trung gian."""
    bao_dam_user(db, "u_api3")
    credit.cap_tay(db, "u_api3", 100, by="test")
    job = _job(db, "u_api3", tu_api=True)

    credit.giu_cho(db, "u_api3", 30, job.id)
    credit.giu_cho(db, "u_api3", 12, job.id)         # worker do ra 42
    credit.quyet_toan(db, "u_api3", job.id, 42)

    assert credit.so_du(db, "u_api3") == 70, "khach tra qua con so da bam dong y"


def test_lan_giu_DAU_TIEN_cua_job_API_van_phai_chay(db, bao_dam_user):
    """Chan ca lan dau thi khong job API nao chay duoc — kiem huong nguoc lai."""
    bao_dam_user(db, "u_api4")
    credit.cap_tay(db, "u_api4", 50, by="test")
    job = _job(db, "u_api4", tu_api=True)

    credit.giu_cho(db, "u_api4", 25, job.id)
    assert credit.so_da_giu(db, job.id) == 25
    assert credit.so_du(db, "u_api4") == 25


# ── Nua thu hai: duong web — van nang duoc, va do la co y ────────────────────

def test_duong_WEB_van_nang_giu_cho_duoc(db, bao_dam_user):
    """Nua de bi bo sot. Co nguoi ngoi do, ho duoc hoi lai — nang la dung."""
    bao_dam_user(db, "u_web")
    credit.cap_tay(db, "u_web", 500, by="test")
    job = _job(db, "u_web", tu_api=False)

    credit.giu_cho(db, "u_web", 30, job.id)
    credit.giu_cho(db, "u_web", 12, job.id)
    assert credit.so_da_giu(db, job.id) == 42


def test_job_khong_co_hang_trong_bang_thi_khong_bi_chan(db, bao_dam_user):
    """Giu cho chay trong cung transaction voi `jobs.submit`.

    Co duong goi giu cho TRUOC khi hang job nhin thay duoc. Coi "khong tim thay
    job" la "da niem phong" se chan dung duong do.
    """
    bao_dam_user(db, "u_mo_coi")
    credit.cap_tay(db, "u_mo_coi", 100, by="test")
    credit.giu_cho(db, "u_mo_coi", 10, "job-khong-co-that")
    assert credit.so_da_giu(db, "job-khong-co-that") == 10


# ── Dau vet: nguoi truc phai doc lai duoc vi sao giu cho khong nhuc nhich ────

def test_lan_bi_chan_de_lai_dau_vet_noi_bo(db, bao_dam_user):
    """Mot chinh sach im lang la mot chinh sach khong ai go roi duoc luc 2 gio sang."""
    from platform_core.models import JobEvent

    bao_dam_user(db, "u_vet")
    credit.cap_tay(db, "u_vet", 500, by="test")
    job = _job(db, "u_vet", tu_api=True)
    credit.giu_cho(db, "u_vet", 30, job.id)
    credit.giu_cho(db, "u_vet", 7, job.id)

    su_kien = db.query(JobEvent).filter_by(job_id=job.id).all()
    loai = [e.event_code for e in su_kien]
    assert "credit_hold_capped" in loai, loai
    vet = next(e for e in su_kien if e.event_code == "credit_hold_capped")
    # So bi tu choi phai co trong dau vet: biet "da chan" ma khong biet "chan
    # bao nhieu" thi khong doi chieu duoc voi hoa don cua khach.
    assert vet.details.get("requested") == 7, vet.details
    assert vet.details.get("held") == 30, vet.details


@pytest.mark.parametrize("xin", [1, 5, 999])
def test_moi_muc_xin_them_deu_bi_chan_nhu_nhau(db, bao_dam_user, xin):
    bao_dam_user(db, "u_nhieu")
    credit.cap_tay(db, "u_nhieu", 5000, by="test")
    job = _job(db, "u_nhieu", tu_api=True)
    credit.giu_cho(db, "u_nhieu", 30, job.id)
    credit.giu_cho(db, "u_nhieu", xin, job.id)
    assert credit.so_da_giu(db, job.id) == 30
