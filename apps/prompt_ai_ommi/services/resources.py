"""
resources.py — kho tài nguyên riêng của từng người dùng.

Quy tắc duy nhất, áp cho mọi hàm trong file: **không có truy vấn nào không lọc
theo `owner_id`.**

Module nguồn (`D:\\BOT GEMINI`) có ba tầng sở hữu trên giấy nhưng `scoping.py`
lại lọc mọi thứ theo một `master_user_id` dùng chung, nên mọi khách hàng nhìn
chung một kho. Lỗi đó không lộ khi thử một mình — chỉ lộ khi có người thứ hai,
và lúc đó là rò rỉ dữ liệu của khách hàng trả tiền.

Ngữ nghĩa lỗi: "không tồn tại" và "không phải của bạn" ném **cùng một** ngoại
lệ → route trả 404. Trả 403 cho bản ghi của người khác là xác nhận nó có thật,
tức vẫn rò rỉ cho người đi dò ID.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.tables import (RESOURCE_KINDS, OmmiCollection,
                                        OmmiCollectionItem, OmmiResource,
                                        OmmiResourceTag, OmmiResourceUsage,
                                        OmmiResourceVariant, OmmiTag)

MAX_NAME = 160
MAX_TEXT = 8000
PAGE_MAX = 100


class ResourceError(ValueError):
    """Dữ liệu vào không hợp lệ — route trả 400."""


class ResourceNotFound(LookupError):
    """Không tồn tại HOẶC không thuộc về người gọi — route trả 404."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_name(value: str) -> str:
    name = (value or "").strip()
    if not name:
        raise ResourceError("Tên không được để trống.")
    if len(name) > MAX_NAME:
        raise ResourceError(f"Tên vượt {MAX_NAME} ký tự.")
    return name


def _clean_text(value, limit: int = MAX_TEXT) -> str:
    text = (value or "")
    if not isinstance(text, str):
        raise ResourceError("Trường văn bản phải là chuỗi.")
    if len(text) > limit:
        raise ResourceError(f"Nội dung vượt {limit} ký tự.")
    return text.strip()


def _clean_kind(value: str) -> str:
    kind = (value or "").strip().lower()
    if kind not in RESOURCE_KINDS:
        raise ResourceError(
            f"Loại tài nguyên không hợp lệ: {value!r}. "
            f"Chọn một trong: {', '.join(RESOURCE_KINDS)}.")
    return kind


# ── đọc ────────────────────────────────────────────────────────────────────

def get_owned(db: Session, resource_id: str, owner_id: str) -> OmmiResource:
    """Lấy tài nguyên CỦA CHÍNH người gọi. Mẫu catalog không tính là của ai.

    Đây là cửa duy nhất để lấy một tài nguyên trước khi sửa. Mọi hàm ghi ở dưới
    đều đi qua đây thay vì tự truy vấn — một chỗ để đúng thay vì mười chỗ để
    quên.
    """
    row = db.get(OmmiResource, resource_id)
    if row is None or row.owner_id != owner_id:
        raise ResourceNotFound("Không tìm thấy tài nguyên.")
    return row


def get_visible(db: Session, resource_id: str, owner_id: str) -> OmmiResource:
    """Lấy tài nguyên người gọi ĐƯỢC XEM: của mình, hoặc mẫu catalog."""
    row = db.get(OmmiResource, resource_id)
    if row is None or (row.owner_id is not None and row.owner_id != owner_id):
        raise ResourceNotFound("Không tìm thấy tài nguyên.")
    return row


def list_resources(db: Session, owner_id: str, *, kind: str = "",
                   query: str = "", include_catalog: bool = False,
                   include_archived: bool = False,
                   limit: int = 40, offset: int = 0) -> tuple[list, int]:
    """Danh sách kho, đã phân trang. Trả về (rows, tổng số).

    Phân trang không phải tối ưu sớm: giao diện tham chiếu hiển thị 178 tài
    nguyên, và trả hết một lần thì trang đầu tiên đã chậm.
    """
    limit = max(1, min(PAGE_MAX, int(limit or 40)))
    offset = max(0, int(offset or 0))

    scope = (OmmiResource.owner_id == owner_id)
    if include_catalog:
        scope = or_(scope, OmmiResource.owner_id.is_(None))

    conditions = [scope]
    if kind:
        conditions.append(OmmiResource.kind == _clean_kind(kind))
    if not include_archived:
        conditions.append(OmmiResource.archived_at.is_(None))
    if query:
        like = f"%{query.strip()[:80]}%"
        conditions.append(or_(OmmiResource.name.ilike(like),
                              OmmiResource.description.ilike(like)))

    total = db.execute(
        select(func.count()).select_from(OmmiResource).where(*conditions)
    ).scalar_one()
    rows = db.execute(
        select(OmmiResource).where(*conditions)
        .order_by(OmmiResource.updated_at.desc())
        .limit(limit).offset(offset)
    ).scalars().all()
    return list(rows), int(total)


