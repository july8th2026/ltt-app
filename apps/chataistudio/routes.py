"""
UI app `chataistudio` — CHAT AI STUDIO.

C1: admin đăng nhập tài khoản ChatGPT cho sidecar.
C2/C3: chat streaming (SSE) + tạo ảnh trong phiên, per-user (Postgres), credit giá
phẳng. Chat chạy trong tiến trình WEB (không qua worker) — gọi sidecar loopback.

Cô lập: mọi truy vấn hội thoại/tin nhắn lọc theo user_id người đăng nhập.
Router KHÔNG tự viết prefix.
"""
from __future__ import annotations

import io
import json
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import (HTMLResponse, JSONResponse, RedirectResponse,
                               Response, StreamingResponse)
from sqlalchemy import select

from apps.chataistudio import cost
from apps.chataistudio import sidecar_client as sc
from apps.chataistudio.manifest import MANIFEST
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

router = APIRouter(tags=["chataistudio"])


# ── DB helpers (per-user isolation) ───────────────────────────────────────────
def _sess():
    from platform_core.db import get_session
    return get_session()


def _conv_of_user(db, user_id: str, conv_id: str):
    from platform_core.models import ChatConversation
    c = db.get(ChatConversation, conv_id)
    return c if (c is not None and c.user_id == user_id) else None


def _list_convs(db, user_id: str):
    from platform_core.models import ChatConversation
    return db.execute(
        select(ChatConversation).where(ChatConversation.user_id == user_id)
        .order_by(ChatConversation.updated_at.desc()).limit(100)
    ).scalars().all()


def _messages(db, conv_id: str):
    from platform_core.models import ChatMessage
    return db.execute(
        select(ChatMessage).where(ChatMessage.conversation_id == conv_id)
        .order_by(ChatMessage.created_at.asc())
    ).scalars().all()


def _models_cached():
    try:
        return sc.models()
    except Exception:  # noqa: BLE001
        return []


# ── Trang chat ────────────────────────────────────────────────────────────────
@router.get("", response_class=HTMLResponse)
def page(request: Request, c: str = "", user: str = Depends(require_login)):
    u = user_hien_tai(request)
    if u is None:
        return RedirectResponse("/login?next=/chataistudio", status_code=303)
    user_is_admin = getattr(u, "role", "") == "admin"
    try:
        acc = sc.account()
    except Exception:  # noqa: BLE001
        acc = {"error": "sidecar"}
    logged_in = bool(acc.get("account"))
    convs = active = None
    messages = []
    gen = _sess(); db = next(gen)
    try:
        convs = _list_convs(db, u.id)
        active = _conv_of_user(db, u.id, c) if c else None
        if active is not None:
            messages = [{"role": m.role, "content": m.content, "image_key": m.image_key,
                         "image_prompt": m.image_prompt} for m in _messages(db, active.id)]
        convs = [{"id": x.id, "title": x.title or "(chưa đặt tên)", "model": x.model} for x in convs]
        active = {"id": active.id, "title": active.title, "model": active.model,
                  "custom_instructions": active.custom_instructions} if active else None
    finally:
        try: next(gen)
        except StopIteration: pass
    return templates.TemplateResponse(request, "chataistudio.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request), "user_is_admin": user_is_admin,
        "logged_in": logged_in, "convs": convs, "active": active,
        "messages": messages, "models": _models_cached(),
    })


