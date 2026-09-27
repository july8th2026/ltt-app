"""Pha 3 -- nhan vat. Trong tam: `fixed_prompt_block` la thu giu nhan vat khong doi.

Neu khoi chu do khong di vao prompt cua MOI canh thi ca tinh nang khoa nhan vat
khong lam gi ca -- va khong test nao bao, vi khoi chu VAN duoc luu. (Buoc di
vao prompt duoc chot o test_5342, tach rieng vi no cham `services/composer.py`.)
"""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services import nhan_vat as nv


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'nhan_vat.db').as_posix()}")
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


def test_tao_va_doc(db):
    c = nv.tao(db, "u1", {"name": "Ong Ngoai", "face_description": "rau bac"})
    db.flush()
    assert nv.doc(db, c.id, "u1").name == "Ong Ngoai"


def test_doc_cua_nguoi_khac_bi_tu_choi(db):
    c = nv.tao(db, "u1", {"name": "A"}); db.flush()
    with pytest.raises(KeyError):
        nv.doc(db, c.id, "u2")


def test_chay_khoa_nhan_vat_nem_khi_thieu_mo_ta():
    """⛔ Phai NEM, khong tra rong: nen tang dua vao exception de hoan credit."""
    with pytest.raises(ValueError):
        nv.chay_khoa_nhan_vat({"name": "", "face_description": ""})


def test_chay_khoa_nhan_vat_khong_gui_placeholder_nguyen_van(monkeypatch):
    """⭐ Doi chung cho bo kiem placeholder: loi nhac gui di khong con `{NAME}`."""
    da_gui = {}

    def _gia(system, prompt, model=""):
        da_gui["prompt"] = prompt
        return ({"fixed_prompt_block": "an old man", "negative_notes": ""}, 10)

    from apps.prompt_ai_ommi import provider
    monkeypatch.setattr(provider, "generate_json", _gia)
    monkeypatch.setattr(provider, "model_mac_dinh", lambda: "m")
    nv.chay_khoa_nhan_vat({"name": "Ong Ngoai", "face_description": "rau bac",
                           "gender": "nam", "age_range": "70",
                           "body_description": "gay", "hair_description": "bac",
                           "outfit_description": "ao nau",
                           "personality": "diem tinh", "expression_style": "it noi",
                           "movement_style": "cham", "negative_notes": "khong kinh"})
    from apps.prompt_ai_ommi.services.placeholders import tim_placeholder
    assert tim_placeholder(da_gui["prompt"]) == []


def test_boi_canh_cung_khuon(db):
    b = nv.tao_boi_canh(db, "u1", {"name": "Phong khach",
                                   "environment_description": "am"})
    db.flush()
    assert nv.doc_boi_canh(db, b.id, "u1").name == "Phong khach"
