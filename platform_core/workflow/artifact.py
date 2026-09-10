"""Artifact với id **tự mô tả backend** — `"<backend>:<key>"` (`G33` `G35` `G36`).

🔴 **Bản vá cho một lỗ SẼ nổ, không phải lỗ đang nổ.** Ngày LTT bật R2 song song
   Local, `storage.get_storage()` là một **singleton toàn cục** ⇒ mọi khoá cũ
   thành mơ hồ. Một `"abc/def.png"` nằm trong `output_ref` của bước trước không
   nói nó ở đâu, và không có chỗ nào để tra.

⭐ Bài học n8n (`05 §4.1`): id phải tự mô tả backend, **vì tham chiếu đi vào
   `output_ref` của bước sau và JSONB không tra bảng được**. Đó là lý do kỹ
   thuật, không phải sở thích đặt tên.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from platform_core.models import Artifact

#: Backend đã biết. Danh sách đóng có chủ ý: một id mang tên backend lạ là một
#: id không ai đọc được, và nó sẽ nằm trong `output_ref` mãi mãi.
BACKEND = frozenset({"local", "r2"})

#: ⚠️ Backend nào có **vòng đời riêng** thì ta KHÔNG tự xoá (bài học n8n:
#: `delete` là **tuỳ chọn** của hợp đồng lưu trữ). R2 có lifecycle rule của
#: chính nó; chồng TTL của ta lên trên là hai bộ đếm cùng nhắm một tệp, và bộ
#: nào chạy trước thì bộ kia thao tác trên hư không.
_TU_XOA = {"local": True, "r2": False}

TTL_CLASS = frozenset({"EPHEMERAL", "RUN", "PROJECT", "PERMANENT"})

_HAN = {
    "EPHEMERAL": timedelta(hours=6),
    "RUN": timedelta(days=7),
    "PROJECT": timedelta(days=90),
}


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def tach_id(artifact_id: str) -> tuple[str, str]:
    """`"r2:a/b.png"` → `("r2", "a/b.png")`."""
    backend, _, key = artifact_id.partition(":")
    return backend, key


def ta_tu_xoa(backend: str) -> bool:
    return bool(_TU_XOA.get(backend, False))


def ghi_danh(db, *, owner_id: str, backend: str, key: str, kind: str,
             ttl_class: str, mime: str = "", size_bytes: int = 0,
             checksum_sha256: str = "",
             created_by_snapshot_id: str = "",
             metadata: Optional[dict] = None) -> Artifact:
    """Ghi danh một artifact. `id` sinh ra từ `backend` + `key`.

    ⛔ `key` **không được chứa `:`** — nếu chứa thì `tach_id()` không tách đúng
       được nữa, và một id không tách được là một id vô dụng ở đúng lúc cần
       nhất: khi ai đó đọc `output_ref` của một run đã chạy xong từ lâu.
    """
    if backend not in BACKEND:
        raise ValueError(
            f"backend khong biet: {backend!r}; can mot trong {sorted(BACKEND)}")
    if ":" in key:
        raise ValueError(
            f"key khong duoc chua ':' (nhan {key!r}) — no la dau tach cua id")
    if ttl_class not in TTL_CLASS:
        raise ValueError(f"ttl_class khong hop le: {ttl_class!r}")

    han = _HAN.get(ttl_class)
    a = Artifact(
        id=f"{backend}:{key}", owner_id=owner_id, kind=kind, mime=mime,
        size_bytes=int(size_bytes or 0), checksum_sha256=checksum_sha256,
        ttl_class=ttl_class,
        expires_at=(_bay_gio() + han) if han else None,
        created_by_snapshot_id=created_by_snapshot_id,
        meta=dict(metadata or {}))
    db.add(a)
    db.flush()
    return a


def het_han(db, gioi_han: int = 500) -> list[Artifact]:
    """Artifact đã quá hạn. **Không bao giờ** chạm tới `PERMANENT`.

    Một truy vấn cho toàn hệ thống, đi vào chỉ số bộ phận `ix_artifact_expiry`.
    """
    return list(db.execute(
        select(Artifact)
        .where(Artifact.ttl_class != "PERMANENT",
               Artifact.expires_at.is_not(None),
               Artifact.expires_at <= _bay_gio())
        .order_by(Artifact.expires_at)
        .limit(max(1, int(gioi_han)))).scalars())