@router.post("/new")
def new_conv(request: Request, csrf_token: str = Form(...), model: str = Form("gpt-5.6-sol"),
             custom_instructions: str = Form(""), user: str = Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(400, "CSRF")
    u = user_hien_tai(request)
    if u is None:
        raise HTTPException(400, "Cần đăng nhập.")
    from platform_core.models import ChatConversation
    gen = _sess(); db = next(gen)
    try:
        conv = ChatConversation(user_id=u.id, model=(model or "gpt-5.6-sol"),
                                custom_instructions=(custom_instructions or "")[:4000], title="")
        db.add(conv); db.commit()
        cid = conv.id
    finally:
        try: next(gen)
        except StopIteration: pass
    return RedirectResponse(f"/chataistudio?c={cid}", status_code=303)


@router.post("/delete/{conv_id}")
def delete_conv(request: Request, conv_id: str, csrf_token: str = Form(...),
                user: str = Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(400, "CSRF")
    u = user_hien_tai(request)
    from platform_core.models import ChatMessage
    gen = _sess(); db = next(gen)
    try:
        conv = _conv_of_user(db, u.id, conv_id) if u else None
        if conv is not None:
            for m in _messages(db, conv_id):
                db.delete(m)
            db.delete(conv); db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    return RedirectResponse("/chataistudio", status_code=303)


# ── Gửi tin (SSE streaming) ───────────────────────────────────────────────────
@router.post("/send")
async def send(request: Request, csrf_token: str = Form(...), conv_id: str = Form(""),
               message: str = Form(""), user: str = Depends(require_login)):
    from platform_core import credit
    from platform_core.models import ChatConversation, ChatMessage
    from platform_core.storage import get_storage

    def _sse(obj) -> str:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    def _err_stream(msg: str):
        async def g():
            yield _sse({"type": "error", "message": msg})
        return StreamingResponse(g(), media_type="text/event-stream")

    if not verify_csrf_token(request, csrf_token):
        return _err_stream("Phiên hết hạn — tải lại trang.")
    u = user_hien_tai(request)
    if u is None:
        return _err_stream("Cần đăng nhập bằng tài khoản người dùng.")
    msg = (message or "").strip()
    if not msg:
        return _err_stream("Tin nhắn trống.")

    # Pre-flight ĐỒNG BỘ: load/tạo hội thoại, giữ chỗ credit, lưu tin user, bảo đảm thread.
    reserve = cost.reserve_credit()
    umsg_id = uuid.uuid4().hex
    gen = _sess(); db = next(gen)
    conv_settings = {}
    try:
        conv = _conv_of_user(db, u.id, conv_id) if conv_id else None
        if conv is None:
            conv = ChatConversation(user_id=u.id, model="gpt-5.6-sol", title="")
            db.add(conv); db.flush()
        try:
            credit.giu_cho(db, u.id, reserve, umsg_id)
        except credit.ThieuCreditError as e:
            db.rollback()
            return _err_stream(str(e))
        db.add(ChatMessage(id=umsg_id, conversation_id=conv.id, user_id=u.id,
                           role="user", content=msg[:20000]))
        if not conv.title:
            conv.title = msg[:48]
        conv_id2 = conv.id
        cthread = conv.codex_thread_id
        conv_settings = {"model": conv.model,
                         "developer_instructions": conv.custom_instructions}
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    owner = u.id

    async def gen_stream():
        storage = get_storage()
        yield _sse({"type": "conv", "id": conv_id2})
        # Bảo đảm có Codex thread (ngữ cảnh) — tạo nếu chưa.
        tid = cthread
        try:
            if not tid:
                tid = sc.thread_start(owner, conv_id2, conv_settings)
                g2 = _sess(); d2 = next(g2)
                try:
                    cc = d2.get(ChatConversation, conv_id2)
                    if cc is not None:
                        cc.codex_thread_id = tid; d2.commit()
                finally:
                    try: next(g2)
                    except StopIteration: pass
        except Exception as e:  # noqa: BLE001
            _refund(owner, umsg_id)
            yield _sse({"type": "error", "message": f"Không tạo được phiên chat: {e}"})
            return

        reply = ""
        n_images = 0
        tokens_total = 0
        fin = {"done": False}   # đã settle/refund chưa (đảm bảo đúng MỘT lần)

        def _finalize_settle():
            # Quyết toán theo phần ĐÃ giao (text + số ảnh đã lưu). Idempotent theo hold.
            if fin["done"]:
                return
            fin["done"] = True
            _settle(owner, umsg_id, cost.settle_credit(n_images), conv_id2)

        def _finalize_refund():
            if fin["done"]:
                return
            fin["done"] = True
            _refund(owner, umsg_id)

        try:
            async for ev in sc.turn_stream(tid, owner, conv_id2, msg, conv_settings):
                m = ev.get("method", "")
                if m == "item/agentMessage/delta":
                    d = (ev.get("payload") or {}).get("delta") \
                        or (ev.get("payload") or {}).get("text") or ""
                    if d:
                        reply += d
                        yield _sse({"type": "delta", "text": d})
                elif m == "tokens":
                    tokens_total = (ev.get("payload") or {}).get("total") or tokens_total
                elif m == "image":
                    pl = ev.get("payload") or {}
                    abspath = pl.get("abs_path")
                    # Cap số ảnh/lượt (chống 1 lượt đẩy balance âm nhiều ảnh × 20cr).
                    if abspath and n_images < cost.MAX_IMAGES_PER_TURN:
                        try:
                            with open(abspath, "rb") as f:
                                data = f.read()
                            n_images += 1
                            ikey = f"chataistudio/{owner}/{conv_id2}/{uuid.uuid4().hex}.png"
                            storage.put(ikey, io.BytesIO(data), content_type="image/png")
                            _save_msg(owner, conv_id2, "assistant", "", ikey,
                                      pl.get("prompt", ""))
                            yield _sse({"type": "image",
                                        "url": f"/chataistudio/img/{ikey}",
                                        "prompt": pl.get("prompt", "")})
                        except Exception:  # noqa: BLE001
                            pass
                elif m == "error":
                    _finalize_refund()
                    yield _sse({"type": "error",
                                "message": (ev.get("payload") or {}).get("message") or "Lỗi"})
                    return
            # Xong: lưu tin assistant (text) + quyết toán credit + cập nhật hội thoại.
            if reply.strip():
                _save_msg(owner, conv_id2, "assistant", reply, "", "", tokens_total)
            _finalize_settle()
            yield _sse({"type": "done"})
        except Exception as e:  # noqa: BLE001
            _finalize_refund()
            yield _sse({"type": "error", "message": str(e)})
        finally:
            # Ngắt kết nối (GeneratorExit — BaseException, KHÔNG lọt except Exception)
            # vẫn phải kết sổ: đã giao ảnh/chữ → settle (chống ảnh miễn phí bằng cách
            # ngắt giữa chừng); chưa giao gì → refund.
            if not fin["done"]:
                if reply.strip() or n_images:
                    _finalize_settle()
                else:
                    _finalize_refund()

    return StreamingResponse(gen_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _save_msg(user_id, conv_id, role, content, image_key="", image_prompt="", tokens=0):
    from platform_core.models import ChatMessage
    gen = _sess(); db = next(gen)
    try:
        db.add(ChatMessage(conversation_id=conv_id, user_id=user_id, role=role,
                           content=content[:20000], image_key=image_key,
                           image_prompt=(image_prompt or "")[:500], tokens_total=int(tokens or 0)))
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass


def _settle(user_id, hold_id, actual, conv_id):
    from platform_core import credit
    from platform_core.models import ChatConversation
    from platform_core.models import _bay_gio
    gen = _sess(); db = next(gen)
    try:
        credit.quyet_toan(db, user_id, hold_id, int(actual))
        cc = db.get(ChatConversation, conv_id)
        if cc is not None:
            cc.updated_at = _bay_gio()
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass


def _refund(user_id, hold_id):
    from platform_core import credit
    gen = _sess(); db = next(gen)
    try:
        credit.hoan(db, user_id, hold_id); db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass


@router.get("/img/{key:path}")
def chat_image(request: Request, key: str, user: str = Depends(require_login)):
    """Serve ảnh chat từ R2 (presigned redirect) hoặc Local. Chỉ chủ sở hữu."""
    from platform_core.storage import StorageError, get_storage
    u = user_hien_tai(request)
    segs = key.split("/")
    if len(segs) < 2 or segs[0] != "chataistudio" or u is None or segs[1] != u.id:
        raise HTTPException(404, "Không tìm thấy.")
    storage = get_storage()
    try:
        direct = storage.url_for(key)
    except Exception:  # noqa: BLE001
        direct = None
    if direct:
        return RedirectResponse(direct, status_code=302)
    try:
        return StreamingResponse(storage.open(key), media_type="image/png")
    except (StorageError, FileNotFoundError):
        raise HTTPException(404, "Không tìm thấy ảnh.")


# ── Admin: đăng nhập tài khoản ChatGPT cho sidecar (C1) ───────────────────────
def _require_admin(request: Request):
    u = user_hien_tai(request)
    if u is None or getattr(u, "role", "") != "admin":
        raise HTTPException(status_code=404, detail="Không tìm thấy.")
    return u


@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, user: str = Depends(require_login)):
    _require_admin(request)
    acc = models = caps = rl = None
    err = ""
    try:
        acc = sc.account(); models = sc.models(); caps = sc.capabilities(); rl = sc.rate_limits()
    except Exception as e:  # noqa: BLE001
        err = str(e)
    logged_in = bool(acc and acc.get("account"))
    return templates.TemplateResponse(request, "chataistudio_admin.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "acc": acc, "models": models or [], "caps": caps or {}, "rate_limits": rl or {},
        "logged_in": logged_in, "error": err,
    })


@router.post("/admin/device/start")
def admin_device_start(request: Request, csrf_token: str = Form(...),
                       user: str = Depends(require_login)):
    _require_admin(request)
    if not verify_csrf_token(request, csrf_token):
        return JSONResponse({"ok": False, "error": "CSRF"}, status_code=400)
    try:
        return JSONResponse({"ok": True, **sc.device_start()})
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)


@router.post("/admin/device/wait")
def admin_device_wait(request: Request, csrf_token: str = Form(...),
                      login_id: str = Form(...), user: str = Depends(require_login)):
    _require_admin(request)
    if not verify_csrf_token(request, csrf_token):
        return JSONResponse({"ok": False, "error": "CSRF"}, status_code=400)
    try:
        sc.device_wait(login_id)
        return JSONResponse({"ok": True})
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)


@router.post("/admin/api-key")
def admin_api_key(request: Request, csrf_token: str = Form(...),
                  api_key: str = Form(...), user: str = Depends(require_login)):
    _require_admin(request)
    if not verify_csrf_token(request, csrf_token):
        return JSONResponse({"ok": False, "error": "CSRF"}, status_code=400)
    try:
        sc.login_api_key(api_key.strip())
        return JSONResponse({"ok": True})
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)


@router.post("/admin/logout")
def admin_logout(request: Request, csrf_token: str = Form(...),
                 user: str = Depends(require_login)):
    _require_admin(request)
    if not verify_csrf_token(request, csrf_token):
        return JSONResponse({"ok": False, "error": "CSRF"}, status_code=400)
    try:
        sc.logout()
        return JSONResponse({"ok": True})
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)
