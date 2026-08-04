from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from server.request_body_limit import AgentBodyLimitMiddleware


def _client(limit=32, asset_limit=256):
    async def echo(request: Request):
        return JSONResponse({"body": (await request.body()).decode()})
    app = Starlette(routes=[Route("/agent/api/workflows/plan", echo, methods=["POST"]),
                            Route("/agent/api/assets", echo, methods=["POST"]),
                            Route("/other", echo, methods=["POST"])])
    app.add_middleware(AgentBodyLimitMiddleware, limit=limit,
                       asset_limit=asset_limit)
    return TestClient(app)


def test_agent_body_cap_runs_before_endpoint_and_preserves_small_body():
    client = _client()
    assert client.post("/agent/api/workflows/plan", content="small").json()["body"] == "small"
    assert client.post("/agent/api/workflows/plan", content="x" * 33).status_code == 413


def test_non_agent_endpoint_is_not_affected():
    assert _client().post("/other", content="x" * 100).status_code == 200


def test_agent_asset_multipart_uses_dedicated_limit_without_buffering():
    client = _client()
    headers = {"content-type": "multipart/form-data; boundary=browser-test"}
    assert client.post("/agent/api/assets", content="x" * 100,
                       headers=headers).status_code == 200
    response = client.post("/agent/api/assets", content="x" * 257,
                           headers=headers)
    assert response.status_code == 413
    assert "Asset" in response.json()["detail"]


def test_agent_asset_exemption_requires_exact_path_and_multipart():
    client = _client()
    assert client.post("/agent/api/assets", content="x" * 100,
                       headers={"content-type": "application/json"}).status_code == 413
