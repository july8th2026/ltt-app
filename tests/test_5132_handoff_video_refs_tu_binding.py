"""N-1 (spec Sec 6.2): handoff video khong con `refs: []` va khong con ghi
de cung "cinematic" cho moi canh — gia tri phai lay tu scene/binding that.

Va (spec Sec 6.2b) hai duong SONG SONG, khong duoc chi co mot:
  1. chi tiet day du cua canh di vao `prompt` NGUYEN VAN;
  2. enum chi la goi y tho, suy ra TAT DINH, khong khop thi `""`.
Chi lam duong 2 la vut truong im lang LAN THU HAI — dung con bo dang chua.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'handoff_n1.db').as_posix()}")
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


class _FakeStorage:
    """Storage gia — chi doc lai bytes da 'put' truoc do, khong dung o dia that."""

    def __init__(self):
        self._data: dict[str, bytes] = {}

    def put_test(self, key: str, data: bytes) -> None:
        self._data[key] = data

    def exists(self, key: str) -> bool:
        return key in self._data

    def open(self, key: str):
        import io
        return io.BytesIO(self._data[key])


def _du_lieu_anh_1x1_png() -> bytes:
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "+A8AAQUBAScY42YAAAAASUVORK5CYII=")


_CAMERA_GOC = "medium shot, 35mm, tu tu dolly toi gan nhan vat"
_MOOD_GOC = "dynamic va cang thang"
_LIGHTING_GOC = "anh neon xanh tu ben trai"


def _du_an_va_canh(db, monkeypatch):
    from apps.prompt_ai_ommi.services import resources as rsvc
    from apps.prompt_ai_ommi.services import bindings as bsvc
    from platform_core import app_projects
    from apps.prompt_ai_ommi.manifest import MANIFEST
    from apps.prompt_ai_ommi.project_schema import empty_project

    fake = _FakeStorage()
    monkeypatch.setattr("platform_core.storage.get_storage", lambda: fake)

    resource = rsvc.create(db, owner_id="khach1", kind="character", name="A")
    variant = rsvc.add_variant(db, resource_id=resource.id, owner_id="khach1",
                               storage_key="ommi/khach1/r1/a.png")
    fake.put_test(variant.storage_key, _du_lieu_anh_1x1_png())

    payload = empty_project("Du an test")
    payload["brief"]["style_id"] = "anime"
    payload["scenes"] = [{"id": "scene1", "order": 0, "title": "Canh 1",
                          "prompt": "Nhan vat @IMAGE_1 buoc vao phong.",
                          "camera": _CAMERA_GOC,
                          "mood": _MOOD_GOC, "lighting": _LIGHTING_GOC,
                          "continuity": "", "duration_seconds": 5,
                          "versions": [], "selected_version": 0}]
    project = app_projects.create(db, user_id="khach1", app_slug=MANIFEST.slug,
                                  name="Du an test", schema_version=1, payload=payload)
    db.commit()

    bsvc.replace_bindings(db, project_id=project.id, owner_id="khach1",
                          scene_id="scene1",
                          items=[{"kind": "image", "variant_id": variant.id}])
    db.commit()
    return project


def test_refs_khong_con_rong_va_camera_motion_tu_canh(db, monkeypatch):
    from apps.prompt_ai_ommi.routes.handoff import _handoff_params

    project = _du_an_va_canh(db, monkeypatch)
    scene = project.payload["scenes"][0]
    tool_name, params = _handoff_params(db, "khach1", project, scene, "video", {})

    assert tool_name == "video.generate"
    assert len(params["refs"]) == 1
    assert params["refs"][0]["handle"] == "image_1"
    assert params["refs"][0]["url"].startswith("data:image/")
    assert params["camera"] == "dolly_in"   # "dolly" trong van ban tu do
    assert params["motion"] == "dynamic"    # "dynamic" trong "dynamic va cang thang"
    assert params["visual_style"] == "anime"


def test_prompt_chua_NGUYEN_VAN_camera_lighting_mood(db, monkeypatch):
    """Spec Sec 6.2b luat 1. Chi khop enum roi bo chu goc la mat du lieu LAN
    HAI: `"medium shot, 35mm"` khong co cho nao trong enum `camera`, neu khong
    ghep vao prompt thi no bien mat khong ai biet."""
    from apps.prompt_ai_ommi.routes.handoff import _handoff_params

    project = _du_an_va_canh(db, monkeypatch)
    scene = project.payload["scenes"][0]
    _, params = _handoff_params(db, "khach1", project, scene, "video", {})

    assert _CAMERA_GOC in params["prompt"]
    assert _LIGHTING_GOC in params["prompt"]
    assert _MOOD_GOC in params["prompt"]
    assert "Nhan vat @IMAGE_1 buoc vao phong." in params["prompt"]
    assert len(params["prompt"]) <= 10000


def test_truong_rong_khong_sinh_nhan_trong(db, monkeypatch):
    """Chi ghep nhan cua truong KHAC RONG — `Lighting: .` la rac gui cho model."""
    from apps.prompt_ai_ommi.routes.handoff import _handoff_params

    project = _du_an_va_canh(db, monkeypatch)
    scene = dict(project.payload["scenes"][0])
    scene["lighting"] = ""
    scene["mood"] = ""
    _, params = _handoff_params(db, "khach1", project, scene, "video", {})

    assert "Lighting:" not in params["prompt"]
    assert "Mood:" not in params["prompt"]
    assert f"Camera: {_CAMERA_GOC}." in params["prompt"]


def test_enum_suy_ra_TAT_DINH_hai_lan_cung_ket_qua(db, monkeypatch):
    """`camera` nam trong `idempotency.key_fields` cua taovideo: hai lan giao
    bai cung mot canh phai cho CUNG mot enum, neu khong dedupe job tach doi va
    khach tra tien hai lan."""
    from apps.prompt_ai_ommi.routes.handoff import _handoff_params, _doan_enum
    from apps.prompt_ai_ommi.routes import handoff as mod

    project = _du_an_va_canh(db, monkeypatch)
    scene = project.payload["scenes"][0]
    _, lan1 = _handoff_params(db, "khach1", project, scene, "video", {})
    _, lan2 = _handoff_params(db, "khach1", project, scene, "video", {})
    khoa = ("camera", "motion", "visual_style", "prompt")
    assert {k: lan1[k] for k in khoa} == {k: lan2[k] for k in khoa}

    # Van ban khop NHIEU tu khoa: luat "khop dau tien thang" tren bang co thu
    # tu co dinh => lap lai bao nhieu lan cung mot ket qua.
    nhap_nhang = "static camera roi dolly in, handheld o cuoi"
    ket_qua = {_doan_enum(nhap_nhang, mod._CAMERA_VALUES, mod._CAMERA_TU_KHOA)
               for _ in range(50)}
    assert len(ket_qua) == 1


def test_khong_khop_tu_khoa_nao_thi_enum_la_chuoi_rong(db, monkeypatch):
    """Spec Sec 6.2b luat 2: khong bao gio doan mot enum khac. `""` hop le."""
    from apps.prompt_ai_ommi.routes.handoff import _handoff_params

    project = _du_an_va_canh(db, monkeypatch)
    scene = dict(project.payload["scenes"][0])
    scene["camera"] = "goc nhin la lung khong ten"
    scene["mood"] = "khong the goi ten"
    _, params = _handoff_params(db, "khach1", project, scene, "video", {})

    assert params["camera"] == ""
    assert params["motion"] == ""
    # ... nhung chu goc VAN o trong prompt.
    assert "goc nhin la lung khong ten" in params["prompt"]


def test_params_chi_chua_khoa_co_trong_params_schema(db, monkeypatch):
    """`validate_tool_params` TU CHOI moi khoa la ("tham so khong duoc phep")
    => mot khoa bao cao them trong `params` bien MOI lan giao bai video thanh
    422. Plan Task 8 dua `skipped_over_limit` vao `params`; phep kiem nay la
    cho duy nhat bat duoc dieu do (test goi `_handoff_params` truc tiep ma
    khong qua `validate_tool_params` thi khong bao gio thay)."""
    from apps.prompt_ai_ommi.routes.handoff import _handoff_params
    from apps.taovideo.manifest import MANIFEST as TAOVIDEO

    project = _du_an_va_canh(db, monkeypatch)
    scene = project.payload["scenes"][0]
    _, params = _handoff_params(db, "khach1", project, scene, "video", {})

    spec = next(t for t in TAOVIDEO.tools if t.name == "video.generate")
    assert set(params) <= set(spec.params_schema), (
        f"khoa la: {sorted(set(params) - set(spec.params_schema))}")


def test_banh_coc_enum_khop_manifest_taovideo():
    """Hai cho khai cung mot dieu thi phai co nguoi bat khop.

    `routes/handoff.py` khai LAI literal ba bo enum cua taovideo, vi be mat
    app->app (`apps/taovideo/__init__.py::BE_MAT_CONG_KHAI`) chi mo 5 ten
    trong `apps.taovideo.refs` — doc `manifest` cua app khac la mo mot canh
    khong ai kiem. Tep test thi duoc import ca hai app (`.importlinter` cai
    quan goi `apps/`, khong cai quan `tests/`), nen cho doi chieu la o day.
    """
    from apps.prompt_ai_ommi.routes import handoff as mod
    from apps.taovideo.manifest import MANIFEST as TAOVIDEO

    spec = next(t for t in TAOVIDEO.tools if t.name == "video.generate")
    that = spec.params_schema
    assert list(mod._CAMERA_VALUES) == list(that["camera"]["values"])
    assert list(mod._MOTION_VALUES) == list(that["motion"]["values"])
    assert list(mod._VISUAL_STYLE_VALUES) == list(that["visual_style"]["values"])

    # Va moi gia tri bang tu khoa tro den phai nam trong bo enum that: mot tu
    # khoa tro sai la mot 422 cho khach.
    for bang, bo in ((mod._CAMERA_TU_KHOA, that["camera"]["values"]),
                     (mod._MOTION_TU_KHOA, that["motion"]["values"]),
                     (mod._STYLE_TU_KHOA, that["visual_style"]["values"])):
        for _tu, gia_tri in bang:
            assert gia_tri in bo, f"{gia_tri!r} khong co trong enum that"


def test_camera_nam_trong_idempotency_key_fields():
    """Ly do cua test tat dinh o tren — chot lai bang ban khai THAT, de neu
    taovideo bo `camera` khoi key_fields thi ai do phai doc lai dong nay."""
    from apps.taovideo.manifest import MANIFEST as TAOVIDEO

    spec = next(t for t in TAOVIDEO.tools if t.name == "video.generate")
    assert "camera" in spec.idempotency["key_fields"]
