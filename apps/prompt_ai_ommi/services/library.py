"""
library.py — thư viện riêng của người dùng: meta prompt, đoạn prompt, phong cách.

Ba loại này khác nhau ở ý nghĩa nhưng **giống hệt nhau ở vòng đời**: riêng tư
hoặc là mẫu catalog, sửa được thì ghi phiên bản, clone mẫu thành bản riêng, lưu
trữ thay vì xoá. Nên viết một lần rồi tham số hoá theo bảng, thay vì ba bản sao
lệch dần theo thời gian — module nguồn có `meta_prompt_manager`,
`style_manager` và phần prompt library tách rời, và chúng đã lệch nhau thật.

Mô hình sở hữu giống `resources.py`:

- `owner_id` có giá trị → riêng tư, chỉ chủ thấy và sửa.
- `owner_id` NULL       → mẫu catalog, ai cũng ĐỌC, chỉ admin ghi.

Người dùng "lấy" mẫu bằng cách clone. Không có đường nào sửa trực tiếp mẫu chung,
và không có đường nào thấy bản riêng của người khác.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from platform_core.i18n import _ as _t

from apps.prompt_ai_ommi.tables import (OmmiMetaPrompt, OmmiPromptSnippet,
                                        OmmiPromptVersion, OmmiStyle)
from apps.prompt_ai_ommi.services.builtin_catalog import (find_builtin,
                                                          list_builtins)

MAX_NAME = 160
MAX_BODY = 24000
PAGE_MAX = 100

#: Loại thư viện -> (model, có trường `purpose`/`category` không).
KINDS = {
    "meta": OmmiMetaPrompt,
    "snippet": OmmiPromptSnippet,
    "style": OmmiStyle,
}


class LibraryError(ValueError):
    """Dữ liệu vào không hợp lệ — route trả 400."""


class LibraryNotFound(LookupError):
    """Không tồn tại HOẶC không thuộc về người gọi — route trả 404."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _model(kind: str):
    model = KINDS.get((kind or "").strip().lower())
    if model is None:
        raise LibraryError(
            f"Loại thư viện không hợp lệ: {kind!r}. "
            f"Chọn một trong: {', '.join(KINDS)}.")
    return model


def _clean_name(value: str) -> str:
    name = (value or "").strip()
    if not name:
        raise LibraryError("Tên không được để trống.")
    if len(name) > MAX_NAME:
        raise LibraryError(f"Tên vượt {MAX_NAME} ký tự.")
    return name


def _clean_body(value) -> str:
    body = value or ""
    if not isinstance(body, str):
        raise LibraryError("Nội dung phải là chuỗi.")
    if len(body) > MAX_BODY:
        raise LibraryError(f"Nội dung vượt {MAX_BODY} ký tự.")
    return body


# ── đọc ────────────────────────────────────────────────────────────────────

def get_owned(db: Session, kind: str, item_id: str, owner_id: str):
    """Bản ghi CỦA CHÍNH người gọi. Mẫu catalog không thuộc về ai nên không lọt."""
    row = db.get(_model(kind), item_id)
    if row is None or row.owner_id != owner_id:
        raise LibraryNotFound("Không tìm thấy mục thư viện.")
    return row


def get_visible(db: Session, kind: str, item_id: str, owner_id: str):
    """Bản ghi người gọi ĐƯỢC XEM: của mình, hoặc mẫu catalog."""
    model = _model(kind)
    built_in = find_builtin(kind, item_id)
    if built_in is not None:
        return built_in
    row = db.get(model, item_id)
    if row is None or (row.owner_id is not None and row.owner_id != owner_id):
        raise LibraryNotFound("Không tìm thấy mục thư viện.")
    return row


def list_items(db: Session, kind: str, owner_id: str, *, catalog: bool = False,
               query: str = "", include_archived: bool = False,
               include_deprecated: bool = False,
               limit: int = 40, offset: int = 0) -> tuple[list, int]:
    """Danh sách. `catalog=True` trả mẫu chung, ngược lại trả bản riêng.

    Hai tập tách hẳn chứ không trộn: người dùng cần biết cái nào sửa được, và
    trộn vào một danh sách là cách chắc chắn để họ sửa nhầm rồi ngạc nhiên.
    """
    model = _model(kind)
    limit = max(1, min(PAGE_MAX, int(limit or 40)))
    offset = max(0, int(offset or 0))

    conditions = [model.owner_id.is_(None) if catalog
                  else model.owner_id == owner_id]
    if not include_archived:
        conditions.append(model.archived_at.is_(None))
    # Mẫu đã ngừng dùng biến khỏi danh sách CHÀO MỜI, nhưng bản riêng của người
    # đã clone thì không đụng tới — họ vẫn đang dùng nó để làm việc (H19.6).
    if catalog and not include_deprecated:
        conditions.append(model.deprecated_at.is_(None))
    if query:
        like = f"%{query.strip()[:80]}%"
        conditions.append(or_(model.name.ilike(like), model.body.ilike(like)))

    total_db = db.execute(
        select(func.count()).select_from(model).where(*conditions)).scalar_one()
    if catalog:
        builtins = list_builtins(kind, query=query)
        builtin_page = builtins[offset:offset + limit]
        remaining = limit - len(builtin_page)
        db_offset = max(0, offset - len(builtins))
        rows = []
        if remaining > 0:
            rows = db.execute(
                select(model).where(*conditions)
                .order_by(model.updated_at.desc())
                .limit(remaining).offset(db_offset)
            ).scalars().all()
        return [*builtin_page, *rows], len(builtins) + int(total_db)

    rows = db.execute(
        select(model).where(*conditions)
        .order_by(model.updated_at.desc()).limit(limit).offset(offset)
    ).scalars().all()
    return list(rows), int(total_db)


