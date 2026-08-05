"""
storyboard.py — cảnh, phiên bản theo cảnh, và ghép prompt cho từng cảnh.

Đây là chỗ hai lớp trước gặp nhau: mỗi cảnh lấy **tài nguyên** để giữ nhất quán
nhân vật, và lấy **meta prompt + phong cách** từ thư viện để giữ giọng chung.

Điều quan trọng nhất của màn này, và cũng là thứ module nguồn làm được mà bản
OMMI trước không: **chạy lại MỘT cảnh** mà không đụng các cảnh khác, giữ bản cũ
để so. Không có nó thì sửa một khung phải trả tiền dựng lại cả bộ.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.tables import (OmmiResource, OmmiScene,
                                        OmmiSceneVersion, OmmiStoryboard,
                                        OmmiStyle)

MAX_NAME = 160
MAX_PROMPT = 12000
MAX_SCENES = 60


class StoryboardError(ValueError):
    """Dữ liệu vào không hợp lệ — route trả 400."""


class StoryboardNotFound(LookupError):
    """Không tồn tại HOẶC không thuộc về người gọi — route trả 404."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_name(value: str) -> str:
    name = (value or "").strip()
    if not name:
        raise StoryboardError("Tên không được để trống.")
    return name[:MAX_NAME]


# ── storyboard ─────────────────────────────────────────────────────────────

def get_owned_board(db: Session, board_id: str, owner_id: str) -> OmmiStoryboard:
    row = db.get(OmmiStoryboard, board_id)
    if row is None or row.owner_id != owner_id:
        raise StoryboardNotFound("Không tìm thấy storyboard.")
    return row


def create_board(db: Session, *, owner_id: str, project_id: str, name: str,
                 aspect_ratio: str = "16:9") -> OmmiStoryboard:
    if not owner_id or not project_id:
        raise StoryboardError("Thiếu chủ sở hữu hoặc project.")
    row = OmmiStoryboard(owner_id=owner_id, project_id=project_id,
                         name=_clean_name(name), aspect_ratio=aspect_ratio[:12])
    db.add(row)
    db.flush()
    return row


def list_boards(db: Session, owner_id: str, *, project_id: str = "",
                include_archived: bool = False) -> list:
    conditions = [OmmiStoryboard.owner_id == owner_id]
    if project_id:
        conditions.append(OmmiStoryboard.project_id == project_id)
    if not include_archived:
        conditions.append(OmmiStoryboard.archived_at.is_(None))
    return list(db.execute(
        select(OmmiStoryboard).where(*conditions)
        .order_by(OmmiStoryboard.updated_at.desc()).limit(200)
    ).scalars().all())


def update_board(db: Session, *, board_id: str, owner_id: str, **fields):
    row = get_owned_board(db, board_id, owner_id)
    if "name" in fields:
        row.name = _clean_name(fields["name"])
    if "aspect_ratio" in fields:
        row.aspect_ratio = str(fields["aspect_ratio"] or "16:9")[:12]
    for key in ("meta_prompt_id", "style_id"):
        if key in fields:
            setattr(row, key, str(fields[key]) if fields[key] else None)
    row.updated_at = _now()
    db.flush()
    return row


def archive_board(db: Session, *, board_id: str, owner_id: str,
                  archived: bool = True):
    row = get_owned_board(db, board_id, owner_id)
    row.archived_at = _now() if archived else None
    row.updated_at = _now()
    db.flush()
    return row


# ── cảnh ───────────────────────────────────────────────────────────────────

def get_owned_scene(db: Session, scene_id: str, owner_id: str) -> OmmiScene:
    row = db.get(OmmiScene, scene_id)
    if row is None or row.owner_id != owner_id:
        raise StoryboardNotFound("Không tìm thấy cảnh.")
    return row


def scenes(db: Session, board_id: str, owner_id: str) -> list:
    get_owned_board(db, board_id, owner_id)
    return list(db.execute(
        select(OmmiScene).where(OmmiScene.storyboard_id == board_id)
        .order_by(OmmiScene.position)
    ).scalars().all())


