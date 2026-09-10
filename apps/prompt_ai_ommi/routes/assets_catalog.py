"""Tai san tai len, xuat/nhap du an, va catalog mau."""
from __future__ import annotations

from platform_core.i18n import _ as _t
from platform_core.llm import canonical as _C
import io
import json
import uuid
import zipfile

from pathlib import Path, PurePath

from fastapi import Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.routes._shared import (
    _csrf, _owned_production, _row, _user, _ASSET_CAP, router, MANIFEST, require_login, get_db, SCHEMA_VERSION, clean_project, load_catalog)


@router.get("/api/admin/health")
def admin_health(request: Request, _identity: str = Depends(require_login),
                 db: Session = Depends(get_db)):
    user = _user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail=_t('Chỉ admin được xem vận hành.'))
    from sqlalchemy import func
    from platform_core.models import AppProject, Job
    projects = db.execute(select(func.count()).select_from(AppProject).where(
        AppProject.app_slug == MANIFEST.slug)).scalar_one()
    statuses = dict(db.execute(select(Job.status, func.count()).where(
        Job.app_slug == MANIFEST.slug).group_by(Job.status)).all())
    return {"app_slug": MANIFEST.slug, "projects": int(projects),
            "jobs": {str(key): int(value) for key, value in statuses.items()},
            # 🔴 Pha 09: app chạy LTT_LLM/LTT_IMAGE từ pha 05.5. Trường này
            #    là thứ khách ĐỌC ĐƯỢC, nên gõ cứng tên một nhà cung cấp đã
            #    ngừng là khai sai với họ. Đọc từ `canonical` để nó không
            #    thể trôi khỏi sự thật một lần nữa.
            "provider": _C.THU_TU_PROVIDER[0],
            "secret_values_exposed": False}


@router.post("/api/assets", status_code=201)
async def upload_asset(request: Request, file: UploadFile = File(...),
                       kind: str = Form("image"), name: str = Form(""),
                       description: str = Form(""),
                       _identity: str = Depends(require_login)):
    _csrf(request); user = _user(request)
    content_type = str(file.content_type or "").lower()
    detected = "image" if content_type.startswith("image/") else (
        "video" if content_type.startswith("video/") else (
            "audio" if content_type.startswith("audio/") else ""))
    if not detected:
        raise HTTPException(status_code=415, detail=_t('Chỉ nhận ảnh, video hoặc audio.'))
    data = await file.read(_ASSET_CAP[detected] + 1)
    if not data or len(data) > _ASSET_CAP[detected]:
        raise HTTPException(status_code=413, detail=_t('File rỗng hoặc vượt giới hạn.'))
    if detected == "image":
        try:
            from PIL import Image
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
        except Exception:
            raise HTTPException(status_code=422, detail=_t('File ảnh không hợp lệ.')) from None
    safe_name = PurePath(str(file.filename or "asset").replace("\\", "/")).name[:120]
    suffix = Path(safe_name).suffix.lower()[:10]
    key = f"prompt_ai_ommi/{user.id}/assets/{uuid.uuid4().hex}{suffix}"
    from platform_core.storage import get_storage
    stored = get_storage().put(key, io.BytesIO(data), content_type=content_type)
    return {"id": f"res_{uuid.uuid4().hex[:12]}",
            "kind": kind if kind in {"character", "location", "prop", "style"} else detected,
            "name": str(name or safe_name)[:120], "description": str(description)[:1200],
            "storage_key": stored.key, "content_type": content_type, "size": stored.size}


@router.get("/api/projects/{project_id}/export/{fmt}")
def export_project(request: Request, project_id: str, fmt: str,
                   _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    user = _user(request); row = _owned_production(db, project_id, user.id)
    payload = clean_project(row.payload)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in row.name)[:80] or "prompt-ai-ommi"
    if fmt == "json":
        data = json.dumps({"format": "ltt-prompt-ai-ommi", "version": 1,
                           "name": row.name, "project": payload}, ensure_ascii=False,
                          indent=2).encode("utf-8")
        return Response(data, media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{safe}.json"'})
    lines = [f"# {payload['brief']['title']}", "", payload["brief"]["story"], ""]
    for scene in payload["scenes"]:
        lines += [f"## {scene['order'] + 1}. {scene['title']}", "",
                  scene["summary"], "", "### Prompt", "", scene["prompt"], "",
                  "### Negative prompt", "", scene["negative_prompt"], ""]
    markdown = "\n".join(lines).encode("utf-8")
    if fmt == "md":
        return Response(markdown, media_type="text/markdown; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{safe}.md"'})
    if fmt == "zip":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(f"{safe}.md", markdown)
            archive.writestr(f"{safe}.json", json.dumps(
                {"format": "ltt-prompt-ai-ommi", "version": 1, "name": row.name,
                 "project": payload}, ensure_ascii=False, indent=2))
        return Response(buf.getvalue(), media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{safe}.zip"'})
    raise HTTPException(status_code=404, detail=_t('Định dạng export không hỗ trợ.'))


@router.post("/api/import", status_code=201)
async def import_project(request: Request, _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if len(raw) > 900_000:
        raise HTTPException(status_code=413, detail=_t('Package vượt giới hạn 900 KiB.'))
    if body.get("format") != "ltt-prompt-ai-ommi" or body.get("version") != 1:
        raise HTTPException(status_code=422, detail=_t('Package không đúng định dạng.'))
    payload = clean_project(body.get("project") or {})
    # Không nhập storage key từ package khác: asset binary phải upload lại.
    for item in payload["resources"]:
        item["storage_key"] = ""; item["size"] = 0; item["content_type"] = ""
    from platform_core import app_projects
    row = app_projects.create(db, user_id=user.id, app_slug=MANIFEST.slug,
                              name=str(body.get("name") or payload["brief"]["title"])[:160],
                              schema_version=SCHEMA_VERSION, payload=payload)
    return _row(row)


@router.get("/api/catalog")
def catalog(request: Request, _identity: str = Depends(require_login),
            db: Session = Depends(get_db)):
    from platform_core.models import APP_PROJECT_ACTIVE, AppProject
    rows = db.execute(select(AppProject).where(
        AppProject.app_slug == MANIFEST.slug, AppProject.status == APP_PROJECT_ACTIVE
    ).order_by(AppProject.updated_at.desc()).limit(100)).scalars().all()
    published = [{"id": row.id, "name": row.name,
                  "item": (row.payload or {}).get("item", {})}
                 for row in rows if (row.payload or {}).get("kind") == "published_catalog" and
                 (row.payload or {}).get("published") is True]
    return {"built_in": load_catalog(), "published": published}


@router.post("/api/admin/catalog", status_code=201)
async def admin_catalog(request: Request, _identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    body = await request.json(); _csrf(request, body); user = _user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail=_t('Chỉ admin được publish catalog.'))
    item = body.get("item") if isinstance(body.get("item"), dict) else {}
    payload = {"kind": "published_catalog", "version": 1, "published": True,
               "item": {"type": str(item.get("type") or "template")[:40],
                        "label": str(item.get("label") or "Mẫu LTT")[:120],
                        "description": str(item.get("description") or "")[:1000],
                        "content": str(item.get("content") or "")[:12000],
                        "provenance": str(item.get("provenance") or "LTT")[:300]}}
    from platform_core import app_projects
    row = app_projects.create(db, user_id=user.id, app_slug=MANIFEST.slug,
                              name=payload["item"]["label"], schema_version=1,
                              payload=payload)
    return _row(row)
