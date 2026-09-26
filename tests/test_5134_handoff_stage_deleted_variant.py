"""Variant khong con ban ghi -> KHONG tieu so (spec Pha 2 Sec 6.3 rule 2).

Quy tac 2 KHAC quy tac 3, va gop hai cai la sai MOT CHIEU:
  - quy tac 2 (variant khong con ban ghi)  => KHONG tieu so  (tep nay)
  - quy tac 3 (con ban ghi, MAT TEP)       => CO tieu so     (test_5139)

Va mot the khong con tro tro toi dau thi phai BI XOA khoi prompt: de nguyen
thi `bat_bien_giao_bai` B-1 nem `ValueError` (HTTP 500) cho mot ca HOP LE, hoac
te hon — `@IMAGE_1` con lai chuan hoa thanh `image_1` trung voi handle cua
`@IMG_1` moi, nen B-1 im lang di qua trong khi prompt tro sai anh.
"""
from __future__ import annotations

import io

import pytest

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture()
def bienh(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hs-deleted.db').as_posix()}")
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


def _canh_hai_binding(db, *, variant_dau: str, owner_variant: str = "user_1"):
    """Binding 1 tro `variant_dau`, binding 2 tro mot variant CON va con tep."""
    import platform_core.storage as storage_mod
    from apps.prompt_ai_ommi.tables import OmmiBinding, OmmiResourceVariant
    storage_mod.get_storage().put("ommi/user_1/res/a.png", io.BytesIO(PNG),
                                  content_type="image/png")
    db.add(OmmiResourceVariant(id="var_con", resource_id="res_1",
                               owner_id="user_1",
                               storage_key="ommi/user_1/res/a.png"))
    if variant_dau != "var_da_xoa":
        db.add(OmmiResourceVariant(id=variant_dau, resource_id="res_1",
                                   owner_id=owner_variant,
                                   storage_key="ommi/user_1/res/a.png"))
    db.flush()
    db.add(OmmiBinding(owner_id="user_1", project_id="proj_1",
                       scene_id="scene_1", tag="@IMAGE_1", kind="image",
                       variant_id=variant_dau, position=1,
                       role="reference_image"))
    db.add(OmmiBinding(owner_id="user_1", project_id="proj_1",
                       scene_id="scene_1", tag="@IMAGE_2", kind="image",
                       variant_id="var_con", position=2,
                       role="reference_image"))
    db.commit()


def test_variant_xoa_han_khong_tieu_so(bienh):
    """Ca 2 cua brief: variant mat ban ghi."""
    db = bienh
    _canh_hai_binding(db, variant_dau="var_da_xoa")

    from apps.prompt_ai_ommi.services import handoff_stage as hs
    scene = {"id": "scene_1", "prompt": "Canh co @IMAGE_1 va @IMAGE_2",
             "camera": "", "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=_project(), scene=scene,
                              owner_id="user_1")

    # variant da xoa: khong trong tag_map, khong tieu @IMG_1, khong vao skipped
    assert "@IMAGE_1" not in payload["tag_map"]
    assert payload["tag_map"]["@IMAGE_2"] == "@IMG_1"
    assert payload["refs"][0]["handle"] == "@IMG_1"
    assert payload["skipped"] == []
    # the mo coi bi xoa khoi prompt, khong de nguyen (xem docstring dau tep)
    assert "@IMAGE_1" not in payload["prompt"]
    assert "@IMG_1" in payload["prompt"]


def test_variant_cua_nguoi_khac_khong_tieu_so(bienh):
    """Ca 4 cua brief: variant thuoc owner khac => nhu khong ton tai."""
    db = bienh
    _canh_hai_binding(db, variant_dau="var_nguoi_khac",
                      owner_variant="user_2")

    from apps.prompt_ai_ommi.services import handoff_stage as hs
    scene = {"id": "scene_1", "prompt": "Canh co @IMAGE_1 va @IMAGE_2",
             "camera": "", "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=_project(), scene=scene,
                              owner_id="user_1")

    assert "@IMAGE_1" not in payload["tag_map"]
    assert payload["tag_map"]["@IMAGE_2"] == "@IMG_1"
    assert len(payload["refs"]) == 1
    assert payload["skipped"] == []
    # ⭐ Doi chung: anh cua nguoi khac KHONG duoc lot vao refs duoi bat ky
    #    handle nao — do la mot ro ri du lieu, khong chi mot lech danh so.
    assert all(ref["handle"] == "@IMG_1" for ref in payload["refs"])


def test_binding_cua_nguoi_khac_khong_thay_duoc(bienh):
    """`list_bindings` loc theo owner: binding cua nguoi khac la vo hinh."""
    db = bienh
    _canh_hai_binding(db, variant_dau="var_khac")

    from apps.prompt_ai_ommi.services import handoff_stage as hs
    scene = {"id": "scene_1", "prompt": "Canh trong",
             "camera": "", "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=_project(), scene=scene,
                              owner_id="user_2")

    assert payload["refs"] == []
    assert payload["tag_map"] == {}
