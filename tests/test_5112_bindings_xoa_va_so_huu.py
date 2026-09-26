"""delete_binding + binding_lines() — Sec 6.1 DELETE va cau noi cho composer."""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'bindings3.db').as_posix()}")
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


def _variant(db, owner="u1", name="Nhân vật A", desc="ao xanh"):
    from apps.prompt_ai_ommi.services import resources as rsvc
    resource = rsvc.create(db, owner_id=owner, kind="character", name=name, description=desc)
    variant = rsvc.add_variant(db, resource_id=resource.id, owner_id=owner,
                               storage_key=f"ommi/{owner}/{resource.id}/a.png",
                               label="goc nghieng")
    db.commit()
    return variant


def test_xoa_dung_tag_con_lai_ban_ghi_khac(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v1, v2 = _variant(db), _variant(db)
    svc.replace_bindings(db, project_id="p1", owner_id="u1", scene_id="s1",
                         items=[{"kind": "image", "variant_id": v1.id},
                               {"kind": "image", "variant_id": v2.id}])
    db.commit()
    remaining = svc.delete_binding(db, project_id="p1", owner_id="u1",
                                  scene_id="s1", tag="@IMAGE_1")
    assert [row.tag for row in remaining] == ["@IMAGE_2"]


def test_xoa_tag_khong_ton_tai_nem_binding_not_found(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    with pytest.raises(svc.BindingNotFound):
        svc.delete_binding(db, project_id="p1", owner_id="u1", scene_id="s1",
                          tag="@IMAGE_9")


def test_binding_lines_doc_ten_va_mo_ta_tu_variant_va_resource(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v1 = _variant(db, name="Nhân vật A", desc="ao xanh")
    svc.replace_bindings(db, project_id="p1", owner_id="u1", scene_id="s1",
                         items=[{"kind": "image", "variant_id": v1.id}])
    db.commit()
    lines = svc.binding_lines(db, project_id="p1", owner_id="u1", scene_id="s1")
    assert lines == [{"tag": "@IMAGE_1", "kind": "image",
                     "name": "goc nghieng", "description": "ao xanh"}]
