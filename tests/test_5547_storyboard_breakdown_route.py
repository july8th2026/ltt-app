"""tests/test_5547_storyboard_breakdown_route.py.

⚠️ Plan gốc giả định `OmmiStoryboard.story` — cột đó KHÔNG tồn tại
(`OmmiStoryboard` chỉ là "khung hình", spec Sec 4.3). `story_vi` do đó được
gõ trực tiếp trong body của request (xem `routes/storyboard.py`, và báo cáo
làm I) — fixture ở đây dựng qua `services/storyboard.py::create_board`, tên
hàm thật (⛔ không phải `get_owned_storyboard` như plan viết nhầm).
"""
from __future__ import annotations

import json
import re
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'sb-route.db').as_posix()}")
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
    user = tao_nguoi_dung(db, email="sb-a@example.com",
                          password="Strong-pass-123", is_verified=True)
    credit.cap_tay(db, user.id, 200, by="test")

    from apps.prompt_ai_ommi.services import storyboard as ssvc
    from apps.prompt_ai_ommi.tables import OmmiStoryboardFramework
    framework = OmmiStoryboardFramework(
        name="Khung X", owner_id=user.id, composite_header="TD",
        composite_rules="LU", composite_negative_footer="KH",
        default_n_scenes=4, breakdown_llm_prompt="Chia {STORY} thanh {N} canh",
        is_builtin=True)
    db.add(framework); db.flush()
    board = ssvc.create_board(db, owner_id=user.id, project_id="p1", name="SB")
    db.commit()
    framework_id = framework.id
    board_id = board.id
    db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-sb-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "sb-a@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
    studio = client.get("/prompt-ai-ommi")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
    yield client, csrf, board_id, framework_id
    client.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_breakdown_route_returns_default_n_scenes(api):
    client, token, sid, fid = api
    fake_raw = {"scenes": [{"title": "A", "prompt": "pa"}]}
    with patch("apps.prompt_ai_ommi.provider.generate_json",
              return_value=(fake_raw, 5)), \
         patch("apps.prompt_ai_ommi.provider.model_mac_dinh",
              return_value="ltt-3.8"):
        resp = client.post(
            f"/prompt-ai-ommi/api/storyboards/{sid}/breakdown",
            headers={"X-CSRF-Token": token},
            json={"framework_id": fid, "story_vi": "mot cau chuyen dai ve A"})
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["scenes"]) == 4


def test_breakdown_route_rejects_missing_story_vi(api):
    client, token, sid, fid = api
    resp = client.post(
        f"/prompt-ai-ommi/api/storyboards/{sid}/breakdown",
        headers={"X-CSRF-Token": token}, json={"framework_id": fid})
    assert resp.status_code == 422


def test_breakdown_route_rejects_unknown_framework(api):
    client, token, sid, _fid = api
    resp = client.post(
        f"/prompt-ai-ommi/api/storyboards/{sid}/breakdown",
        headers={"X-CSRF-Token": token},
        json={"framework_id": "khong-ton-tai", "story_vi": "abc"})
    assert resp.status_code == 404


def test_breakdown_route_rejects_storyboard_of_another_owner(api):
    """Kênh THẬT bắt lỗi quyền — `get_owned_board` phải chặn TRƯỚC khi đọc
    framework hay gọi LLM."""
    client, token, sid, fid = api
    import platform_core.db as dbmod
    db = next(dbmod.get_session())
    from apps.prompt_ai_ommi.tables import OmmiStoryboard
    row = db.get(OmmiStoryboard, sid)
    row.owner_id = "mallory"
    db.commit()
    db.close()

    resp = client.post(
        f"/prompt-ai-ommi/api/storyboards/{sid}/breakdown",
        headers={"X-CSRF-Token": token},
        json={"framework_id": fid, "story_vi": "abc"})
    assert resp.status_code == 404
