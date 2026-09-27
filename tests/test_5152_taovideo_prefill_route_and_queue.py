"""POST /taovideo/prefill stage anh tu payload; /queue nap dung ref (Pha 2).

Va phep DOI CHUNG cua Sec 9g: `taovideo` la app `lifecycle="released"` dang
phuc vu khach, nen KHONG co `?tu_studio` thi `/queue` va form phai chay Y NHU
CU — moi tham so Form moi deu `default=[]` va khoi gop ref prefill la KHONG-OP.
"""
from __future__ import annotations

import base64
import io
import json
import re

import pytest
from PIL import Image
from fastapi.testclient import TestClient


def _png_bytes() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (32, 32), (10, 120, 200)).save(stream, format="PNG")
    return stream.getvalue()


PNG_BYTES = _png_bytes()
PNG_DATA_URL = ("data:image/png;base64,"
                + base64.b64encode(PNG_BYTES).decode("ascii"))


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'tv-prefill.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_SESSION_SECRET", "tv-prefill-test")
    monkeypatch.delenv("LTT_STORAGE", raising=False)
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    db = next(dbmod.get_session())
    from platform_core.credit import cap_tay
    from platform_core.users import tao_nguoi_dung
    uid = tao_nguoi_dung(db, email="tv-prefill@example.com",
                         password="Strong-pass-123", is_verified=True).id
    cap_tay(db, uid, 500, by="fixture", note="prefill test")
    db.commit()
    db.close()
    dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "tv-prefill-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})

    client = TestClient(app, base_url="https://testserver",
                        follow_redirects=False)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "tv-prefill@example.com", "password": "Strong-pass-123",
        "csrf_token": token}).status_code == 303
    home = client.get("/taovideo")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', home.text).group(1)
    yield client, csrf, uid
    client.close()
    dbmod.reset_engine()
    storage_mod.set_storage(None)


def _payload(refs=None):
    return {"prompt": "Canh co @IMG_1", "params": {
        "model": "seedance-2.0-mini", "resolution": "480p", "duration": 5,
        "aspect_ratio": "16:9", "generate_audio": True, "camera": "dolly_in",
        "motion": "cinematic", "visual_style": "cinematic"},
        "refs": [{"kind": "image", "url": PNG_DATA_URL,
                  "role": "reference_image", "handle": "@IMG_1"}]
        if refs is None else refs,
        "tag_map": {}, "skipped": [], "skipped_over_limit": 0}


def _quote(client, *, count="1", has_video="0"):
    resp = client.post("/taovideo/estimate", data={
        "model": "seedance-2.0-mini", "resolution": "480p", "duration": "5",
        "aspect_ratio": "16:9", "count": count, "quote_has_video": has_video})
    return re.search(r'name="quote_id" value="([^"]+)"', resp.text).group(1)


def _job_moi_nhat(uid):
    from platform_core.db import get_session
    from platform_core.models import Job
    from sqlalchemy import select
    gen = get_session()
    db = next(gen)
    try:
        return db.execute(
            select(Job).where(Job.user_id == uid)
            .order_by(Job.created_at.desc())).scalars().first()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_prefill_stage_anh_roi_queue_nap_dung_ref(api):
    client, csrf, uid = api

    resp = client.post("/taovideo/prefill",
                       json={"csrf_token": csrf, "payload": _payload()})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["values"]["prompt"] == "Canh co @IMG_1"
    assert data["values"]["camera"] == "dolly_in"
    assert data["bo_qua"] == 0
    assert len(data["ref_keys"]) == 1
    upload_id = data["ref_keys"][0]["upload_id"]
    assert data["ref_keys"][0]["handle"] == "@IMG_1"

    submit = client.post("/taovideo/queue", data={
        "csrf_token": csrf, "prompt": "Canh co @IMG_1",
        "model": "seedance-2.0-mini", "resolution": "480p", "duration": "5",
        "aspect_ratio": "16:9", "camera": "dolly_in", "motion": "cinematic",
        "visual_style": "cinematic", "count": "1", "quote_id": _quote(client),
        "prefill_upload_ids": [upload_id],
        "prefill_roles": ["reference_image"], "prefill_handles": ["@IMG_1"]})
    assert submit.status_code == 303, submit.text

    job = _job_moi_nhat(uid)
    assert job is not None
    refs = (job.params or {}).get("refs") or []
    assert any(r.get("handle") == "@IMG_1"
               and r.get("role") == "reference_image" for r in refs), refs
    # Ref da duoc `promote` sang key ben vung, khong con o staging.
    assert all("upload_id" not in r for r in refs)