def versions(db: Session, kind: str, item_id: str, owner_id: str) -> list:
    """Lịch sử sửa. Chỉ của bản riêng — mẫu catalog không có lịch sử cho user."""
    get_owned(db, kind, item_id, owner_id)
    return list(db.execute(
        select(OmmiPromptVersion)
        .where(OmmiPromptVersion.target_kind == kind,
               OmmiPromptVersion.target_id == item_id,
               OmmiPromptVersion.owner_id == owner_id)
        .order_by(OmmiPromptVersion.version.desc())
    ).scalars().all())


# ── ghi ────────────────────────────────────────────────────────────────────

def _record_version(db: Session, kind: str, row, owner_id: str,
                    note: str = "") -> None:
    db.add(OmmiPromptVersion(owner_id=owner_id, target_kind=kind,
                             target_id=row.id, version=row.version,
                             body=row.body, note=note[:300]))


def create(db: Session, kind: str, *, owner_id: str, name: str, body: str = "",
           **extra):
    if not owner_id:
        raise LibraryError("Thiếu chủ sở hữu.")
    model = _model(kind)
    row = model(owner_id=owner_id, name=_clean_name(name), body=_clean_body(body))
    if kind == "meta":
        row.purpose = str(extra.get("purpose") or "director")[:64]
        row.variables = extra.get("variables") if isinstance(
            extra.get("variables"), dict) else {}
    elif kind == "snippet":
        row.category = str(extra.get("category") or "")[:64]
    elif kind == "style":
        row.negative = _clean_body(extra.get("negative"))
        row.attributes = extra.get("attributes") if isinstance(
            extra.get("attributes"), dict) else {}
    db.add(row)
    db.flush()
    if kind in ("meta", "snippet"):
        _record_version(db, kind, row, owner_id, "Bản đầu")
    db.flush()
    return row


def update(db: Session, kind: str, *, item_id: str, owner_id: str, **fields):
    """Sửa. Nội dung đổi thì tăng phiên bản và ghi lại bản cũ.

    Chỉ tăng khi `body` THẬT SỰ đổi: đổi mỗi cái tên mà cũng đẻ ra một phiên bản
    thì lịch sử đầy rác và người dùng không tìm nổi lần sửa có ý nghĩa.
    """
    row = get_owned(db, kind, item_id, owner_id)
    body_changed = "body" in fields and _clean_body(fields["body"]) != row.body

    if "name" in fields:
        row.name = _clean_name(fields["name"])
    if body_changed:
        row.body = _clean_body(fields["body"])
    if kind == "meta":
        if "purpose" in fields:
            row.purpose = str(fields["purpose"] or "director")[:64]
        if "variables" in fields and isinstance(fields["variables"], dict):
            row.variables = fields["variables"]
    elif kind == "snippet":
        if "category" in fields:
            row.category = str(fields["category"] or "")[:64]
    elif kind == "style":
        if "negative" in fields:
            row.negative = _clean_body(fields["negative"])
        if "attributes" in fields and isinstance(fields["attributes"], dict):
            row.attributes = fields["attributes"]

    if body_changed and kind in ("meta", "snippet"):
        row.version = int(row.version or 1) + 1
        _record_version(db, kind, row, owner_id, str(fields.get("note") or ""))
    row.updated_at = _now()
    db.flush()
    return row


def archive(db: Session, kind: str, *, item_id: str, owner_id: str,
            archived: bool = True):
    row = get_owned(db, kind, item_id, owner_id)
    row.archived_at = _now() if archived else None
    row.updated_at = _now()
    db.flush()
    return row


