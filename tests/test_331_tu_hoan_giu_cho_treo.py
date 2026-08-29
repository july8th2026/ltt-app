"""H41.3 — INV-5 tu *quan sat* thanh *bao dam*: khoan treo duoc TU HOAN.

Tu 2026-08-26 nen tang DA BIET khoan nao treo: `giu_cho_treo()` do dung, chuong
keu dung, email toi dung nguoi. Va hai khoan treo ngay 24/08 **van nam nguyen o
do** — vi bao khong phai hoan. Mot cai chuong ma moi lan keu deu can mot nguoi
xu tay la mot cai chuong roi se co nguoi tat.

⛔ NUA DE MAT CUA PHEP KIEM NAY la chieu KHONG DUOC HOAN. Mot ham "tu hoan" ma
   hoan qua tay thi te hon han khong co no: so credit CHI GHI THEM, nen mot lan
   tra nham khong xoa duoc — chi bu duoc. Nen quá nửa số phép kiểm dưới đây do
   nhung truong hop **phai giu nguyen tien**.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from platform_core import credit
from platform_core.models import Job


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'hoan.db').as_posix()}"
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


def _user(db, uid: str, nap: int = 100):
    from tests.conftest import bao_dam_user
    bao_dam_user(db, uid)
    credit.cap_tay(db, uid, nap, by="test")
    return uid


def _job(db, uid: str, *, status: str = "failed") -> Job:
    job = Job(user_id=uid, app_slug="thumbnail", job_type="thumbnail.render",
              params={}, status=status)
    db.add(job)
    db.flush()
    return job


def _lui(db, job_id: str, gio: float) -> None:
    """Day but toan `hold` lui ve qua khu, de khong phai cho that."""
    from platform_core.models import CreditEntry
    from sqlalchemy import select

    luc = datetime.now(timezone.utc) - timedelta(hours=gio)
    for e in db.execute(select(CreditEntry).where(
            CreditEntry.job_id == job_id)).scalars().all():
        e.created_at = luc
    db.flush()


# ── Chieu CO hoan ───────────────────────────────────────────────────────────

def test_khoan_treo_qua_han_duoc_hoan_va_khach_lay_lai_du_tien(db):
    uid = _user(db, "u_hoan")
    job = _job(db, uid)
    credit.giu_cho(db, uid, 30, job.id)
    _lui(db, job.id, 30)
    assert credit.so_du(db, uid) == 70

    da = credit.tu_hoan_treo(db)

    assert [m.job_id for m in da] == [job.id]
    assert credit.so_du(db, uid) == 100, "khach chua lay lai du tien"


def test_hoan_hai_lan_khong_tra_hai_lan(db):
    """`hoan()` idempotent theo job — chot lai o day vi day la duong TIEN.

    Neu lease `bao_tri` hong thi N tien trinh cung chay ham nay. Tien khong duoc
    sai vi mot loi dieu phoi.
    """
    uid = _user(db, "u_hai_lan")
    job = _job(db, uid)
    credit.giu_cho(db, uid, 25, job.id)
    _lui(db, job.id, 30)

    credit.tu_hoan_treo(db)
    credit.tu_hoan_treo(db)

    assert credit.so_du(db, uid) == 100


# ── Chieu KHONG duoc hoan — nua de mat ──────────────────────────────────────

def test_chua_du_han_thi_KHONG_hoan(db):
    """Chuong keu o 6 gio; tu hoan o 24. Khoang giua la cho nguoi truc bac bo."""
    uid = _user(db, "u_som")
    job = _job(db, uid)
    credit.giu_cho(db, uid, 40, job.id)
    _lui(db, job.id, 8)                     # da qua nguong BAO, chua qua nguong HOAN

    assert credit.giu_cho_treo(db) != [], "khoan nay phai duoc BAO o moc 8 gio"
    assert credit.tu_hoan_treo(db) == [], "nhung KHONG duoc hoan o moc 8 gio"
    assert credit.so_du(db, uid) == 60


def test_khoan_KHONG_CO_KHOA_thi_khong_bao_gio_tu_hoan(db):
    """`job_id` rong => `hoan()` khong tra duoc => tu dong hoa la DOAN tien cua ai.

    Day chinh la hinh dang cua hai khoan treo that ngay 24/08 tren production.
    Chung phai duoc BAO, va phai de NGUOI xu.
    """
    uid = _user(db, "u_khong_khoa")
    credit.giu_cho(db, uid, 15, "")

    treo = credit.giu_cho_treo(db)
    assert any(t.ly_do == "khong_co_khoa" for t in treo), "phai duoc BAO"
    assert credit.tu_hoan_treo(db) == [], "khong duoc tu hoan khoan khong co khoa"
    assert credit.so_du(db, uid) == 85


def test_job_con_SONG_thi_khong_hoan(db):
    """Hang doi tac 30 tieng khong phai tien treo — no chi dang cho."""
    for trang_thai in ("queued", "running"):
        uid = _user(db, f"u_song_{trang_thai}")
        job = _job(db, uid, status=trang_thai)
        credit.giu_cho(db, uid, 20, job.id)
        _lui(db, job.id, 30)

        assert credit.tu_hoan_treo(db) == [], f"job {trang_thai} bi hoan nham"
        assert credit.so_du(db, uid) == 80


def test_da_quyet_toan_roi_thi_khong_hoan(db):
    uid = _user(db, "u_da_ket")
    job = _job(db, uid)
    credit.giu_cho(db, uid, 30, job.id)
    credit.quyet_toan(db, uid, job.id, 30)
    _lui(db, job.id, 40)

    assert credit.tu_hoan_treo(db) == []
    assert credit.so_du(db, uid) == 70, "khoan da thu roi bi tra lai"


# ── Tran moi luot ───────────────────────────────────────────────────────────

def test_tran_moi_luot_gioi_han_so_khoan_hoan(db):
    """Mot loi khien hang nghin khoan bi coi la treo phai thanh mot su co NHO."""
    uid = _user(db, "u_tran", nap=1000)
    for _ in range(5):
        job = _job(db, uid)
        credit.giu_cho(db, uid, 10, job.id)
        _lui(db, job.id, 30)

    da = credit.tu_hoan_treo(db, tran=2)
    assert len(da) == 2, f"tran khong duoc ton trong: hoan {len(da)} khoan"


def test_cham_tran_thi_NOI_RA_chu_khong_cat_im_lang(db, caplog):
    """Mot tran am tham doc nhu 'da xong het'."""
    import logging

    uid = _user(db, "u_noi", nap=1000)
    for _ in range(4):
        job = _job(db, uid)
        credit.giu_cho(db, uid, 10, job.id)
        _lui(db, job.id, 30)

    with caplog.at_level(logging.WARNING):
        credit.tu_hoan_treo(db, tran=2)

    assert any("cham tran" in r.message.lower() or "cham tran" in r.getMessage().lower()
               for r in caplog.records), "cham tran ma khong co dong log nao"


# ── Vong bao tri ────────────────────────────────────────────────────────────

def test_vong_bao_tri_co_goi_tu_hoan():
    """Mot ham khong ai goi la mot ham khong chay — bay 13 cua cong chat luong."""
    import inspect

    from platform_core import job_runner

    than = inspect.getsource(job_runner._mot_luot_bao_tri)
    assert "_tu_hoan_giu_cho_treo" in than, (
        "tu hoan khong duoc goi trong vong bao tri => no khong bao gio chay")


def test_hai_nguong_KHAC_nhau_va_hoan_LAU_hon_bao():
    """Bang nhau la may hoan truoc khi ai kip nhin."""
    assert credit.TU_HOAN_SAU > credit.TREO_SAU, (
        f"tu hoan {credit.TU_HOAN_SAU} phai DAI HON nguong bao {credit.TREO_SAU}")