def test_video_ref_khong_tu_stage_nhung_duoc_dem_vao_bo_qua(api):
    """Pha 2 chi tu dong dinh kem ANH. Video KHONG bien mat im lang."""
    client, csrf, _uid = api
    refs = [{"kind": "video", "url": "https://example.com/a.mp4",
             "role": "reference_video", "handle": "@VID_1"},
            {"kind": "image", "url": PNG_DATA_URL,
             "role": "reference_image", "handle": "@IMG_1"}]
    data = client.post("/taovideo/prefill",
                       json={"csrf_token": csrf,
                             "payload": _payload(refs)}).json()
    assert len(data["ref_keys"]) == 1
    assert data["bo_qua"] == 1


def test_qua_tran_anh_bi_cat_nhung_bao_so_bi_cat(api):
    """Vuot tran anh thi bi CAT, va so bi cat phai duoc BAO — khong cat am tham.

    ⭐ Doc `refs.TRAN_ANH` chu KHONG go so: ban truoc khang dinh `== 4` va do
    ngay khi chu du an dao quyet dinh sang tran 9 (nguyen van BOT GEMINI,
    `# Seedance 2.0 hard limits`). Mot phep kiem go tay tran la mot phep kiem
    se do lai lan sau — con hanh vi dang bao ve thi KHONG doi.
    """
    from apps.taovideo import refs as tv_refs
    client, csrf, _uid = api
    # Dung TRAN + 1 de chac chan co dung MOT anh bi cat, bat ke tran la bao nhieu.
    so_gui = tv_refs.TRAN_ANH + 1
    refs = [{"kind": "image", "url": PNG_DATA_URL,
             "role": "reference_image", "handle": f"@IMG_{i + 1}"}
            for i in range(so_gui)]
    data = client.post("/taovideo/prefill",
                       json={"csrf_token": csrf,
                             "payload": _payload(refs)}).json()
    assert len(data["ref_keys"]) == tv_refs.TRAN_ANH
    assert data["bo_qua"] == 1


def test_duoi_tran_thi_khong_cat_gi(api):
    """Doi chung cho phep tren: DUOI tran thi khong mat anh nao.

    ⛔ Ca nay PHAI la mot phep RIENG, khong phai luot goi thu hai trong phep
    tren: tai san cua luot truoc VAN CON trong kho cua cung chu so huu, nen luot
    sau cham `TRAN_TONG` va tra ve mot con so khong noi gi ve viec bi cat. Mot
    doi chung dung chung TRANG THAI voi phep chinh khong con la doi chung.
    """
    from apps.taovideo import refs as tv_refs
    client, csrf, _uid = api
    so_gui = tv_refs.TRAN_ANH - 1
    refs = [{"kind": "image", "url": PNG_DATA_URL,
             "role": "reference_image", "handle": f"@IMG_{i + 1}"}
            for i in range(so_gui)]
    data = client.post("/taovideo/prefill",
                       json={"csrf_token": csrf,
                             "payload": _payload(refs)}).json()
    assert len(data["ref_keys"]) == so_gui
    assert data["bo_qua"] == 0


def test_prefill_khong_co_csrf_thi_tu_choi(api):
    client, _csrf, _uid = api
    resp = client.post("/taovideo/prefill",
                       json={"csrf_token": "sai", "payload": _payload()})
    assert resp.status_code == 400


def test_data_url_rac_khong_lam_no_route(api):
    client, csrf, _uid = api
    refs = [{"kind": "image", "url": "data:image/png;base64,###khong-phai-b64",
             "role": "reference_image", "handle": "@IMG_1"}]
    data = client.post("/taovideo/prefill",
                       json={"csrf_token": csrf,
                             "payload": _payload(refs)}).json()
    assert data["ref_keys"] == []
    assert data["bo_qua"] == 1


def test_trang_taovideo_khong_co_tu_studio_giu_nguyen_hanh_vi(api):
    """Sec 9g: app `released`, khong co `?tu_studio` thi khong doi gi ca."""
    client, csrf, uid = api
    trang = client.get("/taovideo")
    assert trang.status_code == 200
    assert 'data-tu-studio=""' in trang.text

    submit = client.post("/taovideo/queue", data={
        "csrf_token": csrf, "prompt": "Canh khong lien quan gi den studio",
        "model": "seedance-2.0-mini", "resolution": "480p", "duration": "5",
        "aspect_ratio": "16:9", "count": "1", "quote_id": _quote(client)})
    assert submit.status_code == 303, submit.text
    job = _job_moi_nhat(uid)
    assert (job.params or {}).get("refs") == []


def test_trang_taovideo_co_tu_studio_mang_ve_xuong_template(api):
    client, _csrf, _uid = api
    trang = client.get("/taovideo?tu_studio=ve-abc-123")
    assert trang.status_code == 200
    assert 'data-tu-studio="ve-abc-123"' in trang.text