def clone_from_catalog(db: Session, kind: str, *, item_id: str, owner_id: str):
    """"Dùng mẫu này" — tạo bản sao thuộc về người gọi.

    Chỉ clone được MẪU CATALOG. Không kiểm điều đó thì biết ID là sao chép được
    bản riêng của người khác, tức rò rỉ qua đường vòng.
    """
    model = _model(kind)
    source = find_builtin(kind, item_id) or db.get(model, item_id)
    if source is None or source.owner_id is not None:
        raise LibraryNotFound("Không tìm thấy mẫu.")
    if source.deprecated_at is not None:
        # Chặn ở service chứ không chỉ ẩn ở danh sách: ẩn khỏi giao diện mà vẫn
        # clone được bằng ID là "ngừng dùng" chỉ trên danh nghĩa.
        raise LibraryError(
            f"Mẫu này đã ngừng dùng. {source.deprecated_note}".strip())

    copy = model(owner_id=owner_id, name=source.name, body=source.body,
                 cloned_from_id=source.id)
    if kind == "meta":
        copy.purpose = source.purpose
        copy.variables = dict(source.variables or {})
    elif kind == "snippet":
        copy.category = source.category
    elif kind == "style":
        copy.negative = source.negative
        copy.attributes = dict(source.attributes or {})
    db.add(copy)
    db.flush()
    if kind in ("meta", "snippet"):
        _record_version(db, kind, copy, owner_id, f"Clone từ mẫu {source.name}")
    db.flush()
    return copy


def publish_to_catalog(db: Session, kind: str, *, item_id: str, owner_id: str,
                       is_admin: bool):
    """Đưa một bản riêng thành mẫu catalog. CHỈ admin.

    Người dùng thường publish được nghĩa là họ đẩy nội dung vào không gian mọi
    người đọc — vừa là kênh phát tán, vừa phá mô hình sở hữu.
    """
    if not is_admin:
        raise LibraryError("Chỉ admin được publish mẫu vào catalog.")
    source = get_owned(db, kind, item_id, owner_id)
    model = _model(kind)
    copy = model(owner_id=None, name=source.name, body=source.body,
                 is_catalog=True)
    if kind == "meta":
        copy.purpose = source.purpose
        copy.variables = dict(source.variables or {})
    elif kind == "snippet":
        copy.category = source.category
    elif kind == "style":
        copy.negative = source.negative
        copy.attributes = dict(source.attributes or {})
    db.add(copy)
    db.flush()
    return copy


def counts(db: Session, owner_id: str) -> dict:
    """Số mục của từng loại — dùng cho ô đếm trên Tổng quan."""
    out = {}
    for kind, model in KINDS.items():
        out[kind] = int(db.execute(
            select(func.count()).select_from(model)
            .where(model.owner_id == owner_id, model.archived_at.is_(None))
        ).scalar_one())
    return out


def deprecate(db: Session, kind: str, *, item_id: str, is_admin: bool,
              note: str = "", deprecated: bool = True):
    """Ngừng chào mời một mẫu catalog. CHỈ admin (H19.6).

    KHÔNG xoá, KHÔNG chạm tới bản riêng của những người đã clone. Người đã dùng
    mẫu này vẫn làm việc bình thường; chỉ là không ai clone mới được nữa.

    `note` nên nói rõ dùng gì thay thế — "đã ngừng dùng" mà không nói thay bằng
    gì thì người dùng chỉ biết mình đang cầm thứ lỗi thời.
    """
    if not is_admin:
        raise LibraryError("Chỉ admin được ngừng dùng mẫu catalog.")
    model = _model(kind)
    if find_builtin(kind, item_id) is not None:
        raise LibraryError(_t(
            "Mẫu tích hợp đi cùng phiên bản ứng dụng và không thể ngừng dùng "
            "trong quản trị. Hãy cập nhật catalog ở bản phát hành kế tiếp."))
    row = db.get(model, item_id)
    if row is None or row.owner_id is not None:
        raise LibraryNotFound("Không tìm thấy mẫu.")
    row.deprecated_at = _now() if deprecated else None
    row.deprecated_note = (note or "").strip()[:300] if deprecated else ""
    row.updated_at = _now()
    db.flush()
    return row


def deprecated_sources(db: Session, kind: str, owner_id: str) -> list:
    """Bản riêng của người này mà MẪU GỐC đã ngừng dùng.

    Để giao diện nói được "mẫu gốc của bản này đã ngừng dùng, xem thay thế" —
    không có phép tra này thì người dùng chỉ phát hiện ra khi kết quả tệ đi.
    """
    model = _model(kind)
    cua_toi = db.execute(select(model).where(
        model.owner_id == owner_id, model.archived_at.is_(None),
        model.cloned_from_id.is_not(None))).scalars().all()
    ra = []
    for row in cua_toi:
        goc = db.get(model, row.cloned_from_id)
        if goc is not None and goc.deprecated_at is not None:
            ra.append({"id": row.id, "name": row.name,
                       "source_id": goc.id, "source_name": goc.name,
                       "note": goc.deprecated_note or ""})
    return ra
