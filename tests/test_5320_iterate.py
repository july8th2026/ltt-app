"""T-3 (spec Sec 10.2) -- 2 luot dau mien phi, bo dem nam trong CSDL.

Phep quyet dinh la `test_bo_dem_song_qua_mot_session_moi`: bo dem trong phien
nghia la khach mo tab moi la co 2 luot mien phi nua -- LLM mien phi vo han.
"""
from __future__ import annotations

from contextlib import contextmanager

import pytest

from apps.prompt_ai_ommi.services import briefs as bf
from apps.prompt_ai_ommi.services import iterate as it


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'iterate.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    yield session
    session.close()
    dbmod.reset_engine()


@pytest.fixture()
def db_factory(tmp_path, monkeypatch):
    """Tra ve mot ham: goi ra la mot context manager mo SESSION MOI, cung
    engine/tep sqlite voi fixture `db` o tren -- de kiem tra bo dem SONG QUA
    mot session moi (khong phai chi song trong RAM cua mot session dang mo).
    """
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'iterate_factory.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    @contextmanager
    def _mo():
        session = next(dbmod.get_session())
        try:
            yield session
        finally:
            session.close()

    yield _mo
    dbmod.reset_engine()


@pytest.fixture()
def brief(db):
    b = bf.tao_brief(db, "u1", {"title": "T", "story_vi": "x" * 40})
    db.commit()
    return b


def test_hai_luot_dau_mien_phi(db, brief):
    assert it.bao_gia(db, brief)["was_free"] is True
    it.mo_luot(db, brief, "sua canh 1", "prompt"); db.commit()
    assert it.bao_gia(db, brief)["was_free"] is True
    it.mo_luot(db, brief, "sua canh 2", "prompt"); db.commit()
    assert it.bao_gia(db, brief)["was_free"] is False


def test_luot_thu_ba_thu_tien_duong(db, brief):
    for i in range(2):
        it.mo_luot(db, brief, f"f{i}", "p")
    db.commit()
    gia = it.bao_gia(db, brief)
    assert gia["was_free"] is False and gia["credit"] > 0


def test_con_mien_phi_dem_dung_va_khong_bao_gio_am(db, brief):
    assert it.con_mien_phi(brief) == 2
    brief.free_iterations_used = 5
    assert it.con_mien_phi(brief) == 0


def test_bo_dem_tang_CUNG_transaction_voi_iteration(db, brief):
    """Neu hai viec khong cung transaction, mot lan crash giua chung se tao
    iteration ma khong tinh luot -- hoac tinh luot ma khong co iteration.
    """
    it.mo_luot(db, brief, "f", "p")
    # Chua commit: ca hai thay doi phai cung nam trong session dang mo.
    assert brief.free_iterations_used == 1
    assert len(db.new) >= 1
    db.rollback()
    assert brief.free_iterations_used == 0


def test_bo_dem_song_qua_mot_session_moi(db_factory):
    """Phep quyet dinh cua T-3. Dong session, mo session MOI, van phai thu tien."""
    with db_factory() as db1:
        b = bf.tao_brief(db1, "u1", {"title": "T", "story_vi": "x" * 40})
        db1.commit()
        bid = b.id
        it.mo_luot(db1, b, "f1", "p"); it.mo_luot(db1, b, "f2", "p")
        db1.commit()

    with db_factory() as db2:
        b2 = bf.doc_brief(db2, bid, "u1")
        assert b2.free_iterations_used == 2
        assert it.bao_gia(db2, b2)["was_free"] is False


def test_seq_tang_lien_tuc_tu_1(db, brief):
    a = it.mo_luot(db, brief, "f1", "p")
    bb = it.mo_luot(db, brief, "f2", "p")
    db.commit()
    assert (a.seq, bb.seq) == (1, 2)


def test_phan_quyet_rejected_KHONG_hoan_credit(db, brief):
    """Hoan thi khach bam rejected moi lan la LLM mien phi vo han."""
    lt = it.mo_luot(db, brief, "f", "p")
    lt.credit_charged = 5
    db.commit()
    it.dat_phan_quyet(db, lt, "rejected"); db.commit()
    assert lt.verdict == "rejected"
    assert lt.credit_charged == 5      # khong ve 0


def test_phan_quyet_chi_nhan_hai_gia_tri(db, brief):
    lt = it.mo_luot(db, brief, "f", "p"); db.commit()
    with pytest.raises(ValueError):
        it.dat_phan_quyet(db, lt, "maybe")


def test_hai_mo_luot_LIEN_TIEP_khong_commit_giua_chung_van_dem_dung(db, brief):
    """Bay da xay ra that: mot ban vá dung `db.refresh()` sau khi co khoa da
    VUT mat lan tang dau tien vi `refresh()` bo qua thay doi CHUA COMMIT cua
    chinh phien nay. Hai `mo_luot` goi LIEN TIEP, KHONG commit giua chung,
    phai vao dung seq 1 va 2, va ca hai deu mien phi (con 2 luot).
    """
    a = it.mo_luot(db, brief, "f1", "p")
    bb = it.mo_luot(db, brief, "f2", "p")
    assert (a.seq, bb.seq) == (1, 2)
    assert (a.was_free, bb.was_free) == (True, True)
    assert brief.free_iterations_used == 2
    db.commit()


def test_luot_thu_ba_thuc_su_bi_thu_tien_khac_khong(db, brief):
    """Tiem ca doi chung cho phep dem: lam het 2 luot free roi mo luot thu ba
    va kiem no KHONG duoc mien phi -- doi voi phep 'hai luot dau mien phi' o
    tren, day la mat khong-mien-phi phai duoc chung minh, khong chi suy tu no.
    """
    for i in range(2):
        it.mo_luot(db, brief, f"f{i}", "p")
    db.commit()
    lt3 = it.mo_luot(db, brief, "f3", "p")
    db.commit()
    assert lt3.was_free is False
    assert lt3.credit_charged > 0
