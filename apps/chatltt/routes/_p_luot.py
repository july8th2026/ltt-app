"""_p_luot.py — gửi một lượt · xem luồng (SSE) · dừng.

    POST /chatltt/api/hoi-thoai/{conv_id}/luot     → 202 {execution_id, …}; lượt chạy ở thread
    GET  /chatltt/api/luot/{execution_id}/stream   → SSE: `snapshot` rồi sự kiện canonical, `: ping` khi chờ
    POST /chatltt/api/luot/{execution_id}/dung     → dừng (CSDL + cờ trong tiến trình)

SSE ở đây là **cửa xem**, không phải cửa chạy: đóng tab không giết lượt (AC-09).
Nối lại = mở lại `stream?after=<seq>` — snapshot đầu tiên mang đủ phần đã có.
"""
from __future__ import annotations

import json
import time
from typing import Iterator

from fastapi import Depends, Request
from fastapi.responses import StreamingResponse

from apps.chatltt.routes._chung import doc_json, json_ok, kiem_csrf, loi, router, uid
from apps.chatltt.services import dang_chay
from apps.chatltt.services import hoi_thoai as H
from apps.chatltt.services import luot as LUOT
from apps.chatltt.services import su_kien as S
from apps.chatltt.tables import ChatlttExecution
from server.auth.session import require_login
from server.deps import get_db

_SSE = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}
NHIP_POLL_GIAY = 1.0
PING_GIAY = 15.0


@router.post("/api/hoi-thoai/{conv_id}/luot")
async def gui(request: Request, conv_id: str, _=Depends(require_login), db=Depends(get_db)):
    than = await doc_json(request)
    if not kiem_csrf(request, than):
        return loi(403, "csrf")
    try:
        kq = LUOT.bat_dau(
            db, user_id=uid(request), conv_id=conv_id,
            van_ban=str(than.get("text") or ""),
            model_alias=str(than.get("model_alias") or ""),
            # Khai `parent_id: null` = "gắn ở gốc"; KHÔNG khai = "nối vào lá
            # đang xem". Hai ý nghĩa khác nhau, nên đọc theo **có mặt khoá**.
            parent_id=((str(than["parent_id"]) if than["parent_id"] else None)
                       if "parent_id" in than else LUOT.MAC_DINH),
            tao_lai_cua=(str(than["tao_lai_cua"]) if than.get("tao_lai_cua") else None),
            reasoning_effort=str(than.get("reasoning_effort") or ""),
            # Khoa anh da tai len truoc do. `bat_dau` kiem SO HUU va TRAN;
            # route khong tu kiem, vi mot ban chep thu hai cua phep kiem
            # so huu la ban se lech.
            anh=[str(x) for x in (than.get("anh") or []) if str(x or "").strip()])
    except H.KhongTimThay:
        return loi(404, "khong_tim_thay")
    except (LUOT.ThamSoSai, H.ThamSoSai) as e:
        return loi(400, "tham_so", str(e))
    LUOT.khoi_chay_nen(kq["execution_id"], user_id=uid(request))
    return json_ok(kq, 202)


def _sk(ten: str, than: dict) -> bytes:
    return (f"event: {ten}\n".encode() + b"data: " + json.dumps(than, ensure_ascii=False).encode()
            + b"\n\n")


def _xem(execution_id: str, user_id: str, after: int) -> Iterator[bytes]:
    from platform_core.db import get_session

    def snapshot():
        gen = get_session()
        db = next(gen)
        try:
            ex = db.get(ChatlttExecution, execution_id)
            if ex is None or ex.user_id != user_id:
                return None
            return S.snapshot(ex)
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

    snap = snapshot()
    if snap is None:
        yield _sk("response.failed", {"code": "khong_tim_thay"})
        return
    yield _sk("snapshot", snap)
    if snap["status"] not in ("streaming", "queued"):
        yield _sk("end", {"seq": snap["seq"]})
        return

    so = dang_chay.tim(execution_id)
    q = so.dang_ky() if so is not None else None
    if q is not None:
        try:
            for sk in dang_chay.theo_doi(q, cho_moi_lan_s=PING_GIAY):
                if sk is None:
                    yield b": ping\n\n"
                    continue
                yield _sk(str(sk.get("type")), sk)
        finally:
            so.huy_dang_ky(q)
        snap = snapshot() or snap
        yield _sk("snapshot", snap)
        yield _sk("end", {"seq": snap["seq"]})
        return

    # Lượt không chạy ở tiến trình này (hoặc vừa xong): đọc CSDL theo nhịp.
    seq = snap["seq"]
    t_ping = time.monotonic()
    while True:
        time.sleep(NHIP_POLL_GIAY)
        snap = snapshot()
        if snap is None:
            return
        if snap["seq"] != seq:
            seq = snap["seq"]
            yield _sk("snapshot", snap)
            t_ping = time.monotonic()
        elif time.monotonic() - t_ping >= PING_GIAY:
            yield b": ping\n\n"
            t_ping = time.monotonic()
        if snap["status"] not in ("streaming", "queued"):
            yield _sk("end", {"seq": snap["seq"]})
            return


@router.get("/api/luot/{execution_id}/stream")
def xem(request: Request, execution_id: str, after: int = 0, _=Depends(require_login)):
    return StreamingResponse(_xem(execution_id, uid(request), int(after or 0)),
                             media_type="text/event-stream", headers=_SSE)


@router.post("/api/luot/{execution_id}/dung")
async def dung(request: Request, execution_id: str, _=Depends(require_login), db=Depends(get_db)):
    than = await doc_json(request)
    if not kiem_csrf(request, than):
        return loi(403, "csrf")
    try:
        return json_ok(LUOT.dung(db, user_id=uid(request), execution_id=execution_id))
    except H.KhongTimThay:
        return loi(404, "khong_tim_thay")
