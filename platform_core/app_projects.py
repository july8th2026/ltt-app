"""Generic AppProject lifecycle with ownership and optimistic concurrency."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from platform_core.models import (APP_PROJECT_ACTIVE, APP_PROJECT_ARCHIVED,
                                  AppProject)

MAX_PROJECT_BYTES = 1_048_576
MAX_PROJECT_DEPTH = 32
_FORBIDDEN = {"credential", "credentials", "secret", "token", "password",
              "csrf_token", "api_key", "private_key"}


class ProjectError(ValueError):
    pass


class ProjectConflict(ProjectError):
    pass


class ProjectNotFound(ProjectError):
    pass


def _depth(value) -> int:
    if isinstance(value, dict):
        return 1 + max((_depth(item) for item in value.values()), default=0)
    if isinstance(value, list):
        return 1 + max((_depth(item) for item in value), default=0)
    return 0


def _contains_forbidden(value) -> bool:
    if isinstance(value, dict):
        return any(str(key).lower() in _FORBIDDEN or _contains_forbidden(item)
                   for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_forbidden(item) for item in value)
    return False


def validate_container_payload(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ProjectError("Project payload phải là object.")
    try:
        raw = json.dumps(payload, ensure_ascii=False, allow_nan=False,
                         separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProjectError("Project payload không phải JSON hợp lệ.") from exc
    if len(raw) > MAX_PROJECT_BYTES:
        raise ProjectError("Project payload vượt giới hạn 1 MiB.")
    if _depth(payload) > MAX_PROJECT_DEPTH:
        raise ProjectError("Project payload lồng quá sâu.")
    if _contains_forbidden(payload):
        raise ProjectError("Project payload chứa trường bí mật bị cấm.")


def get_owned(db: Session, project_id: str, user_id: str,
              app_slug: str) -> AppProject:
    row = db.get(AppProject, project_id)
    if row is None or row.user_id != user_id or row.app_slug != app_slug:
        raise ProjectNotFound("Không tìm thấy project.")
    return row


def create(db: Session, *, user_id: str, app_slug: str, name: str,
           schema_version: int, payload: dict) -> AppProject:
    validate_container_payload(payload)
    if schema_version < 1:
        raise ProjectError("schema_version không hợp lệ.")
    row = AppProject(user_id=user_id, app_slug=app_slug,
                     name=(name.strip() or "Project mới")[:160],
                     schema_version=schema_version, payload=copy.deepcopy(payload))
    db.add(row); db.flush()
    return row


def save(db: Session, *, project_id: str, user_id: str, app_slug: str,
         revision: int, name: str, schema_version: int, payload: dict) -> AppProject:
    row = get_owned(db, project_id, user_id, app_slug)
    if row.status == APP_PROJECT_ARCHIVED:
        raise ProjectError("Project đã lưu trữ.")
    validate_container_payload(payload)
    result = db.execute(update(AppProject).where(
        AppProject.id == project_id, AppProject.user_id == user_id,
        AppProject.app_slug == app_slug, AppProject.revision == revision).values(
            name=(name.strip() or "Project mới")[:160],
            schema_version=schema_version, payload=copy.deepcopy(payload),
            revision=revision + 1, updated_at=datetime.now(timezone.utc)))
    if result.rowcount != 1:
        raise ProjectConflict("Project đã được sửa ở phiên khác.")
    db.flush(); db.expire(row)
    return row


def archive(db: Session, row: AppProject) -> AppProject:
    if row.status != APP_PROJECT_ARCHIVED:
        row.status = APP_PROJECT_ARCHIVED
        row.revision += 1
        row.updated_at = datetime.now(timezone.utc)
        db.flush()
    return row
