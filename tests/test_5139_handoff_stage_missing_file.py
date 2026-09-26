"""Anh mat tep van TIEU SO thu tu va vao `skipped` (spec Pha 2 Sec 6.3 rule 3).

Day la phep KHONG duoc thieu theo brief: dung canh co 2 anh, mot anh mat tep,
khang dinh anh mat tep CO tieu so thu tu va co mat trong `skipped`.
"""
from __future__ import annotations

import io

import pytest

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture()
def bienh(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hs-missing.db').as_posix()}")
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db, storage_mod.get_storage()
    db.close()
    dbmod.reset_engine()
    storage_mod.set_storage(None)


def _project(project_id="proj_1"):
    from types import SimpleNamespace
    return SimpleNamespace(
        id=project_id,
        payload={"brief": {"aspect_ratio": "16:9", "style_id": "cinematic"}})


def test_mat_tep_van_tieu_so_va_vao_skipped(bienh):
    db, storage = bienh
    from apps.prompt_ai_ommi.tables import OmmiBinding, OmmiResourceVariant
    storage.put("ommi/user_1/res/keep.png", io.BytesIO(PNG),
                content_type="image/png")
    db.add(OmmiResourceVariant(id="var_con", resource_id="res_1",
                               owner_id="user_1",
                               storage_key="ommi/user_1/res/keep.png"))
    db.add(OmmiResourceVariant(id="var_mat", resource_id="res_1",
                               owner_id="user_1",
                               storage_key="ommi/user_1/res/da-xoa.png"))
    db.flush()
    db.add(OmmiBinding(owner_id="user_1", project_id="proj_1",
                       scene_id="scene_1", tag="@IMAGE_1", kind="image",
                       variant_id="var_con", position=1,
                       role="reference_image"))
    db.add(OmmiBinding(owner_id="user_1", project_id="proj_1",
                       scene_id="scene_1", tag="@IMAGE_2", kind="image",
                       variant_id="var_mat", position=2,
                       role="reference_image"))
    db.commit()

    from apps.prompt_ai_ommi.services import handoff_stage as hs
    scene = {"id": "scene_1", "prompt": "Canh co @IMAGE_1 va @IMAGE_2",
             "camera": "", "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=_project(), scene=scene,
                              owner_id="user_1")

    assert len(payload["refs"]) == 1
    assert payload["refs"][0]["handle"] == "@IMG_1"
    assert payload["refs"][0]["url"].startswith("data:image/png;base64,")
    assert len(payload["skipped"]) == 1
    assert payload["skipped"][0]["variant_id"] == "var_mat"
    assert payload["skipped"][0]["ly_do"] == "tep khong ton tai"
    # anh mat tep VAN tieu so: no chiem @IMG_2, khong bi bo qua trong tag_map
    assert payload["tag_map"]["@IMAGE_2"] == "@IMG_2"
    assert "@IMG_1" in payload["prompt"] and "@IMG_2" in payload["prompt"]
    assert "@IMAGE_" not in payload["prompt"]


def test_payload_dung_sau_khoa_cap_ngoai_khong_nhet_vao_params(bienh):
    """Sec 6.2c: `tag_map`/`skipped`/`skipped_over_limit` nam NGANG `params`."""
    db, _storage = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    scene = {"id": "scene_1", "prompt": "canh khong co anh",
             "camera": "", "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=_project(), scene=scene,
                              owner_id="user_1")

    assert set(payload) == {"prompt", "params", "refs", "tag_map", "skipped",
                            "skipped_over_limit"}
    for khoa in ("tag_map", "skipped", "skipped_over_limit"):
        assert khoa not in payload["params"]
