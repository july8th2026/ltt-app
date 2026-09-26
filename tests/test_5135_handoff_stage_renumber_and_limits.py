"""Tran 9 anh + 3 video, va danh so lai the (spec Pha 2 Sec 6.2b/6.3).

Vuot tran KHONG phai loi: cat bot, dem vao `skipped_over_limit` o cap PAYLOAD
(khong trong `params` — Sec 6.2c).
"""
from __future__ import annotations

import io

import pytest

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture()
def bienh(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hs-limit.db').as_posix()}")
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close()
    dbmod.reset_engine()
    storage_mod.set_storage(None)


def _project():
    from types import SimpleNamespace
    return SimpleNamespace(id="proj_1", payload={"brief": {}})


def _them(db, storage, *, so: int, kind: str, tien_to: str):
    from apps.prompt_ai_ommi.tables import OmmiBinding, OmmiResourceVariant
    for i in range(so):
        key = f"ommi/user_1/res/{kind}-{i}.png"
        storage.put(key, io.BytesIO(PNG), content_type="image/png")
        db.add(OmmiResourceVariant(id=f"var_{kind}_{i}", resource_id="res_1",
                                   owner_id="user_1", storage_key=key))
        db.add(OmmiBinding(owner_id="user_1", project_id="proj_1",
                           scene_id="scene_1", tag=f"@{tien_to}_{i + 1}",
                           kind=kind, variant_id=f"var_{kind}_{i}",
                           position=i + 1, role="reference_image"))


def test_muoi_hai_anh_cat_con_chin_va_dem_ba(bienh):
    db = bienh
    import platform_core.storage as storage_mod
    _them(db, storage_mod.get_storage(), so=12, kind="image", tien_to="IMAGE")
    db.commit()

    from apps.prompt_ai_ommi.services import handoff_stage as hs
    # Prompt nhac DU 12 the: bat bien B-2 doi moi ref phai duoc prompt nhac,
    # va ba the bi cat phai bien khoi prompt.
    the = " ".join(f"@IMAGE_{i + 1}" for i in range(12))
    scene = {"id": "scene_1", "prompt": f"canh nhieu anh {the}",
             "camera": "", "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=_project(), scene=scene,
                              owner_id="user_1")

    assert payload["skipped_over_limit"] == 3
    assert len(payload["refs"]) == 9
    assert [r["handle"] for r in payload["refs"]] == [
        f"@IMG_{i + 1}" for i in range(9)]
    assert "@IMAGE_" not in payload["prompt"]
    assert "@IMG_10" not in payload["prompt"]
    assert "skipped_over_limit" not in payload["params"]


def test_bon_video_cat_con_ba_va_hai_bo_dem_doc_lap(bienh):
    """Sec 6.3 rule 1: `image` va `video` dem RIENG, khong chung mot bo dem."""
    db = bienh
    import platform_core.storage as storage_mod
    storage = storage_mod.get_storage()
    _them(db, storage, so=2, kind="image", tien_to="IMAGE")
    _them(db, storage, so=4, kind="video", tien_to="VIDEO")
    db.commit()

    from apps.prompt_ai_ommi.services import handoff_stage as hs
    the = "@IMAGE_1 @IMAGE_2 @VIDEO_1 @VIDEO_2 @VIDEO_3 @VIDEO_4"
    scene = {"id": "scene_1", "prompt": f"canh {the}",
             "camera": "", "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=_project(), scene=scene,
                              owner_id="user_1")

    assert payload["skipped_over_limit"] == 1  # 4 video - tran 3
    assert payload["tag_map"] == {"@IMAGE_1": "@IMG_1", "@IMAGE_2": "@IMG_2",
                                  "@VIDEO_1": "@VID_1", "@VIDEO_2": "@VID_2",
                                  "@VIDEO_3": "@VID_3"}
    assert [r["kind"] for r in payload["refs"]] == (
        ["image"] * 2 + ["video"] * 3)
    assert all(r["role"] == "reference_video"
               for r in payload["refs"] if r["kind"] == "video")
    assert "@VIDEO_4" not in payload["prompt"]


def test_doi_tag_khong_nuot_nham_muoi_voi_mot(bienh):
    """`@IMAGE_1` va `[Image 10]` khong duoc va cham (bay tag/collision)."""
    db = bienh
    import platform_core.storage as storage_mod
    from apps.prompt_ai_ommi.tables import OmmiBinding, OmmiResourceVariant
    storage = storage_mod.get_storage()
    for ten in ("a", "b"):
        storage.put(f"ommi/user_1/res/{ten}.png", io.BytesIO(PNG),
                    content_type="image/png")
    db.add(OmmiResourceVariant(id="var_1", resource_id="res_1",
                               owner_id="user_1",
                               storage_key="ommi/user_1/res/a.png"))
    db.add(OmmiResourceVariant(id="var_10", resource_id="res_1",
                               owner_id="user_1",
                               storage_key="ommi/user_1/res/b.png"))
    db.flush()
    db.add(OmmiBinding(owner_id="user_1", project_id="proj_1",
                       scene_id="scene_1", tag="@IMAGE_1", kind="image",
                       variant_id="var_1", position=1, role="reference_image"))
    db.add(OmmiBinding(owner_id="user_1", project_id="proj_1",
                       scene_id="scene_1", tag="@IMAGE_10", kind="image",
                       variant_id="var_10", position=2, role="reference_image"))
    db.commit()

    from apps.prompt_ai_ommi.services import handoff_stage as hs
    scene = {"id": "scene_1",
             "prompt": "Dung @IMAGE_1 va [Image 10] trong cung canh",
             "camera": "", "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=_project(), scene=scene,
                              owner_id="user_1")

    assert payload["tag_map"]["@IMAGE_1"] == "@IMG_1"
    assert payload["tag_map"]["@IMAGE_10"] == "@IMG_2"
    assert "@IMG_1" in payload["prompt"]
    assert "@IMG_2" in payload["prompt"]
    assert "@IMAGE_1" not in payload["prompt"]
    assert "@IMAGE_10" not in payload["prompt"]
    # Sec 6.3 rule 4: dang ngoac vuong cua ban goc cung phai duoc doi.
    assert "[Image 10]" not in payload["prompt"]