def count_by_kind(db: Session, owner_id: str) -> dict:
    """Đếm theo loại — số liệu ô "Phân loại tài nguyên" trên Tổng quan.

    Đếm bằng SQL chứ không tải hết rồi đếm trong Python: kho lớn thì cách sau
    ngốn bộ nhớ và chậm dần theo số tài nguyên.
    """
    rows = db.execute(
        select(OmmiResource.kind, func.count())
        .where(OmmiResource.owner_id == owner_id,
               OmmiResource.archived_at.is_(None))
        .group_by(OmmiResource.kind)
    ).all()
    counts = {kind: 0 for kind in RESOURCE_KINDS}
    for kind, total in rows:
        counts[kind] = int(total)
    return counts


def variants(db: Session, resource_id: str, owner_id: str) -> list:
    """Ảnh của một tài nguyên. Kiểm quyền qua chính tài nguyên đó."""
    get_visible(db, resource_id, owner_id)
    return list(db.execute(
        select(OmmiResourceVariant)
        .where(OmmiResourceVariant.resource_id == resource_id)
        .order_by(OmmiResourceVariant.position, OmmiResourceVariant.created_at)
    ).scalars().all())


def usage(db: Session, resource_id: str, owner_id: str) -> list:
    """Tài nguyên này đang dùng ở project nào — hỏi trước khi cho xoá."""
    get_owned(db, resource_id, owner_id)
    return list(db.execute(
        select(OmmiResourceUsage)
        .where(OmmiResourceUsage.resource_id == resource_id,
               OmmiResourceUsage.owner_id == owner_id)
    ).scalars().all())


# ── ghi ────────────────────────────────────────────────────────────────────

def create(db: Session, *, owner_id: str, kind: str, name: str,
           description: str = "", prompt_text: str = "",
           attributes: dict | None = None) -> OmmiResource:
    if not owner_id:
        raise ResourceError("Thiếu chủ sở hữu.")
    row = OmmiResource(
        owner_id=owner_id, kind=_clean_kind(kind), name=_clean_name(name),
        description=_clean_text(description), prompt_text=_clean_text(prompt_text),
        attributes=attributes if isinstance(attributes, dict) else {})
    db.add(row)
    db.flush()
    return row


def update(db: Session, *, resource_id: str, owner_id: str, **fields) -> OmmiResource:
    row = get_owned(db, resource_id, owner_id)
    if "name" in fields:
        row.name = _clean_name(fields["name"])
    if "kind" in fields:
        row.kind = _clean_kind(fields["kind"])
    if "description" in fields:
        row.description = _clean_text(fields["description"])
    if "prompt_text" in fields:
        row.prompt_text = _clean_text(fields["prompt_text"])
    if "attributes" in fields:
        value = fields["attributes"]
        row.attributes = value if isinstance(value, dict) else {}
    row.updated_at = _now()
    db.flush()
    return row


def archive(db: Session, *, resource_id: str, owner_id: str,
            archived: bool = True) -> OmmiResource:
    """Lưu trữ thay vì xoá hẳn.

    Nguồn có bảng `seedance_trash` riêng cho việc này; một cột ngày là đủ và
    không tạo ra hai nguồn sự thật về việc bản ghi còn sống hay không.
    """
    row = get_owned(db, resource_id, owner_id)
    row.archived_at = _now() if archived else None
    row.updated_at = _now()
    db.flush()
    return row


def clone_from_catalog(db: Session, *, resource_id: str, owner_id: str) -> OmmiResource:
    """Lấy một mẫu catalog thành bản riêng để sửa thoải mái.

    Đây là cách duy nhất dữ liệu đi từ catalog sang người dùng. Không có đường
    nào cho người dùng sửa trực tiếp mẫu chung.
    """
    source = db.get(OmmiResource, resource_id)
    if source is None or source.owner_id is not None:
        raise ResourceNotFound("Không tìm thấy mẫu.")
    copy = OmmiResource(
        owner_id=owner_id, kind=source.kind, name=source.name,
        description=source.description, prompt_text=source.prompt_text,
        attributes=dict(source.attributes or {}))
    db.add(copy)
    db.flush()
    for variant in db.execute(
            select(OmmiResourceVariant)
            .where(OmmiResourceVariant.resource_id == source.id)
            .order_by(OmmiResourceVariant.position)).scalars().all():
        db.add(OmmiResourceVariant(
            resource_id=copy.id, owner_id=owner_id, label=variant.label,
            storage_key=variant.storage_key, thumb_key=variant.thumb_key,
            width=variant.width, height=variant.height,
            bytes_size=variant.bytes_size, position=variant.position))
    db.flush()
    return copy


