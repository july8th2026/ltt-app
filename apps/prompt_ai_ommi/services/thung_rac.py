"""thung_rac.py — xoa THAT nhung phuc hoi duoc (pha 5).

Khac `OmmiResource.archived_at` (luu tru TAM, ban goc con nguyen trong bang
song): o day ban goc bi XOA THAT khoi bang song; snapshot du de dung lai
NGUYEN VEN — cung id, cung cot — nam trong `OmmiTrash.payload`.

`purge_after` mac dinh 30 ngay, cung so voi `retention.TUOI_TOI_THIEU` — dung
mot con so cho "thoi gian an toan truoc khi mat vinh vien" trong toan app.

⭐ Bat bien vong kin: `restore(delete_resource(x))` phai cho lai DUNG `x` —
TUNG TRUONG cua resource lan variant, khong chi `id`. `_resource_snapshot`/
`_variant_snapshot` liet ke tuong minh moi truong duoc giu; them cot moi vao
`OmmiResource`/`OmmiResourceVariant` ma quen them vao day la lam vong kin bi
ho mot truong, va no chi lo khi co nguoi thu roundtrip that (`test_5502`).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from platform_core.i18n import _ as _t
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.services import resources as rsvc
from apps.prompt_ai_ommi.services.resources import ResourceNotFound
from apps.prompt_ai_ommi.tables import OmmiResource, OmmiResourceVariant, OmmiTrash

PURGE_MAC_DINH_NGAY = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _resource_snapshot(row: OmmiResource) -> dict:
    return {"id": row.id, "kind": row.kind, "name": row.name,
            "description": row.description, "prompt_text": row.prompt_text,
            "attributes": row.attributes or {},
            "cover_variant_id": row.cover_variant_id}


def _variant_snapshot(row: OmmiResourceVariant) -> dict:
    return {"id": row.id, "label": row.label, "storage_key": row.storage_key,
            "thumb_key": row.thumb_key, "width": row.width,
            "height": row.height, "bytes_size": row.bytes_size,
            "position": row.position, "file_hash": row.file_hash,
            "favorite": row.favorite, "rating": row.rating}


def delete_resource(db: Session, *, resource_id: str, owner_id: str,
                    purge_after_days: int = PURGE_MAC_DINH_NGAY) -> OmmiTrash:
    """Xoá HẲN một tài nguyên (và mọi variant của nó) khỏi bảng sống.

    Snapshot đủ để `restore()` dựng lại y hệt, kể cả `id` — bindings hay
    project khác còn tham chiếu `resource_id` này vẫn trỏ đúng sau khi khôi
    phục.

    ⚠️ Nợ đã biết (ngoài phạm vi Task 4 theo plan pha 5 — payload chỉ khai
    resource + variant): `OmmiResourceTag`/`OmmiResourceUsage`/
    `OmmiCollectionItem` KHÔNG được snapshot hay dọn ở đây. Một tài nguyên có
    tag hoặc nằm trong usage/collection khi bị xoá sẽ để lại các liên kết đó
    trỏ vào một `resource_id` không còn trong bảng sống, và `restore()` KHÔNG
    dựng lại chúng. Việc dọn ba bảng này cần một quyết định sản phẩm (giữ hay
    bỏ tag/usage khi khôi phục) ngoài phạm vi task này — báo lại điều phối.
    """
    resource = rsvc.get_owned(db, resource_id, owner_id)
    variant_rows = rsvc.variants(db, resource_id, owner_id)
    payload = {"resource": _resource_snapshot(resource),
              "variants": [_variant_snapshot(v) for v in variant_rows]}
    trash = OmmiTrash(
        owner_id=owner_id, target_kind="resource", target_id=resource_id,
        payload=payload, deleted_at=_now(),
        purge_after=_now() + timedelta(days=purge_after_days))
    db.add(trash)
    for v in variant_rows:
        db.delete(v)
    db.delete(resource)
    db.flush()
    return trash


def restore(db: Session, *, trash_id: str, owner_id: str) -> OmmiResource:
    """Dựng lại ĐÚNG bản ghi cũ (cùng id) từ snapshot. Vé dùng một lần.

    ⭐ Dứt khoát theo chủ ý: hàm này đọc `payload` TẠI THỜI ĐIỂM GỌI, không
    giữ bản chụp nào khác. Ai sửa `OmmiTrash.payload` sau khi xoá (thao tác
    ngoài luồng, công cụ vận hành) thì bản sửa đó là thứ được khôi phục —
    không có merge với dữ liệu đã mất, không có "giữ bản gốc". Đây không phải
    một lỗ hổng bỏ sót; nó là hành vi DUY NHẤT hợp lý khi `payload` là nguồn
    sự thật duy nhất còn lại (`test_5502::
    test_restore_reflects_the_current_trash_payload_deterministically`).
    """
    row = db.get(OmmiTrash, trash_id)
    if row is None or row.owner_id != owner_id:
        # Tái dùng msgid đã dịch sẵn (bánh cóc ban-dich-thieu chỉ cho GIẢM số
        # mục chưa dịch) — "vé thùng rác" và "tài nguyên" cùng trỏ về một thứ
        # người dùng hiểu là "cái đã xoá", nên tái dùng không đổi ý nghĩa.
        raise ResourceNotFound(_t('Không tìm thấy tài nguyên.'))
    data = row.payload.get("resource") or {}
    resource = OmmiResource(
        id=data.get("id"), owner_id=owner_id, kind=data.get("kind", "misc"),
        name=data.get("name", ""), description=data.get("description", ""),
        prompt_text=data.get("prompt_text", ""),
        attributes=data.get("attributes") or {},
        cover_variant_id=data.get("cover_variant_id"))
    db.add(resource)
    for v in row.payload.get("variants") or []:
        db.add(OmmiResourceVariant(
            id=v.get("id"), resource_id=resource.id, owner_id=owner_id,
            label=v.get("label", ""), storage_key=v.get("storage_key", ""),
            thumb_key=v.get("thumb_key", ""), width=v.get("width", 0),
            height=v.get("height", 0), bytes_size=v.get("bytes_size", 0),
            position=v.get("position", 0), file_hash=v.get("file_hash"),
            favorite=bool(v.get("favorite", False)), rating=v.get("rating")))
    db.delete(row)
    db.flush()
    return resource


def list_trash(db: Session, *, owner_id: str) -> list[OmmiTrash]:
    return list(db.execute(
        select(OmmiTrash).where(OmmiTrash.owner_id == owner_id)
        .order_by(OmmiTrash.deleted_at.desc())
    ).scalars().all())


def purge_expired(db: Session, *, now: datetime | None = None,
                  storage=None) -> dict:
    """Xoá vĩnh viễn mọi vé đã quá hạn — kể cả file trên storage.

    Lỗi xoá file KHÔNG được làm hỏng cả lượt purge (cùng nguyên tắc với
    `retention.apply`): dòng CSDL đã đi rồi, một file thừa nằm lại vô hại hơn
    dừng giữa chừng.

    Không tạo hàng mồ côi: variant của resource đã purge đã bị xoá TẠI
    `delete_resource` (trước khi vào thùng rác), nên purge chỉ xoá đúng một
    hàng `OmmiTrash` — không còn bảng nào khác trỏ tới `target_id` để dọn
    thêm (`test_5502::test_purge_leaves_no_orphan_variant_rows`).
    """
    moc = now or _now()
    due = list(db.execute(
        select(OmmiTrash).where(OmmiTrash.purge_after <= moc)
    ).scalars().all())
    xoa_ban = 0
    xoa_anh = 0
    for row in due:
        if storage is not None:
            for v in row.payload.get("variants") or []:
                key = v.get("storage_key")
                if not key:
                    continue
                try:
                    storage.delete(key)
                    xoa_anh += 1
                except Exception:              # noqa: BLE001
                    pass
        db.delete(row)
        xoa_ban += 1
    db.flush()
    return {"da_xoa_ban": xoa_ban, "da_xoa_anh": xoa_anh}
