"""POST handoff/video tra VE; GET payload tra dung hinh dang spec Sec 6.2."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ommi-handoff-route.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_PROMPT_AI_OMMI_ROLLOUT", "public")
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
    from platform_core.users import tao_nguoi_dung
    uid = tao_nguoi_dung(db, email="ho-a@example.com",
                         password="Strong-pass-123", is_verified=True).id
    db.commit()
    db.close()
    dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-handoff-route-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})

    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "ho-a@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
    studio = client.get("/prompt-ai-ommi")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
    yield client, csrf, uid
    client.close()
    dbmod.reset_engine()
    storage_mod.set_storage(None)


def _du_an_co_canh(client, csrf):
    made = client.post("/prompt-ai-ommi/api/projects",
                       headers={"X-CSRF-Token": csrf},
                       json={"name": "Giao bai"}).json()
    body = made["payload"]
    body["scenes"] = [{"id": "scene_one", "title": "Canh", "duration_seconds": 5,
                       "prompt": "Mot canh khong co anh tham chieu",
                       "camera": "dolly in, slow push",
                       "lighting": "vang hoang hon", "mood": "cinematic"}]
    client.put(f"/prompt-ai-ommi/api/projects/{made['id']}",
               headers={"X-CSRF-Token": csrf},
               json={"revision": made["revision"], "payload": body})
    return made["id"]


def test_giao_bai_tra_ve_va_doc_payload_lan_dau(api):
    client, csrf, _uid = api
    pid = _du_an_co_canh(client, csrf)

    ve = client.post(f"/prompt-ai-ommi/api/projects/{pid}/handoff/video",
                     headers={"X-CSRF-Token": csrf},
                     json={"scene_id": "scene_one"})
    assert ve.status_code == 201, ve.text
    data = ve.json()
    assert set(data.keys()) >= {"ticket_id", "expires_at", "open_url",
                                "skipped", "skipped_over_limit"}
    assert data["open_url"] == f"/taovideo/?tu_studio={data['ticket_id']}"
    assert data["skipped_over_limit"] == 0

    payload = client.get(
        f"/prompt-ai-ommi/api/handoff/{data['ticket_id']}/payload")
    assert payload.status_code == 200, payload.text
    body = payload.json()
    assert body["prompt"]
    # chi tiet tu do giu NGUYEN VAN (Sec 6.2b luat 1)
    assert "dolly in, slow push" in body["prompt"]
    assert "vang hoang hon" in body["prompt"]
    assert body["params"]["camera"] == "dolly_in"   # goi y enum suy tu khoa
    assert body["params"]["motion"] == "cinematic"
    assert body["params"]["aspect_ratio"] == "16:9"
    assert body["refs"] == []
    assert set(body) == {"prompt", "params", "refs", "tag_map", "skipped",
                         "skipped_over_limit"}


def test_canh_khong_ton_tai_tra_404(api):
    client, csrf, _uid = api
    pid = _du_an_co_canh(client, csrf)
    resp = client.post(f"/prompt-ai-ommi/api/projects/{pid}/handoff/video",
                       headers={"X-CSRF-Token": csrf},
                       json={"scene_id": "khong-co-canh-nay"})
    assert resp.status_code == 404


def test_khong_co_csrf_thi_tu_choi(api):
    client, csrf, _uid = api
    pid = _du_an_co_canh(client, csrf)
    resp = client.post(f"/prompt-ai-ommi/api/projects/{pid}/handoff/video",
                       json={"scene_id": "scene_one"})
    assert resp.status_code == 400


def test_overrides_duoc_ap_vao_params(api):
    client, csrf, _uid = api
    pid = _du_an_co_canh(client, csrf)
    ve = client.post(f"/prompt-ai-ommi/api/projects/{pid}/handoff/video",
                     headers={"X-CSRF-Token": csrf},
                     json={"scene_id": "scene_one", "resolution": "720p",
                           "duration": 10, "generate_audio": False}).json()
    body = client.get(
        f"/prompt-ai-ommi/api/handoff/{ve['ticket_id']}/payload").json()
    assert body["params"]["resolution"] == "720p"
    assert body["params"]["duration"] == 10
    assert body["params"]["generate_audio"] is False


def test_params_cua_payload_di_qua_validate_tool_params(api):
    """Sec 6.2c: mot khoa la trong `params` bien MOI luot giao bai thanh 422.

    Phep kiem nay doc `params` tu DUONG THAT (HTTP -> `ommi_handoff.payload`)
    roi nap vao `validate_tool_params` — khong goi ham noi bo roi tu so bo khoa.
    """
    client, csrf, _uid = api
    pid = _du_an_co_canh(client, csrf)
    ve = client.post(f"/prompt-ai-ommi/api/projects/{pid}/handoff/video",
                     headers={"X-CSRF-Token": csrf},
                     json={"scene_id": "scene_one"}).json()
    body = client.get(
        f"/prompt-ai-ommi/api/handoff/{ve['ticket_id']}/payload").json()

    from platform_core.agent.tools import validate_tool_params
    from platform_core.registry import discover
    clean = validate_tool_params("video.generate", body["params"],
                                 apps=discover())
    assert clean["camera"] == "dolly_in"


def test_duong_image_cu_khong_bi_route_video_che(api):
    """`/handoff/image` (frame storyboard noi bo) phai chay y nhu cu."""
    client, csrf, _uid = api
    pid = _du_an_co_canh(client, csrf)
    resp = client.post(f"/prompt-ai-ommi/api/projects/{pid}/handoff/image",
                       headers={"X-CSRF-Token": csrf},
                       json={"scene_id": "scene_one"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["confirmed"] is False
    assert resp.json()["tool"] == "image.generate"
