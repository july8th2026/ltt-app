"""P9 regression: production Canvas bundle, cache, CSP and release freshness."""
from __future__ import annotations

import json
import gzip
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def canvas_client(tmp_path, monkeypatch):
    db_url = f"sqlite:///{(tmp_path / 'canvas.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", db_url)
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    tao_nguoi_dung(db, email="canvas@example.com", password="Strong-pass-123",
                   is_verified=True)
    db.commit()
    db.close()
    dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    client = TestClient(create_app(env={
        "LTT_ENV": "local-server-test", "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "canvas-test-session-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
    }), base_url="https://testserver", follow_redirects=True)
    login = client.get("/login")
    import re
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', login.text).group(1)
    response = client.post("/login", data={
        "username": "canvas@example.com", "password": "Strong-pass-123",
        "csrf_token": csrf, "next": "/agent/canvas",
    })
    assert response.status_code == 200
    yield client
    client.close()
    dbmod.reset_engine()


def test_canvas_uses_hashed_production_assets_and_cache_policy(canvas_client):
    page = canvas_client.get("/agent/canvas")
    assert page.status_code == 200
    assert 'id="agent-canvas-root"' in page.text
    assert "@vite/client" not in page.text
    manifest = json.loads((ROOT / "server/static/agent-canvas/.vite/manifest.json")
                          .read_text(encoding="utf-8"))
    entry = manifest["src/main.tsx"]
    assets = [entry["file"], *entry.get("css", [])]
    for asset in assets:
        assert f"/static/agent-canvas/{asset}" in page.text
        response = canvas_client.get(f"/static/agent-canvas/{asset}")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert page.headers["cache-control"] == "no-store"
    assert "'unsafe-eval'" not in page.headers["content-security-policy"]


def test_canvas_bundle_is_fresh_hashed_and_has_no_source_maps():
    from tools.build_release import verify_frontend_bundle
    verify_frontend_bundle(str(ROOT))
    assert not list((ROOT / "server/static/agent-canvas").rglob("*.map"))


def test_release_rejects_stale_canvas(monkeypatch):
    from tools import build_release
    monkeypatch.setattr(build_release, "canvas_source_sha256", lambda _root: "0" * 64)
    with pytest.raises(SystemExit, match="stale"):
        build_release.verify_frontend_bundle(str(ROOT))


def test_canvas_source_digest_ignores_tool_caches(tmp_path):
    from tools.build_release import canvas_source_sha256
    source = tmp_path / "frontend/agent-canvas"
    source.mkdir(parents=True)
    (source / "main.ts").write_text("export {}", encoding="utf-8")
    before = canvas_source_sha256(str(tmp_path))
    cache = source / ".pytest_cache"; cache.mkdir()
    (cache / "README.md").write_text("cache", encoding="utf-8")
    assert canvas_source_sha256(str(tmp_path)) == before


def test_release_carries_canvas_inputs_and_output_but_not_node_modules():
    from tools.build_release import collect_files
    files = {rel for _full, rel in collect_files(str(ROOT))}
    assert "frontend/agent-canvas/package-lock.json" in files
    assert "server/static/agent-canvas/.vite/manifest.json" in files
    assert "server/static/agent-canvas/build-meta.json" in files
    assert not any("node_modules" in rel or rel.endswith(".tsbuildinfo") for rel in files)


def test_frontend_toolchain_is_exactly_pinned():
    package = json.loads((ROOT / "frontend/agent-canvas/package.json").read_text("utf-8"))
    assert package["engines"]["node"] == "22.12.0"
    assert (ROOT / "frontend/agent-canvas/.nvmrc").read_text("ascii").strip() == "22.12.0"
    for version in [*package["dependencies"].values(), *package["devDependencies"].values()]:
        assert version[0].isdigit(), version


def test_canvas_bundle_stays_within_p11_size_budget():
    manifest = json.loads((ROOT / "server/static/agent-canvas/.vite/manifest.json")
                          .read_text(encoding="utf-8"))
    javascript = ROOT / "server/static/agent-canvas" / manifest["src/main.tsx"]["file"]
    payload = javascript.read_bytes()
    assert len(payload) <= 500_000
    assert len(gzip.compress(payload, compresslevel=9)) <= 150_000
