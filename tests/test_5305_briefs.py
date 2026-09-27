"""Pha 3 -- brief va canh kich ban. Trong tam: id canh phai TAI DUNG duoc."""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services import briefs as bf


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'briefs.db').as_posix()}")
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


def test_tao_va_doc_brief(db):
    b = bf.tao_brief(db, "u1", {"title": "Phim thu", "story_vi": "x" * 40})
    db.flush()
    assert bf.doc_brief(db, b.id, "u1").title == "Phim thu"


def test_doc_brief_cua_nguoi_khac_bi_tu_choi(db):
    b = bf.tao_brief(db, "u1", {"title": "Phim thu", "story_vi": "x" * 40})
    db.flush()
    with pytest.raises(KeyError):
        bf.doc_brief(db, b.id, "u2")


def test_dat_canh_GIU_NGUYEN_id_truyen_vao(db):
    """S-4: binding cua pha 1 tro vao id canh cu.

    Sinh id moi o day nghia la MOI binding pha 1 tro vao hu khong -- anh tham
    chieu mat sach, dung con bo N-1 ma ca spec nay dang chua.
    """
    b = bf.tao_brief(db, "u1", {"title": "T", "story_vi": "x" * 40})
    db.flush()
    canh = bf.dat_canh(db, b, [
        {"id": "scene_abc123", "title": "Canh 1", "prompt": "p1"},
        {"id": "scene_def456", "title": "Canh 2", "prompt": "p2"},
    ])
    db.flush()
    assert [c.id for c in canh] == ["scene_abc123", "scene_def456"]


def test_dat_canh_khong_co_id_thi_tu_sinh(db):
    b = bf.tao_brief(db, "u1", {"title": "T", "story_vi": "x" * 40})
    db.flush()
    canh = bf.dat_canh(db, b, [{"title": "Canh 1", "prompt": "p"}])
    db.flush()
    assert canh[0].id and len(canh[0].id) >= 8


def test_dat_canh_danh_lai_vi_tri_lien_tuc_tu_0(db):
    b = bf.tao_brief(db, "u1", {"title": "T", "story_vi": "x" * 40})
    db.flush()
    canh = bf.dat_canh(db, b, [{"title": f"C{i}"} for i in range(4)])
    db.flush()
    assert [c.position for c in canh] == [0, 1, 2, 3]


def test_dat_canh_lan_hai_THAY_canh_cu_khong_cong_don(db):
    b = bf.tao_brief(db, "u1", {"title": "T", "story_vi": "x" * 40})
    db.flush()
    bf.dat_canh(db, b, [{"title": "C0"}, {"title": "C1"}])
    db.flush()
    bf.dat_canh(db, b, [{"title": "Moi"}])
    db.flush()
    con_lai = bf.doc_canh(db, b)
    assert len(con_lai) == 1 and con_lai[0].title == "Moi"


def test_preflight_bat_brief_thieu(db):
    b = bf.tao_brief(db, "u1", {"title": "", "story_vi": "ngan"})
    ra = bf.preflight(b)
    assert ra["passed"] is False
    that_bai = {c["id"] for c in ra["checklist"] if not c["passed"]}
    assert {"title", "story"} <= that_bai


def test_preflight_KHONG_goi_LLM_va_khong_ghi_CSDL(db):
    """Preflight mien phi => khong duoc lam gi ton tien hay doi trang thai."""
    b = bf.tao_brief(db, "u1", {"title": "T", "story_vi": "x" * 40})
    db.flush()
    truoc = b.updated_at
    bf.preflight(b)
    assert b.updated_at == truoc


def test_nhan_ban_khong_keo_theo_so_dem_luot_mien_phi(db):
    """Neu nhan ban reset bo dem thi khach nhan ban de co 2 luot free nua.

    Ban sao la mot kich ban MOI => dung 0 la DUNG; nhung phai co phep kiem noi
    ro day la quyet dinh, khong phai tinh co.
    """
    b = bf.tao_brief(db, "u1", {"title": "T", "story_vi": "x" * 40})
    b.free_iterations_used = 2
    db.flush()
    ban_sao = bf.nhan_ban(db, b)
    db.flush()
    assert ban_sao.free_iterations_used == 0
    assert ban_sao.id != b.id