def add_scene(db: Session, *, board_id: str, owner_id: str, title: str = "",
              prompt: str = "", camera: str = "",
              resource_ids: list | None = None) -> OmmiScene:
    get_owned_board(db, board_id, owner_id)
    total = db.execute(
        select(func.count()).select_from(OmmiScene)
        .where(OmmiScene.storyboard_id == board_id)).scalar_one()
    if total >= MAX_SCENES:
        raise StoryboardError(f"Một storyboard tối đa {MAX_SCENES} cảnh.")
    position = db.execute(
        select(func.coalesce(func.max(OmmiScene.position), -1))
        .where(OmmiScene.storyboard_id == board_id)).scalar_one() + 1
    row = OmmiScene(owner_id=owner_id, storyboard_id=board_id, position=position,
                    title=str(title or "")[:200], prompt=str(prompt or "")[:MAX_PROMPT],
                    camera=str(camera or "")[:200],
                    resource_ids=_clean_resource_ids(db, resource_ids, owner_id))
    db.add(row)
    db.flush()
    return row


def _clean_resource_ids(db: Session, ids, owner_id: str) -> list:
    """Chỉ giữ tài nguyên CỦA CHÍNH người gọi.

    Danh sách này đi thẳng vào tham số job, tức vào provider. Nhận ID lạ là ép
    provider đọc ảnh riêng tư của người khác — rò rỉ qua đường vòng, đúng kiểu
    đã phải sửa ở màn sinh ảnh cho tài nguyên.
    """
    wanted = [str(item) for item in (ids or [])[:8] if item]
    if not wanted:
        return []
    owned = db.execute(
        select(OmmiResource.id).where(OmmiResource.id.in_(wanted),
                                      OmmiResource.owner_id == owner_id)
    ).scalars().all()
    keep = set(owned)
    return [item for item in wanted if item in keep]


def update_scene(db: Session, *, scene_id: str, owner_id: str, **fields):
    row = get_owned_scene(db, scene_id, owner_id)
    if "title" in fields:
        row.title = str(fields["title"] or "")[:200]
    if "prompt" in fields:
        row.prompt = str(fields["prompt"] or "")[:MAX_PROMPT]
    if "camera" in fields:
        row.camera = str(fields["camera"] or "")[:200]
    if "continuity" in fields:
        row.continuity = str(fields["continuity"] or "")[:MAX_PROMPT]
    if "resource_ids" in fields:
        row.resource_ids = _clean_resource_ids(db, fields["resource_ids"], owner_id)
    row.updated_at = _now()
    db.flush()
    return row


def delete_scene(db: Session, *, scene_id: str, owner_id: str) -> None:
    """Xoá hẳn một cảnh và dồn lại thứ tự.

    Để hở chỗ trống trong `position` thì lần chèn sau tính sai vị trí và cảnh
    nhảy lung tung — người dùng thấy như dữ liệu bị hỏng.
    """
    row = get_owned_scene(db, scene_id, owner_id)
    board_id = row.storyboard_id
    for version in db.execute(
            select(OmmiSceneVersion)
            .where(OmmiSceneVersion.scene_id == scene_id)).scalars().all():
        db.delete(version)
    db.delete(row)
    db.flush()
    for index, remaining in enumerate(db.execute(
            select(OmmiScene).where(OmmiScene.storyboard_id == board_id)
            .order_by(OmmiScene.position)).scalars().all()):
        remaining.position = index
    db.flush()


def reorder(db: Session, *, board_id: str, owner_id: str, scene_ids: list) -> list:
    """Đặt lại thứ tự. Chỉ nhận đúng tập cảnh của storyboard này."""
    current = scenes(db, board_id, owner_id)
    by_id = {row.id: row for row in current}
    wanted = [str(item) for item in (scene_ids or []) if str(item) in by_id]
    if len(wanted) != len(current):
        raise StoryboardError("Danh sách sắp xếp phải chứa đúng mọi cảnh của storyboard.")
    for index, scene_id in enumerate(wanted):
        by_id[scene_id].position = index
    db.flush()
    return [by_id[item] for item in wanted]


