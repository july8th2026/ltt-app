"""Anh qua 8MiB SAU chuan hoa: vao `skipped` co ly do, VA VAN tieu so.

Day la ca THAT (khach tai anh rat lon). Theo Sec 6.3 rule 3 no CO tieu so thu
tu — variant con ban ghi, chi la khong dung duoc.

Hai duong den cung mot ket cuc, ca hai duoc phu:
  1. `normalize_image()` tra bytes > `MAX_INLINE_BYTES` -> do nguong tuong minh;
  2. `image_to_inline()` nem `RefError` -> nhanh `except (OSError, RuntimeError,
     ValueError)`. ⭐ `handoff_stage` KHONG import ten `RefError` (no khong nam
     trong 5 ten `BE_MAT_CONG_KHAI`), nen phep kiem nay la cho duy nhat chung
     minh nhanh bat loi that su bao duoc no.
"""
from __future__ import annotations

import io

import pytest

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture()
def bienh(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hs-oversize.db').as_posix()}")
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


def _hai_anh(db):
    import platform_core.storage as storage_mod
    from apps.prompt_ai_ommi.tables import OmmiBinding, OmmiResourceVariant
    storage = storage_mod.get_storage()
    for ten, var in (("khong", "var_nho"), ("to", "var_to")):
        key = f"ommi/user_1/res/{ten}.png"
        storage.put(key, io.BytesIO(PNG), content_type="image/png")
        db.add(OmmiResourceVariant(id=var, resource_id="res_1",
                                   owner_id="user_1", storage_key=key))
    db.flush()
    db.add(OmmiBinding(owner_id="user_1", project_id="proj_1",
                       scene_id="scene_1", tag="@IMAGE_1", kind="image",
                       variant_id="var_nho", position=1,
                       role="reference_image"))
    db.add(OmmiBinding(owner_id="user_1", project_id="proj_1",
                       scene_id="scene_1", tag="@IMAGE_2", kind="image",
                       variant_id="var_to", position=2,
                       role="reference_image"))
    db.commit()


def _scene():
    return {"id": "scene_1", "prompt": "Dung @IMAGE_1 va @IMAGE_2",
            "camera": "", "lighting": "", "mood": ""}


def test_qua_nguong_sau_chuan_hoa_vao_skipped_va_tieu_so(bienh, monkeypatch):
    db = bienh
    _hai_anh(db)
    from apps.prompt_ai_ommi.services import handoff_stage as hs

    goc = hs.normalize_image

    def _gia_lap(data: bytes):
        _gia_lap.dem += 1
        if _gia_lap.dem == 2:  # anh thu hai: gia lap "van qua nguong"
            return b"\x00" * (hs.MAX_INLINE_BYTES + 1), "image/png"
        return goc(data)
    _gia_lap.dem = 0
    monkeypatch.setattr(hs, "normalize_image", _gia_lap)

    payload = hs.dung_payload(db, project=_project(), scene=_scene(),
                              owner_id="user_1")

    assert len(payload["refs"]) == 1
    assert payload["refs"][0]["handle"] == "@IMG_1"
    assert len(payload["skipped"]) == 1
    assert payload["skipped"][0]["variant_id"] == "var_to"
    assert payload["skipped"][0]["ly_do"] == (
        "anh vuot qua nguong inline sau chuan hoa")
    # var_to VAN tieu so @IMG_2 du khong co trong refs
    assert payload["tag_map"]["@IMAGE_2"] == "@IMG_2"
    assert "@IMG_2" in payload["prompt"]


def test_ref_error_cua_taovideo_duoc_bat_thanh_skipped(bienh, monkeypatch):
    db = bienh
    _hai_anh(db)
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    from apps.taovideo.refs import RefError

    goc = hs.image_to_inline

    def _gia_lap(data: bytes) -> str:
        _gia_lap.dem += 1
        if _gia_lap.dem == 2:
            raise RefError("anh > 8MiB — can asset:// / URL cong khai")
        return goc(data)
    _gia_lap.dem = 0
    monkeypatch.setattr(hs, "image_to_inline", _gia_lap)

    payload = hs.dung_payload(db, project=_project(), scene=_scene(),
                              owner_id="user_1")

    assert len(payload["refs"]) == 1
    assert len(payload["skipped"]) == 1
    assert payload["skipped"][0]["variant_id"] == "var_to"
    assert payload["skipped"][0]["ly_do"].startswith("khong doc duoc anh")
    assert payload["tag_map"]["@IMAGE_2"] == "@IMG_2"
