"""Thu vien meta prompt, doan prompt va phong cach."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.routes._shared import (
    _as_int, _csrf, _resource_error, _user, get_db, require_login, router)


# ── Thư viện: meta prompt / đoạn prompt / phong cách (R2) ───────────────────
#
# Một bộ endpoint cho cả ba loại, phân biệt bằng `{kind}` trong đường dẫn. Ba
# bộ giống nhau chỉ khác tên bảng là ba chỗ để quên sửa khi luật đổi — module
# nguồn có ba manager riêng và chúng đã lệch nhau thật.

def _library_error(exc: Exception) -> HTTPException:
    """Giống `_resource_error`: chỉ dịch lỗi của người dùng, còn lại để 500."""
    from apps.prompt_ai_ommi.services import library as lsvc
    if isinstance(exc, lsvc.LibraryNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, lsvc.LibraryError):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc


def _library_json(kind: str, row) -> dict:
    payload = {"id": row.id, "kind": kind, "name": row.name, "body": row.body,
               "is_catalog": row.owner_id is None,
               "cloned_from_id": row.cloned_from_id or "",
               "archived": row.archived_at is not None,
               "updated_at": row.updated_at.isoformat()}
    if kind == "meta":
        payload |= {"purpose": row.purpose, "variables": row.variables or {},
                    "version": row.version}
    elif kind == "snippet":
        payload |= {"category": row.category, "version": row.version}
    elif kind == "style":
        payload |= {"negative": row.negative, "attributes": row.attributes or {}}
    return payload


@router.get("/api/library/{kind}")
def list_library(request: Request, kind: str, q: str = "", catalog: bool = False,
                 archived: bool = False, limit: int = 40, offset: int = 0,
                 _identity: str = Depends(require_login),
                 db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import library as lsvc
    user = _user(request)
    try:
        rows, total = lsvc.list_items(
            db, kind, user.id, catalog=bool(catalog), query=q,
            include_archived=bool(archived),
            limit=_as_int(limit, 40, 1, lsvc.PAGE_MAX),
            offset=_as_int(offset, 0, 0, 1_000_000))
    except Exception as exc:
        raise _library_error(exc) from exc
    return {"items": [_library_json(kind, row) for row in rows], "total": total,
            "catalog": bool(catalog), "counts": lsvc.counts(db, user.id)}


@router.post("/api/library/{kind}", status_code=201)
async def create_library_item(request: Request, kind: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import library as lsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = lsvc.create(db, kind, owner_id=user.id, name=body.get("name", ""),
                          body=body.get("body", ""),
                          purpose=body.get("purpose"),
                          category=body.get("category"),
                          negative=body.get("negative"),
                          variables=body.get("variables"),
                          attributes=body.get("attributes"))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _library_error(exc) from exc
    return _library_json(kind, row)


@router.get("/api/library/{kind}/{item_id}")
def get_library_item(request: Request, kind: str, item_id: str,
                     _identity: str = Depends(require_login),
                     db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import library as lsvc
    user = _user(request)
    try:
        row = lsvc.get_visible(db, kind, item_id, user.id)
        payload = _library_json(kind, row)
        # Lịch sử chỉ có với bản riêng; mẫu catalog không thuộc về ai để mà có.
        payload["versions"] = ([] if row.owner_id is None else
                               [{"version": v.version, "note": v.note,
                                 "created_at": v.created_at.isoformat()}
                                for v in lsvc.versions(db, kind, item_id, user.id)])
    except Exception as exc:
        raise _library_error(exc) from exc
    return payload


@router.put("/api/library/{kind}/{item_id}")
async def update_library_item(request: Request, kind: str, item_id: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import library as lsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    fields = {key: body[key] for key in
              ("name", "body", "purpose", "category", "negative", "variables",
               "attributes", "note") if key in body}
    try:
        row = lsvc.update(db, kind, item_id=item_id, owner_id=user.id, **fields)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _library_error(exc) from exc
    return _library_json(kind, row)


@router.post("/api/library/{kind}/{item_id}/archive")
async def archive_library_item(request: Request, kind: str, item_id: str,
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import library as lsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = lsvc.archive(db, kind, item_id=item_id, owner_id=user.id,
                           archived=bool(body.get("archived", True)))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _library_error(exc) from exc
    return _library_json(kind, row)


@router.post("/api/library/{kind}/{item_id}/clone", status_code=201)
async def clone_library_item(request: Request, kind: str, item_id: str,
                             _identity: str = Depends(require_login),
                             db: Session = Depends(get_db)):
    """"Dùng mẫu này" — chỉ áp dụng cho mẫu catalog."""
    from apps.prompt_ai_ommi.services import library as lsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = lsvc.clone_from_catalog(db, kind, item_id=item_id, owner_id=user.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _library_error(exc) from exc
    return _library_json(kind, row)


@router.post("/api/library/{kind}/{item_id}/publish", status_code=201)
async def publish_library_item(request: Request, kind: str, item_id: str,
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    """Đưa một mục thành mẫu catalog. Quyền admin lấy từ CSDL, không từ body."""
    from apps.prompt_ai_ommi.services import library as lsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    if getattr(user, "role", "") != "admin":
        raise HTTPException(status_code=403,
                            detail="Chỉ admin được publish mẫu vào catalog.")
    try:
        row = lsvc.publish_to_catalog(db, kind, item_id=item_id,
                                      owner_id=user.id, is_admin=True)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _library_error(exc) from exc
    return _library_json(kind, row)


@router.post("/api/library/{kind}/{item_id}/deprecate")
async def deprecate_library_item(request: Request, kind: str, item_id: str,
                                 _identity: str = Depends(require_login),
                                 db: Session = Depends(get_db)):
    """Ngừng chào mời một mẫu catalog (H19.6). CHỈ admin.

    KHÔNG chạm tới bản riêng của những người đã clone — họ vẫn đang dùng nó để
    làm việc.
    """
    from apps.prompt_ai_ommi.services import library as lsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    if getattr(user, "role", "") != "admin":
        raise HTTPException(status_code=403,
                            detail="Chỉ admin được ngừng dùng mẫu catalog.")
    try:
        row = lsvc.deprecate(db, kind, item_id=item_id, is_admin=True,
                             note=str(body.get("note") or ""),
                             deprecated=bool(body.get("deprecated", True)))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _library_error(exc) from exc
    return _library_json(kind, row)


@router.get("/api/library/{kind}/deprecated-sources")
def library_deprecated_sources(request: Request, kind: str,
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    """Bản riêng của tôi mà MẪU GỐC đã ngừng dùng.

    Không có phép tra này thì người dùng chỉ phát hiện ra khi kết quả tệ đi.
    """
    from apps.prompt_ai_ommi.services import library as lsvc
    user = _user(request)
    try:
        return {"items": lsvc.deprecated_sources(db, kind, user.id)}
    except Exception as exc:
        raise _library_error(exc) from exc
