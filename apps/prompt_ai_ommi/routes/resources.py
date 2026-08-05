"""Kho tai nguyen rieng cua tung nguoi dung, ke ca anh va sinh anh."""
from __future__ import annotations

import io
import os
import uuid

from fastapi import Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.routes._shared import (
    MANIFEST, _IMAGE_JOB_TYPE, _as_int, _csrf, _require_run_enabled,
    _resource_error, _user, get_db, require_login, router)


# ── Kho tài nguyên (R1) ─────────────────────────────────────────────────────
#
# Mọi handler dưới đây nhận `owner_id` từ PHIÊN ĐĂNG NHẬP, không bao giờ từ
# body hay query. Cho client gửi owner_id lên là trao luôn chìa khoá đọc dữ
# liệu người khác.
#
# Service ném `ResourceNotFound` cho cả "không có" lẫn "không phải của bạn";
# ở đây cả hai thành 404 giống hệt nhau.

def _resource_json(row, *, cover_key: str = "") -> dict:
    return {"id": row.id, "kind": row.kind, "name": row.name,
            "description": row.description, "prompt_text": row.prompt_text,
            "attributes": row.attributes or {},
            "cover_variant_id": row.cover_variant_id or "",
            "cover_key": cover_key,
            "is_catalog": row.owner_id is None,
            "archived": row.archived_at is not None,
            "updated_at": row.updated_at.isoformat()}


def _variant_json(row) -> dict:
    return {"id": row.id, "label": row.label, "storage_key": row.storage_key,
            "thumb_key": row.thumb_key, "width": row.width,
            "height": row.height, "bytes_size": row.bytes_size,
            "position": row.position}




