"""S-4 -- binding pha 1 phai song sot khi canh chuyen tu payload sang `ommi_canh`.

Neu phep nay do, nghia la moi anh tham chieu khach da gan o pha 1/2 tro thanh
hu khong ngay khi pha 3 len production. Khong ai bao loi vi chang ai xem lai
prompt cu -- dung dang loi `cho-noi-hai-module-vut-truong-im-lang`.
"""
from __future__ import annotations

import pytest

from apps.prompt_ai_ommi.services import bindings as bd
from apps.prompt_ai_ommi.services import briefs as bf

ID_CANH_CU = "scene_9f1c2ab30de4"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'binding_song_sot.db').as_posix()}")
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
def du_an():
    from types import SimpleNamespace
    return SimpleNamespace(id="p1", user_id="u1")


@pytest.fixture()
def variant(db):
    from apps.prompt_ai_ommi.services import resources as rsvc
    resource = rsvc.create(db, owner_id="u1", kind="character", name="Nhan vat A")
    v = rsvc.add_variant(db, resource_id=resource.id, owner_id="u1",
                         storage_key=f"ommi/u1/{resource.id}/a.png")
    db.flush()
    return v


def test_binding_tro_vao_id_canh_cu_van_tim_ra_canh_sau_pha_3(db, du_an, variant):
    # Pha 1/2: canh nam trong payload, binding tro vao id do.
    bd.replace_bindings(db, project_id=du_an.id, owner_id=du_an.user_id,
                        scene_id=ID_CANH_CU,
                        items=[{"kind": "image", "variant_id": variant.id}])
    db.flush()

    # Pha 3: chuyen canh sang bang, TAI DUNG dung id cu.
    b = bf.tao_brief(db, du_an.user_id,
                     {"title": "T", "story_vi": "x" * 40, "project_id": du_an.id})
    db.flush()
    bf.dat_canh(db, b, [{"id": ID_CANH_CU, "title": "Canh 1", "prompt": "p"}])
    db.flush()

    canh = bf.doc_canh(db, b)
    assert canh[0].id == ID_CANH_CU
    ds = bd.list_bindings(db, project_id=du_an.id, owner_id=du_an.user_id,
                     scene_id=ID_CANH_CU)
    assert len(ds) == 1 and ds[0].variant_id == variant.id
    assert bool(bd.list_bindings(db, project_id=du_an.id,
                                 owner_id=du_an.user_id,
                                 scene_id=ID_CANH_CU)) is True


def test_doi_chung_sinh_id_moi_thi_binding_MAT(db, du_an, variant):
    """Tiem loi: neu `dat_canh` sinh id moi thi binding khong con tro vao dau.

    Khong co phep doi chung nay thi phep tren co the xanh chi vi
    `list_bindings` luon tra rong -- `khong-doi-chung-thi-so-khong-khong-phai-phat-hien`.
    """
    bd.replace_bindings(db, project_id=du_an.id, owner_id=du_an.user_id,
                        scene_id=ID_CANH_CU,
                        items=[{"kind": "image", "variant_id": variant.id}])
    db.flush()
    b = bf.tao_brief(db, du_an.user_id,
                     {"title": "T", "story_vi": "x" * 40, "project_id": du_an.id})
    db.flush()
    canh = bf.dat_canh(db, b, [{"title": "Canh 1"}])   # KHONG truyen id
    db.flush()
    assert canh[0].id != ID_CANH_CU
    assert bd.list_bindings(db, project_id=du_an.id, owner_id=du_an.user_id,
                            scene_id=canh[0].id) == []
