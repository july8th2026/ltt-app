"""Tuy chon hien thi, bang mau cong cu, tai san va bao gia."""
from __future__ import annotations

from __future__ import annotations
import mimetypes
import os
import io
import tempfile
import uuid
from pathlib import Path
from fastapi import Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import (JSONResponse, RedirectResponse, Response, 
                               StreamingResponse)
from sqlalchemy.orm import Session
from platform_core.agent.tools import (ToolParamsError, discover_tools, 
                                       validate_tool_params)
from platform_core.registry import RegistryError, credit_for, discover
from server.auth.csrf import verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db

from apps.agent.routes._shared import (
    _ASSET_LIMIT, _ASSET_MIME_PREFIXES, _PREFERENCES_SLUG, _palette_tool,
    _preferences_json, _preferences_row, _user, _verify_json_csrf, router)


@router.get("/api/preferences")
def get_preferences(request: Request, _identity: str = Depends(require_login),
                    db: Session = Depends(get_db)):
    user = _user(request)
    return JSONResponse(_preferences_json(_preferences_row(db, user.id)))


@router.put("/api/preferences")
async def save_preferences(request: Request, _identity: str = Depends(require_login),
                           db: Session = Depends(get_db)):
    body = await request.json()
    _verify_json_csrf(request, body)
    theme = str(body.get("theme", ""))
    catalog_mode = str(body.get("catalog_mode", ""))
    presentation_version = str(body.get("presentation_version", "creative-v1"))
    if theme not in {"light", "dark"} or catalog_mode not in {"simple", "advanced"}:
        raise HTTPException(status_code=422, detail="Tùy chọn giao diện không hợp lệ.")
    if presentation_version != "creative-v1":
        raise HTTPException(status_code=422, detail="Phiên bản trình bày không hợp lệ.")
    user = _user(request)
    from platform_core import app_projects
    row = _preferences_row(db, user.id)
    payload = {"theme": theme, "catalog_mode": catalog_mode,
               "presentation_version": presentation_version}
    try:
        if row:
            row = app_projects.save(
                db, project_id=row.id, user_id=user.id, app_slug=_PREFERENCES_SLUG,
                revision=row.revision, name="Agent UI preferences",
                schema_version=1, payload=payload)
        else:
            row = app_projects.create(
                db, user_id=user.id, app_slug=_PREFERENCES_SLUG,
                name="Agent UI preferences", schema_version=1, payload=payload)
    except app_projects.ProjectError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.flush()
    return JSONResponse(_preferences_json(row))


@router.get("/api/palette")
def workflow_palette(request: Request, _identity: str = Depends(require_login),
                     db: Session = Depends(get_db)):
    user = _user(request)
    from platform_core import app_access
    loaded = discover()
    allowed = {item.slug for item in loaded
               if app_access.muc_quyen(db, user, item.slug) == app_access.ENABLED}
    tools = discover_tools(apps=loaded, allowed_slugs=allowed)
    owners = {tool.name: item for item in loaded for tool in item.manifest.tools}
    from platform_core import providers
    return JSONResponse({"version": 2,
        "routing": {"mode": "platform_auto", "server_choice": "managed",
                    "description": "Nền tảng chọn provider khả dụng; không lộ API key."},
        "models": providers.model_catalog(), "tools": [
        _palette_tool(name, spec, owners[name], loaded)
        for name, spec in sorted(tools.items())]})


