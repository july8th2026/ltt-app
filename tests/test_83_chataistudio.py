"""
CHAT AI STUDIO (app `chataistudio` + sidecar). Kiểm phần KHÔNG cần tài khoản/
sidecar thật: giá credit, registry nạp sạch (no job_types), model chat, sidecar
client parse env + base url, an toàn key ảnh. Nghiệm thu chat thật = trình duyệt.
"""
from __future__ import annotations

import pytest


def test_cost_gia_phang():
    from apps.chataistudio import cost
    assert cost.reserve_credit() == cost.CREDIT_PER_MESSAGE
    assert cost.settle_credit(0) == cost.CREDIT_PER_MESSAGE
    assert cost.settle_credit(1) == cost.CREDIT_PER_MESSAGE + cost.CREDIT_PER_IMAGE
    assert cost.settle_credit(2) == cost.CREDIT_PER_MESSAGE + 2 * cost.CREDIT_PER_IMAGE


def test_app_nap_sach_khong_job_types():
    from platform_core.registry import discover
    a = {x.manifest.slug: x for x in discover()}.get("chataistudio")
    assert a is not None and a.error == "" and a.router is not None
    # Chat chạy trong web (không worker) → KHÔNG khai job_types (nên không cần credit_cost).
    assert a.manifest.job_types == ()
    assert a.manifest.credit_cost is None


def test_models_chat_co_trong_platform():
    """models.py có 2 bảng chat (Alembic thấy qua Base.metadata)."""
    from platform_core.models import ChatConversation, ChatMessage
    assert ChatConversation.__tablename__ == "chat_conversations"
    assert ChatMessage.__tablename__ == "chat_messages"


def test_sidecar_client_base_va_headers(monkeypatch):
    from apps.chataistudio import sidecar_client as sc
    monkeypatch.setenv("LTT_CODEX_SIDECAR_PORT", "8123")
    monkeypatch.setenv("LTT_CODEX_SIDECAR_TOKEN", "abc123")
    assert sc._base() == "http://127.0.0.1:8123"
    assert sc._headers() == {"Authorization": "Bearer abc123"}


def test_sidecar_client_khong_token_khong_header(monkeypatch):
    from apps.chataistudio import sidecar_client as sc
    monkeypatch.delenv("LTT_CODEX_SIDECAR_TOKEN", raising=False)
    assert sc._headers() == {}


def test_sidecar_client_models_loi_tra_rong(monkeypatch):
    """Sidecar lỗi → models() ném SidecarError (route bọc lại)."""
    from apps.chataistudio import sidecar_client as sc

    def _boom(*a, **k):
        raise sc.httpx.HTTPError("down")
    monkeypatch.setattr(sc.httpx, "get", _boom)
    with pytest.raises(sc.SidecarError):
        sc.models()


def test_migration_head_co_chat():
    """Migration chat ai studio tồn tại + nối đúng head payment."""
    import pathlib
    p = pathlib.Path(__file__).resolve().parent.parent / "alembic" / "versions" / "20260801_1600_chat_ai_studio.py"
    txt = p.read_text(encoding="utf-8")
    assert "a1b2c3d4e5f6" in txt and "f0a1b2c3d4e5" in txt
    assert "chat_conversations" in txt and "chat_messages" in txt
