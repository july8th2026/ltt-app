"""
UI app `chataistudio` — CHAT AI STUDIO.

C1: admin đăng nhập tài khoản ChatGPT cho sidecar.
C2/C3: chat streaming (SSE) + tạo ảnh trong phiên, per-user (Postgres), credit giá
phẳng. Chat chạy trong tiến trình WEB (không qua worker) — gọi sidecar loopback.

Cô lập: mọi truy vấn hội thoại/tin nhắn lọc theo user_id người đăng nhập.
Router KHÔNG tự viết prefix.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
import io
import json
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import (HTMLResponse, JSONResponse, RedirectResponse,
                               Response, StreamingResponse)
from sqlalchemy import select

from apps.chataistudio import luong_chat, sidecar_client as sc
from platform_core.llm import loi_ra_ngoai as LRN
from apps.chataistudio.manifest import MANIFEST
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

router = APIRouter(tags=["chataistudio"])
logger = logging.getLogger(__name__)


# ── DB helpers (per-user isolation) ───────────────────────────────────────────
def _sess():
    from platform_core.db import get_session
    return get_session()


def _conv_of_user(db, user_id: str, conv_id: str):
    from platform_core.models import ChatConversation
    c = db.get(ChatConversation, conv_id)
    return c if (c is not None and c.user_id == user_id) else None


def _list_convs(db, user_id: str, query: str = ""):
    from platform_core.models import ChatConversation, ChatMessage
    stmt = select(ChatConversation).where(ChatConversation.user_id == user_id)
    q = (query or "").strip()[:100]
    if q:
        matched = select(ChatMessage.conversation_id).where(
            ChatMessage.user_id == user_id, ChatMessage.content.ilike(f"%{q}%"))
        stmt = stmt.where((ChatConversation.title.ilike(f"%{q}%")) |
                          (ChatConversation.id.in_(matched)))
    return db.execute(
        stmt
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


def _public_models(models: list) -> list[dict]:
    from apps.chataistudio.features import public_model_label
    rows = []
    for model in models:
        model_id = str(model.get("id") or "").strip()
        if model_id:
            rows.append({"id": model_id, "model_label": public_model_label(model_id)})
    return rows


def _message_view(message) -> dict:
    created = getattr(message, "created_at", None)
    return {
        "role": message.role,
        "content": message.content,
        "image_key": message.image_key,
        "image_prompt": message.image_prompt,
        "tokens_total": int(getattr(message, "tokens_total", 0) or 0),
        "created_at": created.strftime("%H:%M · %d/%m/%Y") if created else "",
    }


# ── Trang chat ────────────────────────────────────────────────────────────────
@router.get("", response_class=HTMLResponse)
def page(request: Request, c: str = "", q: str = "", user: str = Depends(require_login)):
    from apps.chataistudio.features import public_model_label
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
        convs = _list_convs(db, u.id, q)
        active = _conv_of_user(db, u.id, c) if c else None
        if active is not None:
            messages = [_message_view(m) for m in _messages(db, active.id)]
        convs = [{"id": x.id, "title": x.title or _t('Hội thoại mới'),
                  "model_label": public_model_label(x.model)} for x in convs]
        active = {"id": active.id, "title": active.title, "model": active.model,
                  "model_label": public_model_label(active.model),
                  "custom_instructions": active.custom_instructions} if active else None
    finally:
        try: next(gen)
        except StopIteration: pass
    return templates.TemplateResponse(request, "chataistudio.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request), "user_is_admin": user_is_admin,
        "logged_in": logged_in, "convs": convs, "active": active,
        "messages": messages, "models": _public_models(_models_cached()), "query": q[:100],
    })


@router.post("/new")
def new_conv(request: Request, csrf_token: str = Form(...), model: str = Form("gpt-5.6-sol"),
             custom_instructions: str = Form(""), user: str = Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(400, "CSRF")
    u = user_hien_tai(request)
    if u is None:
        raise HTTPException(400, _t('Cần đăng nhập.'))
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
               message: str = Form(""), attachments: list[UploadFile] = File(default=[]),
               user: str = Depends(require_login)):
    from platform_core.models import ChatConversation, ChatMessage
    from platform_core.storage import get_storage

    def _sse(obj) -> str:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    def _err_stream(msg: str):
        async def g():
            yield _sse({"type": "error", "message": msg})
        return StreamingResponse(g(), media_type="text/event-stream")

    if not verify_csrf_token(request, csrf_token):
        return _err_stream(_t('Phiên hết hạn — tải lại trang.'))
    u = user_hien_tai(request)
    if u is None:
        return _err_stream(_t('Cần đăng nhập bằng tài khoản người dùng.'))
    msg = (message or "").strip()
    if not msg and not any(x.filename for x in attachments):
        return _err_stream(_t('Tin nhắn trống.'))
    from apps.chataistudio.features import MAX_FILES, context_message, parse_attachment
    parsed = []
    try:
        uploads = [x for x in attachments if x.filename]
        if len(uploads) > MAX_FILES:
            raise ValueError(_t('Mỗi lượt chỉ nhận tối đa 3 tệp.'))
        for upload in uploads:
            parsed.append(parse_attachment(await upload.read(), upload.content_type or "",
                                           upload.filename or "tệp"))
    except ValueError as exc:
        return _err_stream(str(exc))
    model_message = context_message(msg or "Hãy phân tích tệp đính kèm.", parsed)
    image_inputs = [item["data_url"] for item in parsed if item["kind"] == "image"]

    # Pre-flight ĐỒNG BỘ: load/tạo hội thoại, giữ chỗ credit, lưu tin user, bảo đảm thread.
    # ⛔ KHÔNG giữ credit ở đây nữa (pha 05.7). `runtime_noi_bo.luong.mo_luong`
    #    tự giành suất → ước token → giữ chỗ → commit → quyết toán trong
    #    `finally` của chính nó. Giữ thêm một vòng đời ở tầng app là **thu tiền
    #    hai lần** hoặc **hoàn nhầm** — hai lỗi sổ sách không đảo được.
    umsg_id = uuid.uuid4().hex
    gen = _sess(); db = next(gen)
    try:
        conv = _conv_of_user(db, u.id, conv_id) if conv_id else None
        if conv is None:
            conv = ChatConversation(user_id=u.id, model="gpt-5.6-sol", title="")
            db.add(conv); db.flush()
        visible = context_message(msg or "Hãy phân tích tệp đính kèm.",
                                  [x for x in parsed if x["kind"] == "text"])
        db.add(ChatMessage(id=umsg_id, conversation_id=conv.id, user_id=u.id,
                           role="user", content=visible[:20000]))
        storage = get_storage()
        for item in parsed:
            if item["kind"] != "image":
                continue
            ikey = f"chataistudio/{u.id}/{conv.id}/uploads/{uuid.uuid4().hex}.png"
            storage.put(ikey, io.BytesIO(item["data"]), content_type=item["mime"])
            db.add(ChatMessage(conversation_id=conv.id, user_id=u.id, role="user",
                               content="", image_key=ikey, image_prompt=item["name"]))
        if not conv.title:
            conv.title = (msg or (parsed[0]["name"] if parsed else _t('Hội thoại mới')))[:48]
        public_title = conv.title
        conv_id2 = conv.id
        # ⭐ Lấy lịch sử TRƯỚC khi thêm tin mới: `dung_messages` tự nối tin mới
        #    vào cuối, nên lấy sau sẽ gửi câu vừa gõ HAI lần.
        lich_su = list(_messages(db, conv.id))
        db.add(ChatMessage(id=umsg_id, conversation_id=conv.id, user_id=u.id,
                           role="user", content=visible[:20000]))
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    owner = u.id
    tin_gui = luong_chat.dung_messages(lich_su, model_message)

    async def gen_stream():
        from starlette.concurrency import iterate_in_threadpool

        yield _sse({"type": "conv", "id": conv_id2})
        if image_inputs:
            # ⛔ LTT_LLM là model VĂN BẢN. Ảnh tải lên vẫn được lưu (chúng là
            #    dữ liệu của khách), nhưng model không đọc được chúng. Nói ra,
            #    không im lặng bỏ qua: khách gửi ảnh rồi nhận một câu trả lời
            #    không nhắc gì tới nó sẽ tưởng model đã xem.
            yield _sse({"type": "warning", "message": _t(
                'Ảnh đã được lưu nhưng model văn bản chưa đọc được ảnh.')})

        g2 = _sess(); d2 = next(g2)
        try:
            # ⛔ `mo_luong` là generator ĐỒNG BỘ. Lặp thẳng nó trong `async def`
            #    sẽ CHẶN EVENT LOOP suốt cả lượt stream — mọi request khác của
            #    tiến trình web đứng chờ. Đẩy qua threadpool, đúng cách route
            #    `taovideo/translate` đã dùng `run_in_threadpool`.
            it = iterate_in_threadpool(luong_chat.chay(
                d2, user_id=owner, conv_id=conv_id2,
                messages=tin_gui, holder_id=umsg_id))
            async for ev in it:
                if ev.get("type") == "done":
                    tra_loi = str(ev.pop("text", "") or "")
                    if tra_loi.strip():
                        _save_msg(owner, conv_id2, "assistant", tra_loi, "", "",
                                  int(ev.get("tokens_total") or 0))
                    ev["title"] = public_title
                    ev["balance"] = _so_du(owner)
                    ev["warning"] = ""
                yield _sse(ev)
        except Exception as e:  # noqa: BLE001
            # ⛔ KHÔNG `str(e)`: thân lỗi thượng nguồn từng mang đường dẫn
            #    `.gguf`, id model nội bộ, `base_url` và IP nội bộ ra trình
            #    duyệt (đo 07/09). Chữ cho khách dựng từ MÃ.
            logger.warning("chataistudio_stream_hong conv=%s loai=%s",
                           conv_id2[:8], type(e).__name__)
            yield _sse({"type": "error", "message": LRN.cau("loi_noi_bo")})
        finally:
            try: next(g2)
            except StopIteration: pass

    return StreamingResponse(gen_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/branch/{conv_id}")
def branch_conv(request: Request, conv_id: str, csrf_token: str = Form(...),
                user: str = Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(400, "CSRF")
    from platform_core.models import ChatConversation, ChatMessage
    u = user_hien_tai(request); gen = _sess(); db = next(gen)
    try:
        source = _conv_of_user(db, u.id, conv_id) if u else None
        if source is None:
            raise HTTPException(404, _t('Không tìm thấy.'))
        clone = ChatConversation(user_id=u.id, title=("Nhánh · " + source.title)[:200],
                                 model=source.model,
                                 custom_instructions=source.custom_instructions)
        db.add(clone); db.flush()
        for m in _messages(db, source.id):
            db.add(ChatMessage(conversation_id=clone.id, user_id=u.id, role=m.role,
                               content=m.content, image_key=m.image_key,
                               image_prompt=m.image_prompt, tokens_total=m.tokens_total))
        db.commit(); target = clone.id
    finally:
        try: next(gen)
        except StopIteration: pass
    return RedirectResponse(f"{MANIFEST.route_prefix}?c={target}", status_code=303)


@router.get("/export/{conv_id}.{fmt}")
def export_conv(request: Request, conv_id: str, fmt: str,
                user: str = Depends(require_login)):
    from apps.chataistudio.features import export_json, export_markdown
    u = user_hien_tai(request); gen = _sess(); db = next(gen)
    try:
        conv = _conv_of_user(db, u.id, conv_id) if u else None
        if conv is None or fmt not in {"md", "json"}:
            raise HTTPException(404, _t('Không tìm thấy.'))
        messages = _messages(db, conv.id)
        if fmt == "json":
            data, media = export_json(conv.title, conv.model, messages), "application/json"
        else:
            data, media = export_markdown(conv.title, messages).encode("utf-8"), "text/markdown"
    finally:
        try: next(gen)
        except StopIteration: pass
    return Response(data, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="chat-{conv_id[:8]}.{fmt}"',
        "X-Content-Type-Options": "nosniff"})


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


def _so_du(user_id: str) -> int:
    """Số dư hiện tại, đọc SAU khi `mo_luong` đã quyết toán.

    ⭐ Phải mở phiên MỚI: generator chạy sau khi phản hồi đã bắt đầu, lúc đó
       phiên CSDL của request đã đóng — cùng bài học `runtime_noi_bo/luong.py`
       ghi ở đầu tệp.
    """
    from platform_core import credit
    gen = _sess(); db = next(gen)
    try:
        return credit.so_du(db, user_id)
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
        raise HTTPException(404, _t('Không tìm thấy.'))
    storage = get_storage()
    direct = storage.try_url_for(key)
    if direct:
        return RedirectResponse(direct, status_code=302)
    try:
        return StreamingResponse(storage.open(key), media_type="image/png")
    except (StorageError, FileNotFoundError):
        raise HTTPException(404, _t('Không tìm thấy ảnh.'))


# ── Admin: đăng nhập tài khoản ChatGPT cho sidecar (C1) ───────────────────────
def _require_admin(request: Request):
    u = user_hien_tai(request)
    if u is None or getattr(u, "role", "") != "admin":
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy.'))
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
