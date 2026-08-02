"""
Rate-limit per-user (chống script/lạm dụng endpoint app) — anti-reverse V4/V5.
Kiểm middleware: POST vượt ngưỡng → 429; GET không bị chặn; path miễn trừ không chặn;
endpoint "expensive" siết chặt hơn general.
"""
from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from server.usage_rate_limit import UsageRateLimitMiddleware


def _app(general=3, expensive=2):
    async def ok(request):
        return PlainTextResponse("ok")
    routes = [
        Route("/taovideo/queue", ok, methods=["POST", "GET"]),
        Route("/taovideo/translate", ok, methods=["POST"]),
        Route("/login", ok, methods=["POST"]),
        Route("/agent/api/workflows/plan", ok, methods=["POST"]),
        Route("/agent/api/runs/x/approve", ok, methods=["POST"]),
    ]
    app = Starlette(routes=routes)
    app.add_middleware(UsageRateLimitMiddleware, general_per_min=general,
                       expensive_per_min=expensive)
    return TestClient(app)


def test_post_general_vuot_nguong_429():
    c = _app(general=3)
    for _ in range(3):
        assert c.post("/taovideo/queue").status_code == 200
    assert c.post("/taovideo/queue").status_code == 429


def test_get_khong_bi_chan():
    c = _app(general=1)
    for _ in range(5):
        assert c.get("/taovideo/queue").status_code == 200   # GET miễn


def test_expensive_siet_chat_hon():
    c = _app(general=100, expensive=2)
    assert c.post("/taovideo/translate").status_code == 200
    assert c.post("/taovideo/translate").status_code == 200
    assert c.post("/taovideo/translate").status_code == 429   # /translate cap 2


def test_login_mien_tru():
    c = _app(general=1)
    for _ in range(5):
        assert c.post("/login").status_code == 200   # có limiter riêng theo IP


def test_agent_plan_va_approve_dung_expensive_limiter():
    c = _app(general=100, expensive=2)
    assert c.post("/agent/api/workflows/plan").status_code == 200
    assert c.post("/agent/api/runs/x/approve").status_code == 200
    # Cùng user/IP + cùng bucket expensive: request thứ ba bị chặn.
    assert c.post("/agent/api/workflows/plan").status_code == 429
