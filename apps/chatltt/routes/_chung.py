"""_chung.py — router + helper dùng chung cho các mảnh route của ChatLTT."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from server.auth.csrf import issue_csrf_token, verify_csrf_token  # noqa: F401
from server.deps import user_hien_tai

router = APIRouter(tags=["chatltt"])

NO_STORE = {"Cache-Control": "no-store"}


def uid(request: Request) -> str:
    u = user_hien_tai(request)
    if u is None:
        raise HTTPException(status_code=401, detail="chua dang nhap")
    return str(u.id)


def json_ok(than: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(than, status_code=status_code, headers=NO_STORE)


def loi(ma: int, code: str, thong_diep: str = "") -> JSONResponse:
    """Lỗi JSON cho client React: `{"error": {"code", "message"}}`, no-store (Q88)."""
    return JSONResponse({"error": {"code": code, "message": thong_diep}},
                        status_code=ma, headers=NO_STORE)


async def doc_json(request: Request) -> dict:
    try:
        than = await request.json()
    except (ValueError, json.JSONDecodeError):
        than = {}
    return than if isinstance(than, dict) else {}


def kiem_csrf(request: Request, than: dict) -> bool:
    """CSRF cho JSON: header `X-CSRF-Token` (React) hoặc trường `csrf_token` (form)."""
    token = request.headers.get("X-CSRF-Token", "") or str(than.get("csrf_token", "") or "")
    return verify_csrf_token(request, token)
