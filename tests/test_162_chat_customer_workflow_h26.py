"""H26.10B — customer workflow, money safety and operation trace for Chat AI."""
from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).parents[1]


def test_chat_ui_hides_engine_ids_and_exposes_customer_controls():
    src = (ROOT / "apps" / "chataistudio" / "templates" /
           "chataistudio.html").read_text("utf-8")
    assert "model_label" in src
    assert "{{active.model}}" not in src
    assert 'class="chat-suggestions"' in src
    assert 'id="stopbtn"' in src
    assert "AbortController" in src
    assert 'class="chat-turn-meta"' in src
    assert "tokens_total" in src
    assert "data-credit-balance" in src


def test_public_model_labels_do_not_leak_provider_ids():
    from apps.chataistudio.features import public_model_label

    assert public_model_label("gpt-5.6-sol") == "Chất lượng cao"
    assert public_model_label("gpt-5.6-terra") == "Nhanh"
    assert "gpt" not in public_model_label("gpt-unknown").lower()


def test_incremental_image_hold_never_makes_balance_negative(tmp_path, monkeypatch):
    db_url = f"sqlite:///{(tmp_path / 'chat-credit.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", db_url)
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session(); db = next(gen)
    try:
        user = tao_nguoi_dung(db, email="chat-credit@test.com",
                              password="Strong-pass-123", is_verified=True)
        credit.cap_tay(db, user.id, 3, by="test")
        db.flush(); user_id = user.id
        credit.giu_cho(db, user_id, 3, "turn-image")
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    from apps.chataistudio.routes import _hold_more
    assert _hold_more(user_id, "turn-image", 20) is False
    from apps.chataistudio.routes import _refund
    assert _refund(user_id, "turn-image") == 3
    gen = dbmod.get_session(); db = next(gen)
    try:
        assert credit.so_du(db, user_id) == 3
        assert credit.so_da_giu(db, "turn-image") == 3
    finally:
        try: next(gen)
        except StopIteration: pass
        dbmod.reset_engine()


def test_partial_reply_is_saved_and_charged_instead_of_lost(tmp_path, monkeypatch):
    db_url = f"sqlite:///{(tmp_path / 'chat-partial.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", db_url)
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "chat-partial-test")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        user = tao_nguoi_dung(db, email="chat-partial@test.com",
                              password="Strong-pass-123", is_verified=True)
        credit.cap_tay(db, user.id, 10, by="test")
        db.commit(); user_id = user.id
    finally:
        try: next(gen)
        except StopIteration: pass

    from apps.chataistudio import routes
    monkeypatch.setattr(routes.sc, "account", lambda: {"account": {"email": "test"}})
    monkeypatch.setattr(routes, "_models_cached", lambda: [])
    monkeypatch.setattr(routes.sc, "thread_start", lambda *_a, **_k: "thread-test")

    async def partial_stream(*_args, **_kwargs):
        yield {"method": "item/agentMessage/delta", "payload": {"delta": "Phần đã nhận"}}
        yield {"method": "tokens", "payload": {"total": 7}}
        yield {"method": "error", "payload": {"message": "provider stopped"}}

    monkeypatch.setattr(routes.sc, "turn_stream", partial_stream)
    from fastapi.testclient import TestClient
    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False)
    try:
        login = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', login.text).group(1)
        assert client.post("/login", data={"username": "chat-partial@test.com",
            "password": "Strong-pass-123", "csrf_token": token}).status_code == 303
        page = client.get("/chataistudio")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        made = client.post("/chataistudio/new", data={"csrf_token": csrf})
        conv_id = re.search(r"[?&]c=([^&]+)", made.headers["location"]).group(1)
        sent = client.post("/chataistudio/send", data={
            "csrf_token": csrf, "conv_id": conv_id, "message": "Kiểm tra partial"})
        assert sent.status_code == 200 and "provider stopped" in sent.text

        async def unaffordable_image(*_args, **_kwargs):
            yield {"method": "image", "payload": {
                "abs_path": str(tmp_path / "would-be-image.png"),
                "prompt": "image only"}}

        monkeypatch.setattr(routes.sc, "turn_stream", unaffordable_image)
        denied = client.post("/chataistudio/send", data={
            "csrf_token": csrf, "conv_id": conv_id, "message": "Tạo ảnh"})
        assert denied.status_code == 200
        assert "Không đủ credit" in denied.text
        assert '"credit_cost": 0' in denied.text

        from platform_core.models import ChatMessage
        gen = dbmod.get_session(); db = next(gen)
        try:
            messages = db.query(ChatMessage).filter_by(
                conversation_id=conv_id, role="assistant").all()
            assert [m.content for m in messages] == ["Phần đã nhận"]
            assert messages[0].tokens_total == 7
            assert credit.so_du(db, user_id) == 7
        finally:
            try: next(gen)
            except StopIteration: pass
    finally:
        client.close(); dbmod.reset_engine()
