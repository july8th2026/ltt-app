"""Spec Sec 6.3 quy tac 3: variant con ban ghi nhung MAT TEP thi van tieu so
va vao `skipped` — khong duoc lam rong ca refs (day la duong N-1 that: mot
anh mat tep khong duoc keo theo ca canh mat het anh).

Quy tac 3 KHAC quy tac 2, va gop hai cai la sai MOT CHIEU:
  - quy tac 2 (variant khong con ban ghi)  => KHONG tieu so  (lan A, test_5111)
  - quy tac 3 (con ban ghi, MAT TEP)       => CO tieu so     (tep nay)
Gop ve "khong tieu" => the trong prompt lech voi anh gui di. Gop ve "co tieu"
=> anh khach da xoa van chiem mot so. Ca hai deu la ca that.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'handoff_skip.db').as_posix()}")
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
    def __init__(self):
        self._data = {}

    def put_test(self, key, data):
        self._data[key] = data

    def exists(self, key):
        return key in self._data

    def open(self, key):
        import io
        return io.BytesIO(self._data[key])


def _png() -> bytes:
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "+A8AAQUBAScY42YAAAAASUVORK5CYII=")


def _dung_canh(db, monkeypatch, *, co_tep_truoc: bool):
    """Dung mot canh hai anh. `co_tep_truoc=True` => anh CO tep duoc gan the
    @IMAGE_1; `False` => anh MAT tep duoc gan the @IMAGE_1 (ca phan biet quy
    tac 3 voi quy tac 2)."""
    from apps.prompt_ai_ommi.services import resources as rsvc
    from apps.prompt_ai_ommi.services import bindings as bsvc
    from platform_core import app_projects
    from apps.prompt_ai_ommi.manifest import MANIFEST
    from apps.prompt_ai_ommi.project_schema import empty_project

    fake = _FakeStorage()
    monkeypatch.setattr("platform_core.storage.get_storage", lambda: fake)

    r1 = rsvc.create(db, owner_id="khach1", kind="character", name="A")
    v_co = rsvc.add_variant(db, resource_id=r1.id, owner_id="khach1",
                            storage_key="ommi/khach1/r1/a.png")
    fake.put_test(v_co.storage_key, _png())  # v_co: tep CO that

    r2 = rsvc.create(db, owner_id="khach1", kind="character", name="B")
    v_mat = rsvc.add_variant(db, resource_id=r2.id, owner_id="khach1",
                             storage_key="ommi/khach1/r2/b.png")
    # v_mat: KHONG put_test — mo phong tep da bi xoa khoi Storage. Ban ghi
    # variant VAN CON trong CSDL (do la diem khac quy tac 2).

    payload = empty_project("Du an test")
    payload["scenes"] = [{"id": "scene1", "order": 0, "title": "Canh 1",
                          "prompt": "Nhan vat @IMAGE_1 dung canh @IMAGE_2.",
                          "camera": "", "mood": "", "lighting": "",
                          "continuity": "", "duration_seconds": 5,
                          "versions": [], "selected_version": 0}]
    project = app_projects.create(db, user_id="khach1", app_slug=MANIFEST.slug,
                                  name="Du an test", schema_version=1, payload=payload)
    db.commit()

    thu_tu = [v_co, v_mat] if co_tep_truoc else [v_mat, v_co]
    bsvc.replace_bindings(db, project_id=project.id, owner_id="khach1",
                          scene_id="scene1",
                          items=[{"kind": "image", "variant_id": v.id}
                                 for v in thu_tu])
    db.commit()
    return project


def test_mot_anh_mat_tep_van_vao_skipped_anh_con_lai_van_di(db, monkeypatch):
    from apps.prompt_ai_ommi.routes.handoff import _handoff_params

    project = _dung_canh(db, monkeypatch, co_tep_truoc=True)
    scene = project.payload["scenes"][0]
    _, params = _handoff_params(db, "khach1", project, scene, "video", {})

    assert len(params["refs"]) == 1
    assert params["refs"][0]["handle"] == "image_1"
    # quy tac 3: v_mat van tieu so @IMAGE_2 — bat_bien_giao_bai khong nem vi
    # @IMAGE_2 nam trong skipped, khong phai vi refs con thieu.


def test_quy_tac_3_anh_mat_tep_CO_TIEU_so_thu_tu(db, monkeypatch):
    """Phep phan biet THAT cua quy tac 3.

    Anh MAT TEP duoc gan the @IMAGE_1, anh con tep la @IMAGE_2. Neu mat tep
    KHONG tieu so (gop lan sang quy tac 2) thi anh con lai se mang handle
    `image_1` va lech voi the trong prompt. Quy tac 3 dung => `image_2`.
    """
    from apps.prompt_ai_ommi.routes.handoff import _handoff_params

    project = _dung_canh(db, monkeypatch, co_tep_truoc=False)
    scene = project.payload["scenes"][0]
    _, params = _handoff_params(db, "khach1", project, scene, "video", {})

    assert len(params["refs"]) == 1
    assert params["refs"][0]["handle"] == "image_2", (
        "anh mat tep phai TIEU so @IMAGE_1 (spec Sec 6.3 quy tac 3); neu no "
        "khong tieu thi anh con lai bi keo ve image_1 va lech voi prompt")


def test_skipped_lam_bat_bien_khong_do_oan(db, monkeypatch):
    """Doi chung cho dieu kien `skipped` cua B-1: bo `skipped` di thi chinh ca
    nay (anh khach da xoa) bien thanh mot bao dong gia."""
    from apps.prompt_ai_ommi.services.bat_bien import bat_bien_giao_bai

    prompt = "Nhan vat @IMAGE_1 dung canh @IMAGE_2."
    refs = [{"kind": "image", "url": "data:image/png;base64,AA==",
             "role": "reference_image", "handle": "image_1"}]
    skipped = [{"variant_id": "v2", "handle": "image_2",
                "ly_do": "tep khong ton tai"}]

    bat_bien_giao_bai(prompt, refs, skipped, has_binding=True)  # khong nem
    with pytest.raises(ValueError, match="B-1"):  # bo skipped => do oan
        bat_bien_giao_bai(prompt, refs, [], has_binding=True)


def test_ca_hai_anh_mat_tep_khong_lam_ca_canh_thanh_500(db, monkeypatch):
    """Khong duoc doi thanh B-5: ca hai anh vao `skipped` nen `skipped` khong
    rong, va do la ca HOP LE (khach xoa het anh)."""
    from apps.prompt_ai_ommi.routes.handoff import _handoff_params
    from apps.prompt_ai_ommi.services import bindings as bsvc

    project = _dung_canh(db, monkeypatch, co_tep_truoc=True)
    # Xoa luon tep cua anh con lai: storage gia bay gio rong hoan toan.
    monkeypatch.setattr("platform_core.storage.get_storage",
                        lambda: _FakeStorage())
    scene = project.payload["scenes"][0]
    assert bsvc.list_bindings(db, project_id=project.id, owner_id="khach1",
                              scene_id="scene1")  # binding VAN con
    _, params = _handoff_params(db, "khach1", project, scene, "video", {})

    assert params["refs"] == []
