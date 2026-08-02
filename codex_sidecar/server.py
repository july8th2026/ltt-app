"""
server.py — dịch vụ HTTP loopback bọc Codex app-server (SIDECAR).

Chỉ nghe 127.0.0.1, bảo vệ bằng bearer token (`LTT_CODEX_SIDECAR_TOKEN`). Platform
web/worker gọi tới. Endpoint: health/models/account/capabilities/rate-limits,
login (device-code + api key), thread (start), turn (SSE stream), history.

Chat-only: sandbox read-only, ảnh do agent sinh ra được lưu file + báo path tuyệt
đối trong sự kiện SSE `image` để platform copy sang R2.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import shutil
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from codex_sidecar.runtime import get_runtime

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("codex_sidecar")

app = FastAPI(title="LTT Codex Sidecar")

_TOKEN = os.environ.get("LTT_CODEX_SIDECAR_TOKEN", "").strip()
_logins: dict = {}          # login_id -> device-login handle
_active_handles: dict = {}  # thread_id -> turn handle (để interrupt khi client ngắt)


def _auth(authorization: str = Header(default="")) -> None:
    if not _TOKEN:
        return  # dev: chưa đặt token → không chặn (chỉ nghe loopback)
    if authorization != f"Bearer {_TOKEN}":
        raise HTTPException(status_code=401, detail="sidecar: sai token")


async def _safe_interrupt(handle) -> None:
    try:
        if hasattr(handle, "interrupt"):
            await handle.interrupt()
    except Exception:  # noqa: BLE001
        pass


def _persist_image_abs(ws: Path, item: dict):
    """Copy ảnh agent sinh (CODEX_HOME/generated_images) vào workspace → trả (abs_path, name)."""
    dest = Path(ws) / "_generated_images"
    sp = item.get("saved_path") or item.get("savedPath")
    try:
        if sp and Path(sp).is_file():
            dest.mkdir(parents=True, exist_ok=True)
            name = Path(sp).name
            shutil.copy2(sp, dest / name)
            return str(dest / name), name
        result = item.get("result")
        if result and isinstance(result, str) and len(result) > 100:
            dest.mkdir(parents=True, exist_ok=True)
            name = (item.get("id") or "image").replace("/", "_") + ".png"
            (dest / name).write_bytes(base64.b64decode(result))
            return str(dest / name), name
    except Exception:  # noqa: BLE001
        log.exception("[sidecar] persist image error")
    return None, None


def _serialize_event(ev) -> dict:
    payload = getattr(ev, "payload", None)
    if hasattr(payload, "model_dump"):
        try:
            p = payload.model_dump(mode="json")
        except Exception:  # noqa: BLE001
            p = str(payload)
    else:
        p = payload
    return {"method": getattr(ev, "method", "?"), "payload": p}


# ── Read-only info ────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"ok": True}


@app.get("/models")
async def models(_: None = Depends(_auth)):
    return {"models": await get_runtime().list_models()}


@app.get("/account")
async def account(_: None = Depends(_auth)):
    return await get_runtime().account()


@app.get("/capabilities")
async def capabilities(_: None = Depends(_auth)):
    return await get_runtime().capabilities()


@app.get("/rate-limits")
async def rate_limits(_: None = Depends(_auth)):
    return await get_runtime().rate_limits()


# ── Login ─────────────────────────────────────────────────────────────────────
class ApiKeyIn(BaseModel):
    api_key: str


@app.post("/login/api-key")
async def login_api_key(body: ApiKeyIn, _: None = Depends(_auth)):
    await get_runtime().login_api_key(body.api_key.strip())
    await get_runtime().reload()
    return {"ok": True}


@app.post("/login/device/start")
async def login_device_start(_: None = Depends(_auth)):
    handle = await get_runtime().start_device_login()
    lid = uuid.uuid4().hex
    _logins[lid] = handle
    return {"login_id": lid,
            "verification_url": getattr(handle, "verification_url", None)
            or getattr(handle, "verificationUrl", None),
            "user_code": getattr(handle, "user_code", None)
            or getattr(handle, "userCode", None)}


class WaitIn(BaseModel):
    login_id: str


@app.post("/login/device/wait")
async def login_device_wait(body: WaitIn, _: None = Depends(_auth)):
    handle = _logins.get(body.login_id)
    if handle is None:
        raise HTTPException(404, "login_id không tồn tại/đã hết hạn")
    try:
        await handle.wait()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Đăng nhập thất bại: {e}")
    finally:
        _logins.pop(body.login_id, None)
    await get_runtime().reload()
    return {"ok": True}


@app.post("/logout")
async def logout(_: None = Depends(_auth)):
    await get_runtime().logout()
    return {"ok": True}


# ── Thread + turn (SSE) ───────────────────────────────────────────────────────
class ThreadIn(BaseModel):
    user_id: str
    conv: str
    settings: dict = {}


@app.post("/thread")
async def thread_start(body: ThreadIn, _: None = Depends(_auth)):
    th = await get_runtime().start_thread(body.user_id, body.conv, settings=body.settings)
    return {"thread_id": th.id}


class TurnIn(BaseModel):
    user_id: str
    conv: str
    message: str
    settings: dict = {}
    images: list = []           # data-URL (vision) tuỳ chọn


@app.post("/thread/{tid}/turn")
async def thread_turn(tid: str, body: TurnIn, request: Request, _: None = Depends(_auth)):
    rt = get_runtime()
    settings = body.settings or {}
    turn_input = rt.build_turn_input(body.message, body.images or [])
    effort = rt.effort_of(settings.get("effort"))

    async def _open_turn():
        try:
            thread = await rt.get_thread(tid, body.user_id, body.conv, settings=settings)
        except Exception as e:  # noqa: BLE001
            low = str(e).lower()
            if "rollout" in low or "not found" in low:
                thread = await rt.start_thread(body.user_id, body.conv, settings=settings)
                try:
                    rt._threads[tid] = thread
                except Exception:  # noqa: BLE001
                    pass
            else:
                raise
        try:
            return await (thread.turn(turn_input, effort=effort) if effort
                          else thread.turn(turn_input))
        except Exception:  # noqa: BLE001
            rt.evict_thread(tid)
            thread = await rt.resume_thread(tid, body.user_id, body.conv, settings=settings)
            return await (thread.turn(turn_input, effort=effort) if effort
                          else thread.turn(turn_input))

    def _sse(obj) -> str:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    async def gen():
        handle = None
        completed = False
        ws_dir = rt.workspace_for(body.user_id, body.conv)
        try:
            handle = await _open_turn()
            _active_handles[tid] = handle
            failed = None
            async for ev in handle.stream():
                method = getattr(ev, "method", "")
                serialized = _serialize_event(ev)
                yield _sse(serialized)
                pl = serialized.get("payload") or {}
                tu = pl.get("token_usage") or pl.get("tokenUsage")
                if isinstance(tu, dict):
                    tot = tu.get("total") or {}
                    tk = tot.get("total_tokens") or tot.get("totalTokens")
                    inp = tot.get("input_tokens") or tot.get("inputTokens")
                    outp = tot.get("output_tokens") or tot.get("outputTokens")
                    if tk is not None:
                        yield _sse({"method": "tokens", "payload": {
                            "total": tk, "input": inp, "output": outp,
                            "context": tu.get("model_context_window") or tu.get("modelContextWindow")}})
                if method == "item/completed":
                    item = (serialized.get("payload") or {}).get("item") or {}
                    if item.get("type") == "imageGeneration":
                        abspath, name = _persist_image_abs(ws_dir, item)
                        if abspath:
                            yield _sse({"method": "image", "payload": {
                                "abs_path": abspath, "name": name,
                                "prompt": item.get("revised_prompt")
                                or item.get("revisedPrompt") or ""}})
                if method == "turn/completed":
                    turn = getattr(getattr(ev, "payload", None), "turn", None)
                    st = getattr(getattr(turn, "status", None), "value", None) \
                        or getattr(turn, "status", None)
                    if str(st) == "failed":
                        failed = turn
            if failed is None:
                yield _sse({"method": "done"})
                completed = True
            else:
                msg = getattr(getattr(failed, "error", None), "message", "") or "Lượt chạy thất bại"
                yield _sse({"method": "error", "payload": {"message": msg}})
        except Exception as e:  # noqa: BLE001
            log.exception("[sidecar] turn fatal")
            yield _sse({"method": "error", "payload": {"message": str(e)}})
        finally:
            if not completed and handle is not None:
                try:
                    asyncio.create_task(_safe_interrupt(handle))
                except Exception:  # noqa: BLE001
                    pass
            if _active_handles.get(tid) is handle:
                _active_handles.pop(tid, None)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/thread/{tid}/history")
async def thread_history(tid: str, user_id: str, conv: str, _: None = Depends(_auth)):
    rt = get_runtime()
    try:
        thread = await rt.get_thread(tid, user_id, conv, settings={})
        resp = await thread.read(include_turns=True)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Không đọc được lịch sử: {e}")
    d = resp.model_dump(mode="json")
    ws = rt.workspace_for(user_id, conv)
    msgs = []
    for turn in (d.get("thread", {}).get("turns") or []):
        for it in (turn.get("items") or []):
            t = it.get("type")
            if t == "userMessage":
                txt = "".join(c.get("text", "") for c in (it.get("content") or [])
                              if c.get("type") == "text")
                if txt:
                    msgs.append({"role": "user", "text": txt})
            elif t == "agentMessage":
                if it.get("text"):
                    msgs.append({"role": "assistant", "text": it["text"]})
            elif t == "imageGeneration":
                abspath, name = _persist_image_abs(ws, it)
                if abspath:
                    msgs.append({"role": "assistant", "type": "image",
                                 "abs_path": abspath, "name": name,
                                 "text": it.get("revised_prompt") or it.get("revisedPrompt") or ""})
    return {"messages": msgs}
