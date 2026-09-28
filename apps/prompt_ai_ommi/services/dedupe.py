"""dedupe.py — sha256 cua bytes tep GOC + tra cuu theo CHU SO HUU (pha 5).

⚠️ Dedupe theo `(owner_id, file_hash)`, KHONG theo `file_hash` toan cuc: hai
khach tai cung mot anh la HAI ban ghi rieng, vi quyen so huu khac nhau — gop
chung se lam mot khach xoa anh cua minh xoa luon anh cua nguoi khac dang tro
vao cung hang, va te hai hon: se lam mot khach NHIN THAY anh cua nguoi khac
qua ket qua "da co roi" cua dedupe (ro ri lien khach).

`file_hash` la sha256 cua BYTES TE GOC, truoc moi buoc chuan hoa (resize/nen).
Goi ham nay TRUOC khi lam bat cu dieu gi khac voi du lieu vua nhan.
"""
from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.tables import OmmiResourceVariant


def compute_file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_existing(db: Session, *, owner_id: str,
                  file_hash: str) -> OmmiResourceVariant | None:
    """Bản đã có CỦA CHÍNH `owner_id` với cùng `file_hash`, hoặc `None`.

    Không lọc theo `resource_id`: một khách import lại cùng file vào một
    resource khác vẫn được coi là "đã có", vì mục đích của dedupe là không để
    một tài khoản giữ hai bản y hệt nhau trên storage — không phải để ép file
    ở đúng một resource.

    ⭐ Bất biến chống rò rỉ liên khách: hàm này LUÔN lọc theo `owner_id` trong
    chính câu SQL — không có đường nào để một `file_hash` trùng của một chủ
    khác lọt qua bộ lọc này, kể cả khi hai chủ tải lên cùng bytes.
    """
    if not file_hash:
        return None
    return db.execute(
        select(OmmiResourceVariant)
        .where(OmmiResourceVariant.owner_id == owner_id,
               OmmiResourceVariant.file_hash == file_hash)
        .order_by(OmmiResourceVariant.created_at)
    ).scalars().first()
