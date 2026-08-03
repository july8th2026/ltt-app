"""H15.S10.2 attachment/search/export/branch feature helpers."""
from __future__ import annotations

import io
import json
import re

import pytest
from PIL import Image


def _png():
    out = io.BytesIO(); Image.new("RGB", (96, 64), "red").save(out, "PNG")
    return out.getvalue()


def test_parse_image_and_text_attachments():
    from apps.chataistudio.features import context_message, parse_attachment
    image = parse_attachment(_png(), "image/png", "ref.png")
    assert image["kind"] == "image" and image["data_url"].startswith("data:image/png;base64,")
    text = parse_attachment(b"noi dung", "text/plain", "notes.txt")
    assert text["text"] == "noi dung"
    assert "[Tệp notes.txt]" in context_message("hãy đọc", [text])
    with pytest.raises(ValueError, match="Chỉ nhận"):
        parse_attachment(b"bin", "application/octet-stream", "x.exe")


def test_export_formats_are_versioned_and_human_readable():
    from apps.chataistudio.features import export_json, export_markdown
    class M:
        role = "user"; content = "Xin chào"; image_key = ""; image_prompt = ""
    md = export_markdown("Dự án", [M()])
    assert "# Dự án" in md and "## Bạn" in md and "Xin chào" in md
    data = json.loads(export_json("Dự án", "gpt-test", [M()]))
    assert data["version"] == 1 and data["messages"][0]["role"] == "user"


def test_search_export_and_branch_are_owner_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path/'chat-feature.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "chat-feature-test")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine(); import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.models import ChatConversation, ChatMessage
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        owner = tao_nguoi_dung(db, email="chat-owner@test.com", password="matkhau-tot-12",
                               is_verified=True)
        other = tao_nguoi_dung(db, email="chat-other@test.com", password="matkhau-tot-12",
                               is_verified=True)
        db.flush(); mine = ChatConversation(user_id=owner.id, title="Dự án của tôi")
        foreign = ChatConversation(user_id=other.id, title="Dự án khác")
        db.add_all([mine, foreign]); db.flush()
        db.add_all([ChatMessage(conversation_id=mine.id, user_id=owner.id, role="user",
                                content="MAGIC-SEARCH-CONTENT"),
                    ChatMessage(conversation_id=foreign.id, user_id=other.id, role="user",
                                content="MAGIC-SEARCH-CONTENT")])
        db.commit(); mine_id = mine.id
    finally:
        try: next(gen)
        except StopIteration: pass
    from apps.chataistudio import routes
    monkeypatch.setattr(routes.sc, "account", lambda: {"account": {"email": "x"}})
    monkeypatch.setattr(routes, "_models_cached", lambda: [])
    from fastapi.testclient import TestClient
    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver", follow_redirects=False)
    def login(email):
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert client.post("/login", data={"username": email, "password": "matkhau-tot-12",
                                           "csrf_token": token}).status_code == 303
    try:
        login("chat-owner@test.com")
        found = client.get("/chataistudio?q=MAGIC-SEARCH-CONTENT")
        assert found.status_code == 200 and "Dự án của tôi" in found.text
        assert "Dự án khác" not in found.text
        exported = client.get(f"/chataistudio/export/{mine_id}.json")
        assert exported.status_code == 200 and exported.json()["version"] == 1
        page = client.get(f"/chataistudio?c={mine_id}")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        branch = client.post(f"/chataistudio/branch/{mine_id}", data={"csrf_token": csrf})
        assert branch.status_code == 303 and "?c=" in branch.headers["location"]
    finally:
        client.close(); dbmod.reset_engine()