@router.get("/api/resources")
def list_resources(request: Request, kind: str = "", q: str = "",
                   catalog: bool = False, archived: bool = False,
                   limit: int = 40, offset: int = 0,
                   _identity: str = Depends(require_login),
                   db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    user = _user(request)
    try:
        rows, total = rsvc.list_resources(
            db, user.id, kind=kind, query=q, include_catalog=bool(catalog),
            include_archived=bool(archived),
            limit=_as_int(limit, 40, 1, rsvc.PAGE_MAX),
            offset=_as_int(offset, 0, 0, 1_000_000))
    except Exception as exc:
        raise _resource_error(exc) from exc
    return {"items": [_resource_json(row) for row in rows], "total": total,
            "limit": _as_int(limit, 40, 1, rsvc.PAGE_MAX),
            "offset": _as_int(offset, 0, 0, 1_000_000),
            "counts": rsvc.count_by_kind(db, user.id),
            "kinds": list(rsvc.RESOURCE_KINDS)}


@router.post("/api/resources", status_code=201)
async def create_resource(request: Request, _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = rsvc.create(db, owner_id=user.id, kind=body.get("kind", ""),
                          name=body.get("name", ""),
                          description=body.get("description", ""),
                          prompt_text=body.get("prompt_text", ""),
                          attributes=body.get("attributes"))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return _resource_json(row)


@router.get("/api/resources/{resource_id}")
def get_resource(request: Request, resource_id: str,
                 _identity: str = Depends(require_login),
                 db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    user = _user(request)
    try:
        row = rsvc.get_visible(db, resource_id, user.id)
        payload = _resource_json(row)
        payload["variants"] = [_variant_json(v)
                               for v in rsvc.variants(db, resource_id, user.id)]
        payload["tags"] = [t.name for t in rsvc.tags_of(db, resource_id, user.id)]
    except Exception as exc:
        raise _resource_error(exc) from exc
    return payload


@router.put("/api/resources/{resource_id}")
async def update_resource(request: Request, resource_id: str,
                          _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    fields = {key: body[key] for key in
              ("name", "kind", "description", "prompt_text", "attributes")
              if key in body}
    try:
        row = rsvc.update(db, resource_id=resource_id, owner_id=user.id, **fields)
        if isinstance(body.get("tags"), list):
            rsvc.set_tags(db, resource_id=resource_id, owner_id=user.id,
                          names=body["tags"])
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return _resource_json(row)


@router.post("/api/resources/{resource_id}/archive")
async def archive_resource(request: Request, resource_id: str,
                           _identity: str = Depends(require_login),
                           db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = rsvc.archive(db, resource_id=resource_id, owner_id=user.id,
                           archived=bool(body.get("archived", True)))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return _resource_json(row)


@router.post("/api/resources/{resource_id}/clone", status_code=201)
async def clone_resource(request: Request, resource_id: str,
                         _identity: str = Depends(require_login),
                         db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        row = rsvc.clone_from_catalog(db, resource_id=resource_id, owner_id=user.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return _resource_json(row)


@router.get("/api/resources/{resource_id}/usage")
def resource_usage(request: Request, resource_id: str,
                   _identity: str = Depends(require_login),
                   db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    user = _user(request)
    try:
        rows = rsvc.usage(db, resource_id, user.id)
    except Exception as exc:
        raise _resource_error(exc) from exc
    return {"items": [{"project_id": r.project_id, "scene_ref": r.scene_ref}
                      for r in rows], "total": len(rows)}


# ── Ảnh của tài nguyên (R1.3) ──────────────────────────────────────────────
#
# Hai đường, cùng một kết quả:
#   1. Có R2 và CORS đã bật  -> trả vé presigned, trình duyệt PUT THẲNG lên R2.
#      Ảnh không đi qua tunnel nên không đụng trần 100 MB của Cloudflare.
#   2. Chưa có               -> nhận multipart qua route, giới hạn nhỏ hơn.
#
# Dù đi đường nào, `confirm` mới là chỗ ghi vào CSDL, và nó luôn kiểm quyền sở
# hữu tài nguyên trước. Không có đường nào ghi ảnh vào tài nguyên người khác.

_RESOURCE_IMAGE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg",
                         "image/webp": ".webp"}
_RESOURCE_IMAGE_CAP = 20 * 1024 * 1024


def _browser_direct_upload_enabled() -> bool:
    """Presigned PUT chỉ chạy sau khi luật CORS của bucket đã được kiểm.

    Mặc định tắt để không tạo ra một lỗi CORS chắc chắn rồi mới rơi về
    multipart — người dùng thấy lỗi đỏ trước khi thấy nó tự chữa.
    """
    return os.environ.get("LTT_R2_BROWSER_UPLOAD_ENABLED", "").strip() == "1"


def _image_key(user_id: str, resource_id: str, content_type: str):
    """Khoá lưu trữ, giữ NGẮN có chủ đích.

    Windows giới hạn đường dẫn 260 ký tự và `LocalStorage` còn thêm hậu tố
    `.part<pid>` khi ghi. Bản đầu dùng
    `prompt_ai_ommi/{uuid}/resources/{uuid}/{32 hex}` ≈ 145 ký tự và đã vỡ thật
    khi thư mục gốc dài — `FileNotFoundError` chứ không phải lỗi nói rõ là quá
    dài, nên rất khó đoán. Production hiện có gốc ngắn nên chưa vỡ; đó là may,
    không phải thiết kế.

    Vẫn giữ ĐỦ `user_id` và `resource_id` vì `confirm` dựa vào tiền tố này để
    buộc khoá thuộc đúng người gọi và đúng tài nguyên.
    """
    ct = (content_type or "").split(";")[0].strip().lower()
    ext = _RESOURCE_IMAGE_TYPES.get(ct)
    if ext is None:
        raise HTTPException(status_code=400,
                            detail="Chỉ nhận ảnh PNG, JPEG hoặc WebP.")
    return f"ommi/{user_id}/{resource_id}/{uuid.uuid4().hex[:16]}{ext}", ct


@router.post("/api/resources/{resource_id}/images/ticket")
async def resource_image_ticket(request: Request, resource_id: str,
                                _identity: str = Depends(require_login),
                                db: Session = Depends(get_db)):
    """Xin chỗ để tải ảnh lên. Kiểm quyền TRƯỚC khi cấp vé."""
    from apps.prompt_ai_ommi.services import resources as rsvc
    from platform_core.storage import get_storage
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        rsvc.get_owned(db, resource_id, user.id)
    except Exception as exc:
        raise _resource_error(exc) from exc

    key, ct = _image_key(user.id, resource_id, body.get("content_type", ""))
    target = None
    if _browser_direct_upload_enabled():
        try:
            target = get_storage().put_url(key, ttl_s=3600, content_type=ct)
        except Exception:  # noqa: BLE001
            target = None
    if target is None:
        return {"mode": "local", "key": key, "max_bytes": _RESOURCE_IMAGE_CAP}
    return {"mode": "direct", "key": target.key, "url": target.url,
            "method": target.method, "headers": target.headers or {}}


@router.post("/api/resources/{resource_id}/images", status_code=201)
async def upload_resource_image(request: Request, resource_id: str,
                                file: UploadFile = File(...),
                                csrf_token: str = Form(""),
                                label: str = Form(""),
                                _identity: str = Depends(require_login),
                                db: Session = Depends(get_db)):
    """Đường dự phòng: nhận multipart khi chưa bật upload thẳng lên R2."""
    from apps.prompt_ai_ommi.services import resources as rsvc
    from platform_core.storage import get_storage
    _csrf(request, {"csrf_token": csrf_token}); user = _user(request)
    try:
        rsvc.get_owned(db, resource_id, user.id)
    except Exception as exc:
        raise _resource_error(exc) from exc

    key, ct = _image_key(user.id, resource_id, file.content_type or "")
    data = await file.read(_RESOURCE_IMAGE_CAP + 1)
    if len(data) > _RESOURCE_IMAGE_CAP:
        raise HTTPException(status_code=413, detail="Ảnh vượt 20 MB.")
    if not data:
        raise HTTPException(status_code=400, detail="File rỗng.")
    get_storage().put(key, io.BytesIO(data), content_type=ct)
    try:
        row = rsvc.add_variant(db, resource_id=resource_id, owner_id=user.id,
                               storage_key=key, label=label,
                               bytes_size=len(data))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return _variant_json(row)


@router.post("/api/resources/{resource_id}/images/confirm", status_code=201)
async def confirm_resource_image(request: Request, resource_id: str,
                                 _identity: str = Depends(require_login),
                                 db: Session = Depends(get_db)):
    """Ghi nhận ảnh đã PUT thẳng lên storage.

    Kiểm ba việc trước khi ghi: tài nguyên là của người gọi, khoá nằm ĐÚNG
    trong thư mục của người gọi, và file có thật trên storage. Thiếu kiểm thứ
    hai thì client gửi khoá của người khác là gắn được ảnh người ta vào tài
    nguyên của mình.
    """
    from apps.prompt_ai_ommi.services import resources as rsvc
    from platform_core.storage import get_storage
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        rsvc.get_owned(db, resource_id, user.id)
    except Exception as exc:
        raise _resource_error(exc) from exc

    key = str(body.get("key") or "").strip()
    prefix = f"ommi/{user.id}/{resource_id}/"
    if not key.startswith(prefix):
        raise HTTPException(status_code=400, detail="Khoá lưu trữ không hợp lệ.")
    storage = get_storage()
    if not storage.exists(key):
        raise HTTPException(status_code=400, detail="Chưa thấy file trên kho lưu trữ.")
    try:
        row = rsvc.add_variant(db, resource_id=resource_id, owner_id=user.id,
                               storage_key=key, label=str(body.get("label") or ""),
                               width=_as_int(body.get("width"), 0, 0, 20000),
                               height=_as_int(body.get("height"), 0, 0, 20000),
                               bytes_size=storage.size(key))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return _variant_json(row)


@router.delete("/api/resources/{resource_id}/images/{variant_id}")
async def delete_resource_image(request: Request, resource_id: str,
                                variant_id: str,
                                _identity: str = Depends(require_login),
                                db: Session = Depends(get_db)):
    from apps.prompt_ai_ommi.services import resources as rsvc
    _csrf(request); user = _user(request)
    try:
        rsvc.remove_variant(db, variant_id=variant_id, owner_id=user.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return {"ok": True}


@router.get("/api/resources/{resource_id}/images/{variant_id}/url")
def resource_image_url(request: Request, resource_id: str, variant_id: str,
                       _identity: str = Depends(require_login),
                       db: Session = Depends(get_db)):
    """URL xem ảnh.

    KHÔNG dùng `storage.download_token`: token nằm trong RAM của TỪNG tiến
    trình, mà worker (tạo ảnh) và web (phục vụ ảnh) là hai tiến trình khác nhau
    — token cấp ở đây tiến trình kia không biết. Bản đầu trả token và ảnh 404
    trên browser đúng vì lý do đó. App tự phục vụ file qua `/f/{key}` và kiểm
    sở hữu theo khoá, giống các app ảnh khác.
    """
    from apps.prompt_ai_ommi.services import resources as rsvc
    user = _user(request)
    try:
        found = [v for v in rsvc.variants(db, resource_id, user.id)
                 if v.id == variant_id]
    except Exception as exc:
        raise _resource_error(exc) from exc
    if not found:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh.")
    return {"url": f"{MANIFEST.route_prefix}/f/{found[0].storage_key}"}


@router.get("/f/{key:path}")
def resource_image_file(request: Request, key: str,
                        _identity: str = Depends(require_login)):
    """Phục vụ ảnh tài nguyên, kiểm sở hữu NGAY TRÊN KHOÁ.

    Khoá có dạng `ommi/{owner_id}/{resource_id}/...`, nên chỉ cần so đoạn thứ
    hai với người đang đăng nhập là đủ chặn đọc chéo — không phải tra CSDL.
    Ảnh do `taoanh.generate` sinh nằm ngoài tiền tố này và được phục vụ bởi
    chính app Tạo ảnh.
    """
    from fastapi.responses import RedirectResponse, StreamingResponse
    from platform_core.storage import StorageError, get_storage
    user = _user(request)
    segments = key.split("/")
    if len(segments) < 3 or segments[0] != "ommi" or segments[1] != user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh.")
    storage = get_storage()
    try:
        direct = storage.url_for(key)
    except Exception:  # noqa: BLE001
        direct = None
    if direct:
        return RedirectResponse(direct, status_code=302)
    try:
        stream = storage.open(key)
    except (StorageError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh.") from None
    kind = "image/png" if key.endswith(".png") else (
        "image/webp" if key.endswith(".webp") else "image/jpeg")
    return StreamingResponse(stream, media_type=kind)


# ── Sinh ảnh cho tài nguyên (R1.5) ─────────────────────────────────────────
#
# OMMI sở hữu ĐIỀU PHỐI và trải nghiệm; lời gọi provider dùng lại job
# `taoanh.generate` của app Tạo ảnh. Người dùng không rời OMMI.
#
# Vì sao không dựng engine riêng: phần có giá trị trong `image_gen` của module
# nguồn (3.269 dòng) là sinh hàng loạt theo cảnh, chèn ảnh tham chiếu để giữ
# nhất quán nhân vật, và phiên bản theo cảnh — tất cả nằm TRÊN lời gọi provider,
# không phải bên trong nó. `image.generate` đã nhận `image_keys`, tức cơ chế
# nhất quán đã có sẵn. Dựng engine thứ hai chỉ nhân đôi tích hợp provider, xoay
# khoá, retry và bảng giá.
#
# Cơ chế cho phép điều này, đã kiểm: worker phân việc theo `job_type` chứ không
# theo `app_slug` (`platform_core/jobs.py`), và giá tra theo `job_type`
# (`platform_core/job_submit.py`). Nên OMMI nộp `taoanh.generate` là hợp lệ và
# tính đúng giá của Tạo ảnh.



def _reference_keys(db, *, resource_id: str, owner_id: str,
                    variant_ids: list) -> list:
    """Ảnh tham chiếu để giữ nhất quán nhân vật giữa các lần sinh.

    Chỉ chọn trong ảnh CỦA CHÍNH tài nguyên này. Client gửi ID lạ — của người
    khác hay của tài nguyên khác — thì ID đó rơi ra, không có đường nào ép
    provider đọc ảnh riêng tư của người khác.

    Phép so `owner_id` bên dưới là phòng thủ lớp hai chứ không phải lớp chính:
    `variants()` đã lọc qua tài nguyên, và caller luôn gọi `get_owned` trước.
    Nó chỉ có tác dụng nếu sau này có ai cho phép tham chiếu ảnh của mẫu
    catalog (owner NULL) — giữ lại để lúc đó không phải nhớ ra.
    """
    from apps.prompt_ai_ommi.services import resources as rsvc
    wanted = {str(v) for v in (variant_ids or [])[:4] if v}
    if not wanted:
        return []
    keys = []
    for variant in rsvc.variants(db, resource_id, owner_id):
        if variant.id in wanted and variant.owner_id == owner_id:
            keys.append(variant.storage_key)
    return keys


def _image_params(request_body: dict, *, resource, owner_id: str,
                  reference_keys: list) -> dict:
    prompt = str(request_body.get("prompt") or resource.prompt_text
                 or resource.description or resource.name).strip()
    if len(prompt) < 8:
        raise HTTPException(status_code=422,
                            detail="Mô tả ảnh quá ngắn — tối thiểu 8 ký tự.")
    params = {
        "prompt": prompt[:4000],
        "aspect_ratio": str(request_body.get("aspect_ratio") or "1:1"),
        "count": _as_int(request_body.get("count"), 1, 1, 4),
        "owner_id": owner_id,
    }
    model = str(request_body.get("model") or "").strip()
    if model:
        params["model"] = model
    if reference_keys:
        params["image_keys"] = reference_keys
    return params


@router.post("/api/resources/{resource_id}/images/generate")
async def generate_resource_image(request: Request, resource_id: str,
                                  _identity: str = Depends(require_login),
                                  db: Session = Depends(get_db)):
    """Báo giá, rồi chạy khi `confirmed` là true.

    Một endpoint làm hai việc để giá người dùng thấy và giá bị trừ được tính
    bằng ĐÚNG một đoạn mã. Tách đôi là mở đường cho hai công thức lệch nhau.
    """
    from apps.prompt_ai_ommi.services import resources as rsvc
    from platform_core.registry import credit_for
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        resource = rsvc.get_owned(db, resource_id, user.id)
        refs = _reference_keys(db, resource_id=resource_id, owner_id=user.id,
                               variant_ids=body.get("reference_variant_ids") or [])
    except HTTPException:
        raise
    except Exception as exc:
        raise _resource_error(exc) from exc

    params = _image_params(body, resource=resource, owner_id=user.id,
                           reference_keys=refs)
    estimate = int(credit_for(_IMAGE_JOB_TYPE, params))
    if not body.get("confirmed"):
        return {"credit": estimate, "count": params["count"],
                "reference_count": len(refs), "authoritative": True,
                "confirmed": False}

    _require_run_enabled(user)
    from platform_core import credit
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError
    try:
        job = submit_with_credit(
            db, user_id=user.id, app_slug=MANIFEST.slug,
            job_type=_IMAGE_JOB_TYPE, params=params,
            dedupe_key=dedupe_key_for(_IMAGE_JOB_TYPE, params))
        db.commit()
    except (credit.ThieuCreditError, RegistryError) as exc:
        db.rollback()
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    return {"id": job.id, "status": job.status, "credit": estimate,
            "resource_id": resource_id, "job_url": f"/jobs/{job.id}"}


@router.post("/api/resources/{resource_id}/images/from-job", status_code=201)
async def attach_generated_images(request: Request, resource_id: str,
                                  _identity: str = Depends(require_login),
                                  db: Session = Depends(get_db)):
    """Gắn ảnh một job đã sinh vào tài nguyên.

    Quyền ở đây suy từ CHÍNH job (`job.user_id`), không suy từ tiền tố khoá như
    `confirm`: ảnh do `taoanh.generate` sinh nằm trong namespace của app Tạo
    ảnh, không nằm trong thư mục OMMI của người dùng. Hai đường kiểm khác nhau
    vì nguồn tin cậy khác nhau — nới lỏng luật tiền tố của `confirm` để dùng
    chung sẽ mở đúng lỗ hổng mà luật đó đang bịt.
    """
    from apps.prompt_ai_ommi.services import resources as rsvc
    from platform_core.models import JOB_DONE, Job
    body = await request.json(); _csrf(request, body); user = _user(request)
    try:
        rsvc.get_owned(db, resource_id, user.id)
    except Exception as exc:
        raise _resource_error(exc) from exc

    job = db.get(Job, str(body.get("job_id") or ""))
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy job.")
    if job.status != JOB_DONE:
        raise HTTPException(status_code=409, detail="Job chưa chạy xong.")
    if job.job_type != _IMAGE_JOB_TYPE:
        raise HTTPException(status_code=400, detail="Job này không sinh ảnh.")

    keys = [k for k in ((job.result or {}).get("image_keys") or []) if k][:4]
    if not keys:
        raise HTTPException(status_code=400, detail="Job không trả về ảnh nào.")

    made = []
    try:
        for index, key in enumerate(keys):
            made.append(rsvc.add_variant(
                db, resource_id=resource_id, owner_id=user.id, storage_key=key,
                label=str(body.get("label") or f"AI {index + 1}")))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _resource_error(exc) from exc
    return {"variants": [_variant_json(row) for row in made]}
