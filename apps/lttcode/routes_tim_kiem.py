"""`POST /lttcode/search` — tìm kiếm web cho agent LTTCODE. Nghiệp vụ ở `tim_kiem.py`.

Gọi từ runtime trên máy người dùng, không có cookie ⇒ không CSRF; xác thực bằng
Bearer khoá thiết bị (`ltt_sk_`), như `/lttcode/revoke`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.lttcode import tim_kiem
from platform_core.public_api import keys as devkeys
from server.deps import get_db

router = APIRouter()

_KHONG_LUU = {"Cache-Control": "no-store"}


def _loi(ma: str, status: int) -> JSONResponse:
    return JSONResponse({"error": ma}, status_code=status, headers=_KHONG_LUU)


@router.post("/search")
async def tim(request: Request, db: Session = Depends(get_db)):
    header = request.headers.get("authorization", "")
    key = devkeys.verify(db, header[7:].strip()) if header.lower().startswith("bearer ") else None
    if key is None:
        return _loi("invalid_key", 401)
    try:
        body = await request.json()
    except ValueError:
        body = None
    body = body if isinstance(body, dict) else {}
    truy_van = str(body.get("query") or "").strip()[:tim_kiem.DO_DAI_TRUY_VAN]
    if not truy_van:
        return _loi("empty_query", 400)
    if not tim_kiem.GIOI_HAN.cho_phep(key.key_id):
        return _loi("rate_limited", 429)
    du_lieu = await tim_kiem.goi_searxng(truy_van)
    if du_lieu is None:
        return _loi("search_unavailable", 503)
    toi_da = body.get("max_results")
    toi_da = toi_da if isinstance(toi_da, int) and not isinstance(toi_da, bool) else tim_kiem.TOI_DA_NGUON
    return JSONResponse({"sources": tim_kiem.chuan_hoa(du_lieu, toi_da=toi_da)}, headers=_KHONG_LUU)
