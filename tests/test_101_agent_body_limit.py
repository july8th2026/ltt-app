from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from server.request_body_limit import AgentBodyLimitMiddleware


def _client(limit=32):
    async def echo(request: Request):
        return JSONResponse({"body": (await request.body()).decode()})
    app = Starlette(routes=[Route("/agent/api/workflows/plan", echo, methods=["POST"]),
                            Route("/other", echo, methods=["POST"])])
    app.add_middleware(AgentBodyLimitMiddleware, limit=limit)
    return TestClient(app)


def test_agent_body_cap_runs_before_endpoint_and_preserves_small_body():
    client = _client()
    assert client.post("/agent/api/workflows/plan", content="small").json()["body"] == "small"
    assert client.post("/agent/api/workflows/plan", content="x" * 33).status_code == 413


def test_non_agent_endpoint_is_not_affected():
    assert _client().post("/other", content="x" * 100).status_code == 200
