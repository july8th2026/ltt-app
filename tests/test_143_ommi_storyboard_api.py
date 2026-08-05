"""Storyboard OMMI — tầng HTTP.

Điều quan trọng nhất được chốt ở đây: **chạy lại một cảnh chỉ tính tiền một
cảnh**, và cảnh khác không bị đụng. Đó là lý do storyboard tồn tại thay vì dựng
lại cả bộ mỗi lần sửa một khung.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'sb-api.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_STORAGE", raising=False)
    monkeypatch.setenv("LTT_PROMPT_AI_OMMI_ROLLOUT", "public")
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    db = next(dbmod.get_session())
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    ids = {}
    for email in ("sb-a@example.com", "sb-b@example.com"):
        user = tao_nguoi_dung(db, email=email, password="Strong-pass-123",
                              is_verified=True)
        ids[email] = user.id
        credit.cap_tay(db, user.id, 500, by="test")
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-storyboard-api-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})

    def login(email):
        client = TestClient(app, base_url="https://testserver",
                            follow_redirects=True)
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert client.post("/login", data={
            "username": email, "password": "Strong-pass-123",
            "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
        studio = client.get("/prompt-ai-ommi")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
        return client, csrf

    a, token_a = login("sb-a@example.com")
    b, token_b = login("sb-b@example.com")
    yield a, token_a, ids["sb-a@example.com"], b, token_b
    a.close(); b.close(); dbmod.reset_engine(); storage_mod._storage = None


def _project(client, token, name="Dự án"):
    made = client.post("/prompt-ai-ommi/api/projects",
                       headers={"X-CSRF-Token": token}, json={"name": name})
    assert made.status_code == 201, made.text
    return made.json()["id"]


def _board(client, token, project_id, name="Bảng"):
    made = client.post("/prompt-ai-ommi/api/storyboards",
                       headers={"X-CSRF-Token": token},
                       json={"project_id": project_id, "name": name})
    assert made.status_code == 201, made.text
    return made.json()["id"]


def _scene(client, token, board_id, **body):
    made = client.post(f"/prompt-ai-ommi/api/storyboards/{board_id}/scenes",
                       headers={"X-CSRF-Token": token}, json=body)
    assert made.status_code == 201, made.text
    return made.json()


def test_board_and_scenes_round_trip(api):
    a, token_a, *_ = api
    board = _board(a, token_a, _project(a, token_a))
    _scene(a, token_a, board, title="Mở đầu", prompt="canh mo dau ngoai troi")
    _scene(a, token_a, board, title="Cao trào", prompt="canh cao trao trong nha")

    detail = a.get(f"/prompt-ai-ommi/api/storyboards/{board}").json()
    assert [s["title"] for s in detail["scenes"]] == ["Mở đầu", "Cao trào"]
    assert [s["position"] for s in detail["scenes"]] == [0, 1]


def test_a_board_cannot_be_attached_to_someone_elses_project(api):
    """Không kiểm thì biết ID project là gắn được storyboard vào dự án người khác."""
    a, token_a, _id_a, b, token_b = api
    project_a = _project(a, token_a)
    response = b.post("/prompt-ai-ommi/api/storyboards",
                      headers={"X-CSRF-Token": token_b},
                      json={"project_id": project_a, "name": "Chen ngang"})
    assert response.status_code == 404


def test_every_storyboard_endpoint_is_404_for_another_user(api):
    a, token_a, id_a, b, token_b = api
    board = _board(a, token_a, _project(a, token_a))
    scene = _scene(a, token_a, board, title="Cảnh", prompt="mot canh du dai")["id"]

    checks = [
        ("GET", f"/prompt-ai-ommi/api/storyboards/{board}", None),
        ("PUT", f"/prompt-ai-ommi/api/storyboards/{board}", {"name": "Cướp"}),
        ("POST", f"/prompt-ai-ommi/api/storyboards/{board}/scenes", {"title": "X"}),
        ("POST", f"/prompt-ai-ommi/api/storyboards/{board}/reorder",
         {"scene_ids": [scene]}),
        ("PUT", f"/prompt-ai-ommi/api/scenes/{scene}", {"title": "Cướp"}),
        ("DELETE", f"/prompt-ai-ommi/api/scenes/{scene}", None),
        ("GET", f"/prompt-ai-ommi/api/scenes/{scene}/versions", None),
        ("POST", f"/prompt-ai-ommi/api/scenes/{scene}/render", {}),
    ]
    for method, path, body in checks:
        for payload in (body, {**(body or {}), "owner_id": id_a}):
            response = b.request(method, path,
                                 headers={"X-CSRF-Token": token_b}, json=payload)
            assert response.status_code == 404, (
                f"{method} {path} với {payload!r} trả {response.status_code}")


def test_rendering_quotes_before_it_charges(api):
    a, token_a, id_a, *_ = api
    board = _board(a, token_a, _project(a, token_a))
    scene = _scene(a, token_a, board, prompt="mot canh du dai de sinh anh")["id"]

    quoted = a.post(f"/prompt-ai-ommi/api/scenes/{scene}/render",
                    headers={"X-CSRF-Token": token_a}, json={})
    assert quoted.status_code == 200
    assert quoted.json()["confirmed"] is False and quoted.json()["credit"] > 0

    from platform_core.db import get_session
    from platform_core.models import Job
    db = next(get_session())
    try:
        assert db.query(Job).filter(Job.user_id == id_a).count() == 0
    finally:
        db.close()


def test_rendering_one_scene_only_submits_one_job(api):
    """Đây là lý do storyboard tồn tại: sửa một khung không phải trả tiền dựng
    lại cả bộ."""
    a, token_a, id_a, *_ = api
    board = _board(a, token_a, _project(a, token_a))
    first = _scene(a, token_a, board, prompt="canh mot du dai de sinh anh")["id"]
    _scene(a, token_a, board, prompt="canh hai du dai de sinh anh")

    started = a.post(f"/prompt-ai-ommi/api/scenes/{first}/render",
                     headers={"X-CSRF-Token": token_a}, json={"confirmed": True})
    assert started.status_code == 200, started.text

    from platform_core.db import get_session
    from platform_core.models import Job
    db = next(get_session())
    try:
        jobs = db.query(Job).filter(Job.user_id == id_a).all()
        assert len(jobs) == 1
        assert jobs[0].job_type == "taoanh.generate"
        assert jobs[0].app_slug == "prompt_ai_ommi"
    finally:
        db.close()


def test_attaching_a_render_records_a_version_and_leaves_others_alone(api):
    a, token_a, *_ = api
    board = _board(a, token_a, _project(a, token_a))
    first = _scene(a, token_a, board, prompt="canh mot du dai de sinh anh")["id"]
    second = _scene(a, token_a, board, prompt="canh hai du dai de sinh anh")["id"]

    job_id = a.post(f"/prompt-ai-ommi/api/scenes/{first}/render",
                    headers={"X-CSRF-Token": token_a},
                    json={"confirmed": True}).json()["id"]

    from platform_core.db import get_session
    from platform_core.models import JOB_DONE, Job
    db = next(get_session())
    try:
        job = db.get(Job, job_id)
        job.status = JOB_DONE
        job.result = {"image_keys": ["taoanh/x/1.png"]}
        db.commit()
    finally:
        db.close()

    attached = a.post(f"/prompt-ai-ommi/api/scenes/{first}/attach/{job_id}",
                      headers={"X-CSRF-Token": token_a}, json={})
    assert attached.status_code == 201, attached.text
    assert attached.json()["image_key"] == "taoanh/x/1.png"
    assert attached.json()["version"] == 2

    history = a.get(f"/prompt-ai-ommi/api/scenes/{first}/versions").json()
    assert [v["version"] for v in history["items"]] == [1]

    board_now = a.get(f"/prompt-ai-ommi/api/storyboards/{board}").json()
    other = [s for s in board_now["scenes"] if s["id"] == second][0]
    assert other["image_key"] == "" and other["version"] == 1


def test_cannot_attach_someone_elses_job(api):
    a, token_a, _id_a, b, token_b = api
    board_a = _board(a, token_a, _project(a, token_a))
    scene_a = _scene(a, token_a, board_a, prompt="canh cua a du dai")["id"]
    board_b = _board(b, token_b, _project(b, token_b))
    scene_b = _scene(b, token_b, board_b, prompt="canh cua b du dai")["id"]

    job_id = b.post(f"/prompt-ai-ommi/api/scenes/{scene_b}/render",
                    headers={"X-CSRF-Token": token_b},
                    json={"confirmed": True}).json()["id"]
    from platform_core.db import get_session
    from platform_core.models import JOB_DONE, Job
    db = next(get_session())
    try:
        job = db.get(Job, job_id)
        job.status = JOB_DONE
        job.result = {"image_keys": ["taoanh/b/1.png"]}
        db.commit()
    finally:
        db.close()

    stolen = a.post(f"/prompt-ai-ommi/api/scenes/{scene_a}/attach/{job_id}",
                    headers={"X-CSRF-Token": token_a}, json={})
    assert stolen.status_code == 404


def test_reorder_and_delete_keep_positions_contiguous(api):
    a, token_a, *_ = api
    board = _board(a, token_a, _project(a, token_a))
    one = _scene(a, token_a, board, title="Một")["id"]
    two = _scene(a, token_a, board, title="Hai")["id"]
    three = _scene(a, token_a, board, title="Ba")["id"]

    reordered = a.post(f"/prompt-ai-ommi/api/storyboards/{board}/reorder",
                       headers={"X-CSRF-Token": token_a},
                       json={"scene_ids": [three, one, two]})
    assert [s["title"] for s in reordered.json()["scenes"]] == ["Ba", "Một", "Hai"]

    assert a.delete(f"/prompt-ai-ommi/api/scenes/{one}",
                    headers={"X-CSRF-Token": token_a}).status_code == 200
    left = a.get(f"/prompt-ai-ommi/api/storyboards/{board}").json()["scenes"]
    assert [s["title"] for s in left] == ["Ba", "Hai"]
    assert [s["position"] for s in left] == [0, 1]


def test_a_scene_without_enough_prompt_cannot_be_rendered(api):
    a, token_a, *_ = api
    board = _board(a, token_a, _project(a, token_a))
    scene = _scene(a, token_a, board, prompt="ngan")["id"]
    response = a.post(f"/prompt-ai-ommi/api/scenes/{scene}/render",
                      headers={"X-CSRF-Token": token_a}, json={})
    assert response.status_code == 422