# ── phiên bản theo cảnh ────────────────────────────────────────────────────

def record_version(db: Session, *, scene_id: str, owner_id: str,
                   image_key: str, job_id: str = "") -> OmmiSceneVersion:
    """Ghi kết quả một lần chạy vào lịch sử CỦA CẢNH ĐÓ, rồi đặt làm ảnh hiện tại."""
    row = get_owned_scene(db, scene_id, owner_id)
    version = OmmiSceneVersion(owner_id=owner_id, scene_id=scene_id,
                               version=int(row.version or 1), prompt=row.prompt,
                               image_key=image_key, job_id=job_id)
    db.add(version)
    row.image_key = image_key
    row.version = int(row.version or 1) + 1
    row.updated_at = _now()
    db.flush()
    return version


def versions(db: Session, scene_id: str, owner_id: str) -> list:
    get_owned_scene(db, scene_id, owner_id)
    return list(db.execute(
        select(OmmiSceneVersion)
        .where(OmmiSceneVersion.scene_id == scene_id,
               OmmiSceneVersion.owner_id == owner_id)
        .order_by(OmmiSceneVersion.version.desc())
    ).scalars().all())


def restore_version(db: Session, *, scene_id: str, owner_id: str,
                    version: int) -> OmmiScene:
    """Quay về một bản cũ — đặt lại ảnh, KHÔNG xoá lịch sử."""
    scene = get_owned_scene(db, scene_id, owner_id)
    row = db.execute(
        select(OmmiSceneVersion)
        .where(OmmiSceneVersion.scene_id == scene_id,
               OmmiSceneVersion.owner_id == owner_id,
               OmmiSceneVersion.version == int(version))).scalars().first()
    if row is None:
        raise StoryboardNotFound("Không tìm thấy phiên bản.")
    scene.image_key = row.image_key
    scene.updated_at = _now()
    db.flush()
    return scene


# ── ghép prompt ────────────────────────────────────────────────────────────

def compose_prompt(db: Session, *, scene_id: str, owner_id: str) -> str:
    """Prompt cuối cùng gửi provider cho MỘT cảnh.

    Ghép theo thứ tự: phong cách của storyboard → mô tả từng tài nguyên →
    prompt của cảnh → góc máy → continuity. Đặt phong cách trước để cảnh có thể
    ghi đè bằng mô tả cụ thể hơn, thay vì bị phong cách chung đè lại.
    """
    scene = get_owned_scene(db, scene_id, owner_id)
    board = get_owned_board(db, scene.storyboard_id, owner_id)

    parts: list[str] = []
    if board.style_id:
        style = db.get(OmmiStyle, board.style_id)
        # Phong cách phải của chính người gọi hoặc là mẫu catalog.
        if style is not None and style.owner_id in (owner_id, None) and style.body:
            parts.append(style.body.strip())

    for resource_id in scene.resource_ids or []:
        resource = db.get(OmmiResource, resource_id)
        if resource is not None and resource.owner_id == owner_id:
            text = (resource.prompt_text or resource.description or "").strip()
            if text:
                parts.append(f"{resource.name}: {text}")

    for value in (scene.prompt, scene.camera, scene.continuity):
        if (value or "").strip():
            parts.append(value.strip())

    return "\n".join(parts)[:MAX_PROMPT]


def reference_keys(db: Session, *, scene_id: str, owner_id: str) -> list:
    """Ảnh bìa của các tài nguyên gắn vào cảnh — dùng làm ảnh tham chiếu."""
    from apps.prompt_ai_ommi.tables import OmmiResourceVariant
    scene = get_owned_scene(db, scene_id, owner_id)
    keys: list[str] = []
    for resource_id in (scene.resource_ids or [])[:4]:
        resource = db.get(OmmiResource, resource_id)
        if resource is None or resource.owner_id != owner_id:
            continue
        if not resource.cover_variant_id:
            continue
        variant = db.get(OmmiResourceVariant, resource.cover_variant_id)
        if variant is not None and variant.owner_id == owner_id:
            keys.append(variant.storage_key)
    return keys
