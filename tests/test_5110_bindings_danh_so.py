"""services/bindings.py — dang so the theo spec Sec 6.3 quy tac 1.

Hai bo dem DOC LAP: image -> @IMAGE_1, @IMAGE_2...; video -> @VIDEO_1...
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'bindings.db').as_posix()}")
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


def _variant(db, owner="u1", resource_name="Nhân vật A"):
    from apps.prompt_ai_ommi.services import resources as rsvc
    resource = rsvc.create(db, owner_id=owner, kind="character", name=resource_name)
    variant = rsvc.add_variant(db, resource_id=resource.id, owner_id=owner,
                               storage_key=f"ommi/{owner}/{resource.id}/a.png")
    db.commit()
    return variant


def test_dang_so_hai_bo_dem_doc_lap(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v1, v2, v3 = _variant(db), _variant(db), _variant(db)
    created, changed = svc.replace_bindings(
        db, project_id="p1", owner_id="u1", scene_id="s1",
        items=[{"kind": "image", "variant_id": v1.id},
               {"kind": "video", "variant_id": v2.id},
               {"kind": "image", "variant_id": v3.id}])
    db.commit()
    assert changed == 3
    by_tag = {row.tag: row for row in created}
    assert set(by_tag) == {"@IMAGE_1", "@VIDEO_1", "@IMAGE_2"}
    assert by_tag["@IMAGE_1"].variant_id == v1.id
    assert by_tag["@IMAGE_2"].variant_id == v3.id


def test_role_mac_dinh_va_hop_le(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v1 = _variant(db)
    created, _ = svc.replace_bindings(
        db, project_id="p1", owner_id="u1", scene_id="s1",
        items=[{"kind": "image", "variant_id": v1.id}])
    assert created[0].role == "reference_image"


def test_role_khong_hop_le_bi_tu_choi(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v1 = _variant(db)
    with pytest.raises(svc.BindingError):
        svc.replace_bindings(
            db, project_id="p1", owner_id="u1", scene_id="s1",
            items=[{"kind": "image", "variant_id": v1.id, "role": "khong_ton_tai"}])