def add_variant(db: Session, *, resource_id: str, owner_id: str,
                storage_key: str, label: str = "", thumb_key: str = "",
                width: int = 0, height: int = 0,
                bytes_size: int = 0, file_hash: str = "") -> OmmiResourceVariant:
    resource = get_owned(db, resource_id, owner_id)
    if not (storage_key or "").strip():
        raise ResourceError("Thiếu khoá lưu trữ của ảnh.")
    position = db.execute(
        select(func.coalesce(func.max(OmmiResourceVariant.position), -1))
        .where(OmmiResourceVariant.resource_id == resource_id)
    ).scalar_one() + 1
    row = OmmiResourceVariant(
        resource_id=resource_id, owner_id=owner_id, label=_clean_text(label, 160),
        storage_key=storage_key.strip(), thumb_key=(thumb_key or "").strip(),
        width=int(width or 0), height=int(height or 0),
        bytes_size=int(bytes_size or 0), position=position,
        file_hash=(file_hash or "").strip() or None)
    db.add(row)
    db.flush()
    if not resource.cover_variant_id:
        resource.cover_variant_id = row.id
    resource.updated_at = _now()
    db.flush()
    return row


def remove_variant(db: Session, *, variant_id: str, owner_id: str) -> None:
    row = db.get(OmmiResourceVariant, variant_id)
    if row is None or row.owner_id != owner_id:
        raise ResourceNotFound("Không tìm thấy ảnh.")
    resource = get_owned(db, row.resource_id, owner_id)
    db.delete(row)
    db.flush()
    if resource.cover_variant_id == variant_id:
        nxt = db.execute(
            select(OmmiResourceVariant)
            .where(OmmiResourceVariant.resource_id == resource.id)
            .order_by(OmmiResourceVariant.position)
        ).scalars().first()
        resource.cover_variant_id = nxt.id if nxt else None
    resource.updated_at = _now()
    db.flush()


def set_tags(db: Session, *, resource_id: str, owner_id: str,
             names: list) -> list:
    """Đặt lại toàn bộ nhãn của một tài nguyên. Nhãn cũng riêng theo người dùng."""
    get_owned(db, resource_id, owner_id)
    cleaned = []
    for raw in (names or [])[:24]:
        name = (raw or "").strip().lower()[:64]
        if name and name not in cleaned:
            cleaned.append(name)

    tags = []
    for name in cleaned:
        tag = db.execute(
            select(OmmiTag).where(OmmiTag.owner_id == owner_id,
                                  OmmiTag.name == name)
        ).scalars().first()
        if tag is None:
            tag = OmmiTag(owner_id=owner_id, name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)

    for link in db.execute(
            select(OmmiResourceTag)
            .where(OmmiResourceTag.resource_id == resource_id)).scalars().all():
        db.delete(link)
    db.flush()
    for tag in tags:
        db.add(OmmiResourceTag(resource_id=resource_id, tag_id=tag.id))
    db.flush()
    return tags


def tags_of(db: Session, resource_id: str, owner_id: str) -> list:
    get_visible(db, resource_id, owner_id)
    return list(db.execute(
        select(OmmiTag)
        .join(OmmiResourceTag, OmmiResourceTag.tag_id == OmmiTag.id)
        .where(OmmiResourceTag.resource_id == resource_id)
        .order_by(OmmiTag.name)
    ).scalars().all())


# ── bộ sưu tập ─────────────────────────────────────────────────────────────

def create_collection(db: Session, *, owner_id: str, name: str,
                      description: str = "") -> OmmiCollection:
    row = OmmiCollection(owner_id=owner_id, name=_clean_name(name),
                         description=_clean_text(description))
    db.add(row)
    db.flush()
    return row


def get_owned_collection(db: Session, collection_id: str,
                         owner_id: str) -> OmmiCollection:
    row = db.get(OmmiCollection, collection_id)
    if row is None or row.owner_id != owner_id:
        raise ResourceNotFound("Không tìm thấy bộ sưu tập.")
    return row


def set_collection_items(db: Session, *, collection_id: str, owner_id: str,
                         resource_ids: list) -> list:
    """Đặt lại nội dung bộ sưu tập.

    Mỗi tài nguyên đều qua `get_owned`, nên không thể nhét ID của người khác vào
    bộ sưu tập của mình để đọc ké.
    """
    get_owned_collection(db, collection_id, owner_id)
    ordered = []
    for rid in (resource_ids or [])[:200]:
        if rid and rid not in ordered:
            get_owned(db, rid, owner_id)
            ordered.append(rid)

    for link in db.execute(
            select(OmmiCollectionItem)
            .where(OmmiCollectionItem.collection_id == collection_id)
    ).scalars().all():
        db.delete(link)
    db.flush()
    for index, rid in enumerate(ordered):
        db.add(OmmiCollectionItem(collection_id=collection_id,
                                  resource_id=rid, position=index))
    db.flush()
    return ordered
