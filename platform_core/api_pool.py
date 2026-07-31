"""
api_pool.py — cấp phát API key (H8, Pha 1). App xin key ở đây theo (provider,
category, model); nền tảng chọn key khả dụng và đánh dấu lỗi để tự nghỉ/tắt.

KHÁC hàng đợi job: một API key CHIA SẺ được cho nhiều request đồng thời, nên
KHÔNG cần khoá độc quyền (`FOR UPDATE`) — chỉ chọn theo priority rồi cập nhật
trạng thái. Không tự commit (caller quyết định transaction).

Phân loại lỗi (học BOT GEMINI, đã kiểm chứng ở đó):
- 401/403 → auth_error; cooldown ngắn, DISABLE sau `AUTH_DISABLE_THRESHOLD` lần
  liên tiếp (chống một key hỏng làm chết mọi request);
- 429     → cooldown theo retry-after (mặc định `DEFAULT_COOLDOWN_S`);
- 4xx khác → LỖI CỦA TA (bad request) → KHÔNG phạt key;
- 5xx/mạng → error; sang trạng thái error sau nhiều lần.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from platform_core.models import (APIKEY_ACTIVE, APIKEY_COOLDOWN,
                                  APIKEY_DISABLED, APIKEY_ERROR, ApiKey)

AUTH_DISABLE_THRESHOLD = 5
DEFAULT_COOLDOWN_S = 60
ERROR_TO_STATUS_THRESHOLD = 5


class ThieuKeyError(Exception):
    """Không có API key khả dụng cho yêu cầu — app phải báo lỗi rõ, không gọi API."""


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def lay_key(db: DbSession, provider: str, *, category: Optional[str] = None,
            model: Optional[str] = None) -> ApiKey:
    """Chọn một API key khả dụng cho (provider[, category][, model]).

    Ưu tiên `priority` cao, rồi ít dùng nhất (`total_requests`). Tự hồi key hết
    cooldown. Raise `ThieuKeyError` nếu không có key nào dùng được.
    """
    provider = (provider or "").strip().lower()
    now = _bay_gio()
    rows = db.execute(
        select(ApiKey).where(ApiKey.provider == provider, ApiKey.enabled.is_(True))
    ).scalars().all()

    ung_vien = []
    for k in rows:
        # Tự hồi cooldown đã hết hạn.
        if k.status == APIKEY_COOLDOWN and k.cooldown_until and _aware(k.cooldown_until) <= now:
            k.status = APIKEY_ACTIVE
            k.cooldown_until = None
        if k.status != APIKEY_ACTIVE:
            continue
        if category and k.categories and category not in k.categories:
            continue
        if model and k.supported_models and model not in k.supported_models:
            continue
        ung_vien.append(k)

    if not ung_vien:
        raise ThieuKeyError(
            f"khong co API key kha dung: provider={provider} "
            f"category={category} model={model}")

    ung_vien.sort(key=lambda k: (-k.priority, k.total_requests))
    chon = ung_vien[0]
    chon.last_used_at = now
    chon.total_requests += 1
    db.flush()
    return chon


def danh_dau_thanh_cong(db: DbSession, key: ApiKey) -> None:
    key.total_success += 1
    key.error_count = 0
    key.auth_error_count = 0
    key.health_score = min(100, key.health_score + 5)
    if key.status == APIKEY_ERROR:
        key.status = APIKEY_ACTIVE
    db.flush()


def danh_dau_loi(db: DbSession, key: ApiKey, *, http_status: Optional[int] = None,
                 retry_after_s: Optional[int] = None, message: str = "") -> None:
    key.total_failed += 1
    key.last_error = (message or "")[:500]
    s = http_status

    if s in (401, 403):
        key.auth_error_count += 1
        key.health_score = max(0, key.health_score - 10)
        if key.auth_error_count >= AUTH_DISABLE_THRESHOLD:
            key.status = APIKEY_DISABLED       # hỏng thật -> tắt hẳn, chờ admin
        else:
            key.status = APIKEY_COOLDOWN       # có thể chỉ trục trặc tạm
            key.cooldown_until = _bay_gio() + timedelta(seconds=DEFAULT_COOLDOWN_S)
    elif s == 429:
        cd = int(retry_after_s) if retry_after_s else DEFAULT_COOLDOWN_S
        key.status = APIKEY_COOLDOWN
        key.cooldown_until = _bay_gio() + timedelta(seconds=cd)
        key.health_score = max(0, key.health_score - 5)
    elif s is not None and 400 <= s < 500:
        # Bad request CỦA TA — không phải lỗi của key. KHÔNG phạt.
        pass
    else:
        # 5xx hoặc lỗi mạng.
        key.error_count += 1
        key.health_score = max(0, key.health_score - 10)
        if key.error_count >= ERROR_TO_STATUS_THRESHOLD:
            key.status = APIKEY_ERROR
    db.flush()
