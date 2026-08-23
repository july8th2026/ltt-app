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


def _chuan_hoa_categories(categories, provider: str = "") -> list:
    """Chuẩn hoá + kiểm category, và kiểm CẢ việc provider có phục vụ nó không.

    ⛔ SỰ CỐ THẬT 2026-08-23. Khoá `ltt_image` được tạo với category
    `model_control`. Nó hợp lệ về mặt danh sách, nên form nhận. Nhưng provider
    `ltt_image` chỉ khai `('image',)`, nên `api_pool` **không bao giờ cấp phát
    nó** — và lỗi báo ra là `ThieuKeyError: khong co API key kha dung`, tức là
    *"không có khoá nào"*, chứ không phải *"khoá có nhưng sai category"*.

    Người vận hành nhìn thấy khoá nằm sờ sờ trong danh sách mà hệ thống bảo
    không có khoá. Và vì **không có đường sửa `categories` từ giao diện**, cách
    duy nhất để chữa là **xoá khoá đi tạo lại** — mất sạch lịch sử của nó.

    Provider đã khai sẵn `categories`. Không dùng dữ liệu đó để chặn từ đầu là
    để một lỗi gõ nhầm đi thẳng vào CSDL rồi hỏng ở một chỗ cách xa nguyên nhân.
    """
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

    if provider and out:
        from platform_core import providers as _p
        prov = _p.get((provider or "").strip().lower())
        # Provider không khai gì thì không chặn — chỗ này kiểm một lời khai, và
        # không có lời khai thì không có gì để kiểm.
        phuc_vu = tuple(getattr(prov, "categories", ()) or ()) if prov else ()
        if phuc_vu:
            la = [c for c in out if c not in phuc_vu]
            if la:
                raise ApiKeyError(
                    f"provider {provider!r} khong phuc vu category "
                    f"{', '.join(la)} — no chi phuc vu: {', '.join(phuc_vu)}")
    return out


def categories_goi_y(provider: str) -> list:
    """Category mà provider này phục vụ. Dùng để tick sẵn trên form thêm khoá."""
    from platform_core import providers as _p
    prov = _p.get((provider or "").strip().lower())
    return list(getattr(prov, "categories", ()) or ()) if prov else []


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
        categories=_chuan_hoa_categories(categories, provider),
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


def cap_nhat_categories(db: DbSession, key: ApiKey, categories) -> None:
    """Đổi `categories` của một khoá, **giữ nguyên id và toàn bộ lịch sử**.

    ⭐ Vì sao cần hàm này chứ không phải "xoá đi tạo lại": khoá mang
    `total_requests`, `total_success`, `health_score`, `last_used_at` — và một id
    mà nhật ký vận hành đang tham chiếu. Tạo lại là **mất hết**, chỉ vì tick nhầm
    một ô.
    """
    from sqlalchemy.orm.attributes import flag_modified

    key.categories = _chuan_hoa_categories(categories, key.provider)
    # Cột JSON: không đánh dấu thì SQLAlchemy không thấy thay đổi và lặng lẽ bỏ qua.
    flag_modified(key, "categories")
    db.flush()


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
