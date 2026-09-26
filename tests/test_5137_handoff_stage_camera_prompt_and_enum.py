"""Sec 6.2b: chi tiet tu do -> prompt nguyen van; enum chi la goi y THO, tat dinh.

Hai phep bat buoc theo spec:
1. `scene.camera` khac rong => prompt gui di PHAI CHUA `scene.camera` nguyen
   van (khong duoc chi khop enum roi bo chu goc — dung N-1 lan hai).
2. Goi hai lan cho CUNG MOT canh => CUNG MOT enum (`camera` nam trong
   `idempotency.key_fields` cua taovideo — khong tat dinh la tach doi job
   dedupe va khach tra tien hai lan).
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def bienh(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hs-camera.db').as_posix()}")
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


def _project(style_id="cinematic"):
    from types import SimpleNamespace
    return SimpleNamespace(id="proj_1",
                           payload={"brief": {"style_id": style_id}})


def test_camera_tu_do_giu_nguyen_van_trong_prompt(bienh):
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    scene = {"id": "scene_1",
             "prompt": "Mot canh binh minh tren nui",
             "camera": "medium shot, 35mm, slow dolly in",
             "lighting": "anh sang vang buoi som",
             "mood": "yen binh, cham rai"}
    payload = hs.dung_payload(db, project=_project(), scene=scene,
                              owner_id="user_1")

    assert "medium shot, 35mm, slow dolly in" in payload["prompt"]
    assert "anh sang vang buoi som" in payload["prompt"]
    assert "yen binh, cham rai" in payload["prompt"]
    assert "Mot canh binh minh tren nui" in payload["prompt"]
    # goi y enum: "dolly" -> dolly_in; "cham" -> subtle
    assert payload["params"]["camera"] == "dolly_in"
    assert payload["params"]["motion"] == "subtle"
    # `params["prompt"]` va `payload["prompt"]` la MOT chuoi, khong hai ban
    assert payload["params"]["prompt"] == payload["prompt"]


def test_truong_rong_khong_sinh_nhan_trong(bienh):
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    scene = {"id": "scene_1", "prompt": "canh don gian",
             "camera": "aerial drone shot", "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=_project(), scene=scene,
                              owner_id="user_1")
    assert "Lighting:" not in payload["prompt"]
    assert "Mood:" not in payload["prompt"]
    assert "Camera: aerial drone shot." in payload["prompt"]


def test_camera_khong_khop_tu_khoa_nao_ra_rong(bienh):
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    scene = {"id": "scene_1", "prompt": "canh don gian",
             "camera": "mot cau mo ta khong lien quan gi toi may quay",
             "lighting": "", "mood": ""}
    payload = hs.dung_payload(db, project=_project(), scene=scene,
                              owner_id="user_1")
    assert payload["params"]["camera"] == ""
    assert payload["params"]["motion"] == ""
    # ... nhung chu goc VAN o trong prompt.
    assert "mot cau mo ta khong lien quan gi toi may quay" in payload["prompt"]


def test_goi_hai_lan_cung_canh_ra_cung_mot_enum(bienh):
    """Tat dinh: khong LLM, khong phu thuoc thu tu khong xac dinh."""
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    scene = {"id": "scene_1", "prompt": "canh",
             "camera": "static camera roi dolly in, handheld o cuoi",
             "lighting": "", "mood": ""}
    khoa = ("camera", "motion", "visual_style", "prompt")
    lan_mot = hs.dung_payload(db, project=_project(), scene=dict(scene),
                              owner_id="user_1")
    lan_hai = hs.dung_payload(db, project=_project(), scene=dict(scene),
                              owner_id="user_1")
    assert ({k: lan_mot["params"][k] for k in khoa}
            == {k: lan_hai["params"][k] for k in khoa})
    # Van ban khop NHIEU tu khoa: luat "khop dau tien thang" tren bang co thu
    # tu co dinh => lap lai bao nhieu lan cung mot ket qua.
    ket_qua = {hs._doan_enum(scene["camera"], hs._CAMERA_VALUES,
                             hs._CAMERA_TU_KHOA) for _ in range(50)}
    assert ket_qua == {"dolly_in"}


def test_visual_style_lay_tu_brief_khong_ghi_de_cinematic(bienh):
    """N-1: `visual_style` truoc day bi ghi de cung `"cinematic"`."""
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    scene = {"id": "scene_1", "prompt": "canh", "camera": "", "lighting": "",
             "mood": ""}
    anime = hs.dung_payload(db, project=_project("anime"), scene=scene,
                            owner_id="user_1")
    assert anime["params"]["visual_style"] == "anime"


def test_params_chi_chua_khoa_co_trong_params_schema(bienh):
    """Sec 6.2c — di QUA `validate_tool_params`, khong doc `params` roi doan.

    Mot khoa bao cao them trong `params` bien MOI luot giao bai thanh 422; goi
    `dung_payload` roi tu so bo khoa la doc thu DAI DIEN, khong phai thu that.
    """
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    from platform_core.agent.tools import validate_tool_params
    from platform_core.registry import discover

    scene = {"id": "scene_1", "prompt": "canh binh minh",
             "camera": "aerial drone", "lighting": "vang", "mood": "cham"}
    payload = hs.dung_payload(db, project=_project(), scene=scene,
                              owner_id="user_1")

    loaded = discover()
    clean = validate_tool_params("video.generate", payload["params"],
                                 apps=loaded)
    assert clean["camera"] == "aerial"
    assert clean["prompt"] == payload["prompt"]


def test_banh_coc_enum_khop_manifest_taovideo():
    """Hai cho khai cung mot dieu thi phai co nguoi bat khop.

    Ban sinh doi cua `tests/test_5132_...::test_banh_coc_enum_khop_manifest_taovideo`
    — ⛔ KHONG phai mot ban sao: tep kia chot ba bo enum o `routes/handoff.py`
    (noi Pha 1 dat chung), tep nay chot chung o `services/handoff_stage.py`
    (noi Pha 2 chuyen chung den). Neu ai do go bo lop re-export o `routes`, tep
    kia do va tep nay xanh — do chinh la thong tin can biet.
    """
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    from apps.taovideo.manifest import MANIFEST as TAOVIDEO

    spec = next(t for t in TAOVIDEO.tools if t.name == "video.generate")
    that = spec.params_schema
    assert list(hs._CAMERA_VALUES) == list(that["camera"]["values"])
    assert list(hs._MOTION_VALUES) == list(that["motion"]["values"])
    assert list(hs._VISUAL_STYLE_VALUES) == list(that["visual_style"]["values"])
    for bang, bo in ((hs._CAMERA_TU_KHOA, that["camera"]["values"]),
                     (hs._MOTION_TU_KHOA, that["motion"]["values"]),
                     (hs._STYLE_TU_KHOA, that["visual_style"]["values"])):
        for _tu, gia_tri in bang:
            assert gia_tri in bo, f"{gia_tri!r} khong co trong enum that"