@router.post("/api/assets")
async def workflow_asset_upload(request: Request, file: UploadFile = File(...),
                                _identity: str = Depends(require_login)):
    """Upload an owned Canvas asset; output is a server-generated storage key."""
    token = request.headers.get("X-CSRF-Token", "")
    if not verify_csrf_token(request, token):
        raise HTTPException(status_code=400, detail="Phiên đã hết hạn.")
    user = _user(request)
    content_type = str(file.content_type or "").lower()
    if not any(content_type.startswith(prefix) for prefix in _ASSET_MIME_PREFIXES):
        raise HTTPException(status_code=415, detail="Chỉ nhận ảnh, video hoặc audio.")
    data = await file.read(_ASSET_LIMIT + 1)
    if not data or len(data) > _ASSET_LIMIT:
        raise HTTPException(status_code=413, detail="Asset phải từ 1 byte đến 90 MB.")
    suffix = Path(file.filename or "asset").suffix.lower()[:10]
    if content_type.startswith("image/"):
        try:
            from PIL import Image
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
        except Exception:
            raise HTTPException(status_code=422, detail="File ảnh không hợp lệ.") from None
    else:
        from platform_core import media
        temp_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                temp.write(data); temp_path = temp.name
            if media.duration_seconds(temp_path) <= 0:
                raise HTTPException(status_code=422, detail="File media không có thời lượng hợp lệ.")
        finally:
            if temp_path:
                try: os.unlink(temp_path)
                except OSError: pass
    from platform_core.storage import get_storage
    key = f"agent-assets/{user.id}/{uuid.uuid4().hex}{suffix}"
    stored = get_storage().put(key, io.BytesIO(data), content_type=content_type)
    kind = content_type.split("/", 1)[0]
    return {"key": stored.key, "kind": kind, "name": Path(file.filename or "asset").name,
            "size": stored.size, "content_type": content_type,
            "url": f"/agent/api/assets/{Path(stored.key).name}",
            "provenance": {"source": "user_upload", "owner": "current_user"}}


@router.get("/api/assets/{asset_name}")
def workflow_asset_preview(request: Request, asset_name: str,
                           _identity: str = Depends(require_login)):
    """Stream only an asset owned by the current Canvas user."""
    if Path(asset_name).name != asset_name or len(asset_name) > 80:
        raise HTTPException(status_code=404, detail="Không tìm thấy asset.")
    user = _user(request)
    key = f"agent-assets/{user.id}/{asset_name}"
    from platform_core.storage import StorageError, get_storage
    storage = get_storage()
    try:
        direct = storage.url_for(key)
        if direct:
            return RedirectResponse(direct, status_code=307)
        total = storage.size(key)
    except (OSError, StorageError):
        raise HTTPException(status_code=404, detail="Không tìm thấy asset.") from None
    media_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
    range_header = request.headers.get("range", "")
    if range_header.startswith("bytes="):
        try:
            start_text, _, end_text = range_header[6:].partition("-")
            start = int(start_text) if start_text else 0
            end = int(end_text) if end_text else total - 1
        except ValueError:
            start, end = 0, total - 1
        start = max(0, start); end = min(end, total - 1)
        if start > end:
            start, end = 0, total - 1
        stream = storage.open(key)
        try:
            stream.seek(start); chunk = stream.read(end - start + 1)
        finally:
            stream.close()
        return Response(chunk, status_code=206, media_type=media_type, headers={
            "Content-Range": f"bytes {start}-{end}/{total}", "Accept-Ranges": "bytes",
            "Content-Length": str(len(chunk)), "Cache-Control": "private, no-store"})
    return StreamingResponse(storage.open(key), media_type=media_type, headers={
        "Accept-Ranges": "bytes", "Content-Length": str(total),
        "Cache-Control": "private, no-store"})


@router.post("/api/tools/{tool_name}/quote")
async def workflow_tool_quote(request: Request, tool_name: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    """Authoritative non-mutating node quote for the inline composer."""
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    from platform_core import app_access
    loaded = discover()
    allowed = {item.slug for item in loaded
               if app_access.muc_quyen(db, user, item.slug) == app_access.ENABLED}
    tools = discover_tools(apps=loaded, allowed_slugs=allowed)
    spec = tools.get(tool_name)
    if spec is None:
        raise HTTPException(status_code=404, detail="Tool không tồn tại/không có quyền.")
    try:
        params = validate_tool_params(tool_name, body.get("params", {}), apps=loaded)
        fanout = int(body.get("fanout", 1)); retry = int(body.get("max_retry", 0))
        if not 1 <= fanout <= 4 or not 0 <= retry <= 2:
            raise ToolParamsError("fanout/max_retry không hợp lệ")
        unit = credit_for(spec.job_type, params, apps=loaded)
    except (ToolParamsError, RegistryError, ValueError, TypeError) as exc:
        return {"tool": tool_name, "valid": False, "detail": str(exc),
                "maximum": None, "authoritative": True}
    return {"tool": tool_name, "valid": True, "unit": unit, "fanout": fanout,
            "max_retry": retry, "maximum": unit * fanout * (1 + retry),
            "authoritative": True}
