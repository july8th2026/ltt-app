"""Spec Sec 6.3 quy tac 2: variant khong con ban ghi thi KHONG tieu so."""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'bindings2.db').as_posix()}")
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


def _variant(db, owner="u1"):
    from apps.prompt_ai_ommi.services import resources as rsvc
    resource = rsvc.create(db, owner_id=owner, kind="prop", name="Do vat")
    variant = rsvc.add_variant(db, resource_id=resource.id, owner_id=owner,
                               storage_key=f"ommi/{owner}/{resource.id}/a.png")
    db.commit()
    return variant


def test_variant_khong_ton_tai_khong_tieu_so(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v1, v2 = _variant(db), _variant(db)
    created, changed = svc.replace_bindings(
        db, project_id="p1", owner_id="u1", scene_id="s1",
        items=[{"kind": "image", "variant_id": v1.id},
               {"kind": "image", "variant_id": "khong-ton-tai"},
               {"kind": "image", "variant_id": v2.id}])
    assert changed == 2
    tags = sorted(row.tag for row in created)
    assert tags == ["@IMAGE_1", "@IMAGE_2"], (
        "variant vang mat khong duoc chiem mot so — @IMAGE_2 phai thuoc ve v2, "
        "khong phai nhay len @IMAGE_3")


def test_variant_cua_nguoi_khac_khong_tieu_so(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v_cua_a = _variant(db, owner="a")
    v_cua_b = _variant(db, owner="b")
    created, changed = svc.replace_bindings(
        db, project_id="p1", owner_id="a", scene_id="s1",
        items=[{"kind": "image", "variant_id": v_cua_a.id},
               {"kind": "image", "variant_id": v_cua_b.id}])
    assert changed == 1
    assert created[0].variant_id == v_cua_a.id


def test_put_la_ghi_de_toan_bo_khong_phai_them(db):
    from apps.prompt_ai_ommi.services import bindings as svc
    v1, v2 = _variant(db), _variant(db)
    svc.replace_bindings(db, project_id="p1", owner_id="u1", scene_id="s1",
                         items=[{"kind": "image", "variant_id": v1.id}])
    db.commit()
    created, changed = svc.replace_bindings(
        db, project_id="p1", owner_id="u1", scene_id="s1",
        items=[{"kind": "image", "variant_id": v2.id}])
    db.commit()
    assert changed == 1
    remaining = svc.list_bindings(db, project_id="p1", owner_id="u1", scene_id="s1")
    assert [row.variant_id for row in remaining] == [v2.id], (
        "PUT phai la GHI DE TOAN BO (spec 6.1) — v1 phai bien mat sau lan PUT thu hai")
