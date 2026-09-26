"""Ve giao bai: chu moi doc duoc, va CHI doc duoc MOT LAN (409 lan hai)."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ommi-handoff-owner.db').as_posix()}")
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
    for email in ("owner-a@example.com", "owner-b@example.com"):
        tao_nguoi_dung(db, email=email, password="Strong-pass-123",
                       is_verified=True)
    db.commit()
    db.close()
    dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-handoff-owner-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})

    def login(email):
        client = TestClient(app, base_url="https://testserver",
                            follow_redirects=True)
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"',
                          page.text).group(1)
        assert client.post("/login", data={
            "username": email, "password": "Strong-pass-123",
            "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
        studio = client.get("/prompt-ai-ommi")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"',
                         studio.text).group(1)
        return client, csrf

    a, ca = login("owner-a@example.com")
    b, cb = login("owner-b@example.com")
    yield a, ca, b, cb
    a.close()
    b.close()
    dbmod.reset_engine()
    storage_mod.set_storage(None)


def _du_an_co_canh(client, csrf):
    made = client.post("/prompt-ai-ommi/api/projects",
                       headers={"X-CSRF-Token": csrf},
                       json={"name": "Giao bai"}).json()
    body = made["payload"]
    body["scenes"] = [{"id": "scene_one", "title": "Canh",
                       "prompt": "canh trong"}]
    client.put(f"/prompt-ai-ommi/api/projects/{made['id']}",
               headers={"X-CSRF-Token": csrf},
               json={"revision": made["revision"], "payload": body})
    return made["id"]


def _ve(client, csrf, pid):
    resp = client.post(f"/prompt-ai-ommi/api/projects/{pid}/handoff/video",
                       headers={"X-CSRF-Token": csrf},
                       json={"scene_id": "scene_one"})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_nguoi_khac_khong_doc_duoc_ve(api):
    a, ca, b, _cb = api
    pid = _du_an_co_canh(a, ca)
    ve = _ve(a, ca, pid)
    resp = b.get(f"/prompt-ai-ommi/api/handoff/{ve['ticket_id']}/payload")
    assert resp.status_code == 404


def test_nguoi_khac_doc_that_bai_KHONG_tieu_ve_cua_chu(api):
    """Doi chung: mot lan doc that bai cua nguoi la khong duoc bien ve cua chu
    thanh ve da dung — do la mot cua chan dich vu re tien."""
    a, ca, b, _cb = api
    pid = _du_an_co_canh(a, ca)
    ve = _ve(a, ca, pid)
    assert b.get(
        f"/prompt-ai-ommi/api/handoff/{ve['ticket_id']}/payload").status_code == 404
    assert a.get(
        f"/prompt-ai-ommi/api/handoff/{ve['ticket_id']}/payload").status_code == 200


def test_doc_lan_hai_bi_tu_choi_409(api):
    a, ca, _b, _cb = api
    pid = _du_an_co_canh(a, ca)
    ve = _ve(a, ca, pid)
    lan_mot = a.get(f"/prompt-ai-ommi/api/handoff/{ve['ticket_id']}/payload")
    assert lan_mot.status_code == 200
    lan_hai = a.get(f"/prompt-ai-ommi/api/handoff/{ve['ticket_id']}/payload")
    assert lan_hai.status_code == 409


def test_ve_khong_ton_tai_tra_404(api):
    a, ca, _b, _cb = api
    _du_an_co_canh(a, ca)
    assert a.get(
        "/prompt-ai-ommi/api/handoff/khong-ton-tai/payload").status_code == 404


def test_ve_het_han_tra_410(api):
    from datetime import datetime, timedelta, timezone
    a, ca, _b, _cb = api
    pid = _du_an_co_canh(a, ca)
    ve = _ve(a, ca, pid)

    import platform_core.db as dbmod
    from apps.prompt_ai_ommi.tables import OmmiHandoff
    gen = dbmod.get_session()
    db = next(gen)
    try:
        row = db.get(OmmiHandoff, ve["ticket_id"])
        row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    assert a.get(
        f"/prompt-ai-ommi/api/handoff/{ve['ticket_id']}/payload").status_code == 410
