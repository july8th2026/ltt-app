"""
sidecar_client.py — client gọi dịch vụ SIDECAR `LTTStudioCodex` (loopback).

Platform web/worker KHÔNG import codex SDK trực tiếp — mọi thứ đi qua sidecar (tách
tiến trình stateful). Base URL + bearer token lấy từ env (setup/2 ghi vào app.env).
"""
from __future__ import annotations

import json
import os
from typing import AsyncIterator, Optional

import httpx


def _base() -> str:
    port = os.environ.get("LTT_CODEX_SIDECAR_PORT", "8110").strip() or "8110"
    return f"http://127.0.0.1:{port}"


def _headers() -> dict:
    tok = os.environ.get("LTT_CODEX_SIDECAR_TOKEN", "").strip()
    return {"Authorization": f"Bearer {tok}"} if tok else {}


class SidecarError(RuntimeError):
    pass


def _get(path: str, *, timeout: float = 60.0) -> dict:
    try:
        r = httpx.get(_base() + path, headers=_headers(), timeout=timeout)
    except httpx.HTTPError as e:
        raise SidecarError(f"Sidecar không phản hồi: {e}") from e
    if r.status_code != 200:
        raise SidecarError(f"Sidecar {path} HTTP {r.status_code}: {r.text[:200]}")
    return r.json()


def _post(path: str, body: Optional[dict] = None, *, timeout: float = 120.0) -> dict:
    try:
        r = httpx.post(_base() + path, headers=_headers(), json=body or {}, timeout=timeout)
    except httpx.HTTPError as e:
        raise SidecarError(f"Sidecar không phản hồi: {e}") from e
    if r.status_code != 200:
        raise SidecarError(f"Sidecar {path} HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


# ── Read-only ─────────────────────────────────────────────────────────────────
def models() -> list:
    return _get("/models").get("models", [])


def account() -> dict:
    return _get("/account")


def capabilities() -> dict:
    return _get("/capabilities")


def rate_limits() -> dict:
    return _get("/rate-limits")


def health() -> bool:
    try:
        return bool(httpx.get(_base() + "/health", timeout=5).json().get("ok"))
    except Exception:  # noqa: BLE001
        return False


# ── Login (admin) ─────────────────────────────────────────────────────────────
def login_api_key(api_key: str) -> dict:
    return _post("/login/api-key", {"api_key": api_key})


def device_start() -> dict:
    return _post("/login/device/start", {})


def device_wait(login_id: str, *, timeout: float = 900.0) -> dict:
    return _post("/login/device/wait", {"login_id": login_id}, timeout=timeout)


def logout() -> dict:
    return _post("/logout", {})


# ── Thread + turn ─────────────────────────────────────────────────────────────
def thread_start(user_id: str, conv: str, settings: Optional[dict] = None) -> str:
    return _post("/thread", {"user_id": user_id, "conv": conv,
                             "settings": settings or {}}).get("thread_id", "")


def history(thread_id: str, user_id: str, conv: str) -> list:
    r = _get(f"/thread/{thread_id}/history?user_id={user_id}&conv={conv}", timeout=120)
    return r.get("messages", [])


async def turn_stream(thread_id: str, user_id: str, conv: str, message: str,
                      settings: Optional[dict] = None,
                      images: Optional[list] = None) -> AsyncIterator[dict]:
    """Mở turn ở sidecar, yield từng sự kiện SSE (dict đã parse). Dùng cho route proxy."""
    body = {"user_id": user_id, "conv": conv, "message": message,
            "settings": settings or {}, "images": images or []}
    url = _base() + f"/thread/{thread_id}/turn"
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, headers=_headers(), json=body) as resp:
            if resp.status_code != 200:
                text = (await resp.aread()).decode(errors="replace")[:300]
                raise SidecarError(f"turn HTTP {resp.status_code}: {text}")
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    try:
                        yield json.loads(line[6:])
                    except Exception:  # noqa: BLE001
                        continue
