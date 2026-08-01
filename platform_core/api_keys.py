"""
api_keys.py — CRUD sổ API key (H8). Lớp nghiệp vụ quanh bảng `ApiKey`.

Bất biến: **không hàm nào trả credential thô** trừ `lay_credential` (chỉ
allocator/worker gọi để thực sự gọi API). UI/admin chỉ đọc `key_preview`.
Credential mã hoá at-rest qua `platform_core.secretbox` (LTT_TOKEN_ENCRYPTION_KEY).

Không tự commit — caller quyết định ranh giới transaction (như các module khác).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from platform_core import secretbox
from platform_core.models import ApiKey


class ApiKeyError(Exception):
    pass


def _chuan_hoa_categories(categories) -> list:
    from platform_core.models import (APIKEY_CAT_CHAT, APIKEY_CAT_IMAGE,
                                      APIKEY_CAT_MODEL, APIKEY_CAT_VIDEO)
    hop_le = {APIKEY_CAT_MODEL, APIKEY_CAT_CHAT, APIKEY_CAT_IMAGE, APIKEY_CAT_VIDEO}
    out = []
    for c in (categories or []):
        c = str(c).strip()
        if c not in hop_le:
            raise ApiKeyError(f"category khong hop le: {c!r}")
        if c not in out:
            out.append(c)
    return out


def tao_key(db: DbSession, *, provider: str, credential: str, name: str = "",
            categories=None, base_url: str = "", supported_models=None,
            default_model: str = "", priority: int = 100,
            owner_user_id: str = "") -> ApiKey:
    """Tạo một API key mới. `credential` là secret THÔ — sẽ mã hoá trước khi lưu."""
    provider = (provider or "").strip().lower()
    if not provider:
        raise ApiKeyError("thieu provider")
    if not (credential or "").strip():
        raise ApiKeyError("thieu credential")
    key = ApiKey(
        provider=provider,
        name=name or provider,
        categories=_chuan_hoa_categories(categories),
        credential_enc=secretbox.ma_hoa(credential),
        key_preview=secretbox.preview(credential),
        base_url=(base_url or "").strip(),
        supported_models=list(supported_models or []),
        default_model=(default_model or "").strip(),
        priority=int(priority),
        owner_user_id=(owner_user_id or "").strip(),
    )
    db.add(key)
    db.flush()
    return key


def dat_credential(db: DbSession, key: ApiKey, credential: str) -> None:
    """Đổi credential (mã hoá lại + cập nhật preview)."""
    if not (credential or "").strip():
        raise ApiKeyError("credential rong")
    key.credential_enc = secretbox.ma_hoa(credential)
    key.key_preview = secretbox.preview(credential)
    db.flush()


def lay_credential(db: DbSession, key: ApiKey) -> str:
    """Giải mã credential thô — CHỈ allocator/worker gọi để gọi API thật."""
    return secretbox.giai_ma(key.credential_enc)


def cap_nhat_supported_models(db: DbSession, key: ApiKey, models) -> None:
    """Ghi `supported_models` từ danh sách model SỐNG (H8 Pha 2, làm mới model).

    Chuẩn hoá: bỏ rỗng, khử trùng, giữ thứ tự. Không đụng credential."""
    seen = set()
    out = []
    for m in (models or []):
        m = str(m).strip()
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    key.supported_models = out
    db.flush()


def lay_key_theo_id(db: DbSession, key_id: str) -> Optional[ApiKey]:
    return db.get(ApiKey, key_id)


def liet_ke(db: DbSession, *, provider: Optional[str] = None,
            category: Optional[str] = None) -> list:
    """Liệt kê key (không giải mã). Lọc theo provider/category nếu truyền."""
    stmt = select(ApiKey).order_by(ApiKey.provider, ApiKey.priority.desc())
    if provider:
        stmt = stmt.where(ApiKey.provider == provider.strip().lower())
    rows = list(db.execute(stmt).scalars().all())
    if category:
        rows = [k for k in rows if category in (k.categories or [])]
    return rows


def xoa_key(db: DbSession, key_id: str) -> bool:
    key = db.get(ApiKey, key_id)
    if key is None:
        return False
    db.delete(key)
    db.flush()
    return True
