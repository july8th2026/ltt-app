"""Owner-scoped source attachment lifecycle for AutoSub Studio projects."""
from __future__ import annotations

from pathlib import PurePath

from apps.autosubvideo.schemas import StudioProjectV1
from platform_core import app_projects, upload_sessions
from platform_core.i18n import _ as _t
from platform_core.models import UPLOAD_ATTACHED


def create_ticket(db, storage, *, user_id: str, app_slug: str, filename: str,
                  content_type: str, expected_size, direct_enabled: bool,
                  max_size: int, local_max: int,
                  allowed_types: tuple[str, ...]) -> dict:
    try:
        size = int(expected_size)
    except (TypeError, ValueError) as exc:
        raise upload_sessions.UploadSessionError(
            _t("Kích thước file không hợp lệ.")) from exc
    if not direct_enabled:
        if size <= 0 or size > max_size:
            raise upload_sessions.UploadSessionError(
                _t("Kích thước file vượt giới hạn."))
        if size > local_max:
            raise upload_sessions.UploadSessionError(
                _t("Video trên 90MB cần bật upload trực tiếp R2."))
        normalized = content_type.split(";", 1)[0].strip().lower()
        if normalized not in allowed_types:
            raise upload_sessions.UploadSessionError(
                _t("Loại file không được hỗ trợ."))
        return {"mode": "local"}
    session = upload_sessions.create(
        db, user_id=user_id, app_slug=app_slug, filename=filename,
        content_type=content_type, expected_size=size,
        max_size=max_size, allowed_types=allowed_types)
    target = upload_sessions.upload_target(storage, session)
    if target is None:
        db.delete(session); db.flush()
        return {"mode": "local"}
    return {"mode": "direct", "upload_id": session.id, "url": target.url,
            "method": target.method, "headers": target.headers or {}}


def refresh(db, storage, row, *, user_id: str, app_slug: str):
    """Refresh attachment TTL or clear a missing attachment from the project."""
    source = (row.payload or {}).get("source") or {}
    key = str(source.get("key", ""))
    attachment = upload_sessions.project_attachment(
        db, user_id=user_id, app_slug=app_slug,
        project_id=row.id, final_key=key) if key else None
    if attachment is not None and (attachment.status != UPLOAD_ATTACHED or
                                   not storage.exists(key)):
        payload = dict(row.payload); payload["source"] = {
            "key": "", "filename": "", "duration_s": 0,
            "width": 0, "height": 0}
        validated = StudioProjectV1.model_validate(payload).model_dump(mode="json")
        saved = app_projects.save(
            db, project_id=row.id, user_id=user_id, app_slug=app_slug,
            revision=row.revision, name=row.name, schema_version=1,
            payload=validated)
        return saved, True
    if attachment is not None:
        upload_sessions.touch_project_attachment(db, attachment)
    return row, False


def attach(db, storage, *, project_id: str, user_id: str, app_slug: str,
           revision: int, upload_id: str, video_name: str,
           video_content_type: str, video_data: bytes | None, filename: str,
           duration_s: float, width: int, height: int, local_max: int,
           allowed_types: tuple[str, ...]):
    """Validate, move and persist a draft source with storage compensation."""
    promotion = None
    try:
        row = app_projects.get_owned(db, project_id, user_id, app_slug)
        if row.revision != revision:
            raise app_projects.ProjectConflict(
                _t("Project đã được sửa ở phiên khác."))
        if upload_id.strip():
            session = upload_sessions.owned(
                db, session_id=upload_id.strip(), user_id=user_id,
                app_slug=app_slug)
            if session is None:
                raise upload_sessions.UploadSessionError(
                    _t("Vé upload không tồn tại hoặc không thuộc user."))
        else:
            if not video_name or not video_data:
                raise upload_sessions.UploadSessionError(_t("Chưa chọn video."))
            if len(video_data) > local_max:
                raise upload_sessions.UploadSessionError(
                    _t("Video local rỗng hoặc quá 90MB."))
            session = upload_sessions.stage_bytes(
                db, storage, user_id=user_id, app_slug=app_slug,
                filename=video_name, content_type=video_content_type or "video/mp4",
                data=video_data, max_size=local_max, allowed_types=allowed_types)
        ext = PurePath(session.filename).suffix.lower()[:12] or ".mp4"
        key = f"{app_slug}/{user_id}/drafts/{row.id}/{session.id}{ext}"
        upload_sessions.attach_to_project(
            db, storage, session, project_id=row.id, final_key=key)
        promotion = (session.staging_key, key, session.content_type)
        payload = dict(row.payload)
        payload["source"] = {
            "key": key, "filename": (filename or session.filename)[:255],
            "duration_s": max(0, min(float(duration_s), 86400)),
            "width": max(0, min(int(width), 16384)),
            "height": max(0, min(int(height), 16384)),
        }
        payload["active_step"] = "transcript"
        validated = StudioProjectV1.model_validate(payload).model_dump(mode="json")
        saved = app_projects.save(
            db, project_id=project_id, user_id=user_id, app_slug=app_slug,
            revision=revision, name=row.name, schema_version=1,
            payload=validated)
        db.commit()
        return saved
    except Exception:
        db.rollback()
        if promotion:
            upload_sessions.compensate(storage, [promotion])
        raise
