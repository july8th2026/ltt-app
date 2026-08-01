"""
api_pool.py — cấp phát API key (H8). App xin key ở đây theo (provider, category,
model); nền tảng chọn key khả dụng, đếm tải (rpm/tpm/token) và đánh dấu lỗi để tự
nghỉ/tắt.

KHÁC hàng đợi job: một API key CHIA SẺ được cho nhiều request đồng thời, nên
KHÔNG cần khoá độc quyền (`FOR UPDATE`) — chỉ chọn theo priority rồi cập nhật
trạng thái. Không tự commit (caller quyết định transaction).

Pha 2 thêm:
- **Telemetry rpm/tpm/token** — cửa sổ cố định 60s ngay trong hàng: allocator bỏ
  qua key đã chạm `rpm_limit`/`tpm_limit` trong cửa sổ hiện tại, tự reset khi quá
  hạn. `danh_dau_thanh_cong(..., tokens=)` kế toán token.
- **Cascade đa-provider** — `chon_key(category=..., thu_tu_provider=[...])` gom key
  MỌI provider phục vụ category, nên một provider cạn key KHÔNG làm chết cả loại.

Phân loại lỗi (học BOT GEMINI, đã kiểm chứng ở đó):
- 401/403 → auth_error; cooldown ngắn, DISABLE sau `AUTH_DISABLE_THRESHOLD` lần
  liên tiếp (chống một key hỏng làm chết mọi request);
- 429     → cooldown theo retry-after (mặc định `DEFAULT_COOLDOWN_S`);
- 4xx khác → LỖI CỦA TA (bad request) → KHÔNG phạt key;
- 5xx/mạng → error; sang trạng thái error sau nhiều lần.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from platform_core.models import (APIKEY_ACTIVE, APIKEY_COOLDOWN,
                                  APIKEY_DISABLED, APIKEY_ERROR, ApiKey)

AUTH_DISABLE_THRESHOLD = 5
DEFAULT_COOLDOWN_S = 60
ERROR_TO_STATUS_THRESHOLD = 5
WINDOW_S = 60          # cửa sổ đo rpm/tpm (giây)


class ThieuKeyError(Exception):
    """Không có API key khả dụng cho yêu cầu — app phải báo lỗi rõ, không gọi API."""


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _cuon_cua_so(key: ApiKey, now: datetime) -> None:
    """Reset cửa sổ đếm khi đã quá `WINDOW_S`. Gọi trước khi đọc/tăng bộ đếm."""
    ws = _aware(key.window_start)
    if ws is None or (now - ws).total_seconds() >= WINDOW_S:
        key.window_start = now
        key.window_requests = 0
        key.window_tokens = 0


def _dinh_muc_con(key: ApiKey) -> bool:
    """True nếu key CÒN quota trong cửa sổ hiện tại (đã cuộn cửa sổ trước khi gọi)."""
    if key.rpm_limit and key.window_requests >= key.rpm_limit:
        return False
    if key.tpm_limit and key.window_tokens >= key.tpm_limit:
        return False
    return True


def _ung_vien(db: DbSession, now: datetime, *, providers: Optional[Sequence[str]],
              category: Optional[str], model: Optional[str]) -> list:
    """Gom key khả dụng (tự hồi cooldown + cuộn cửa sổ). Lọc provider/category/model
    và bỏ key đã chạm rpm/tpm. KHÔNG sắp xếp — caller quyết thứ tự."""
    stmt = select(ApiKey).where(ApiKey.enabled.is_(True))
    if providers:
        stmt = stmt.where(ApiKey.provider.in_(list(providers)))
    rows = db.execute(stmt).scalars().all()

    out = []
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
        _cuon_cua_so(k, now)
        if not _dinh_muc_con(k):
            continue          # đã chạm rpm/tpm trong cửa sổ này -> tạm bỏ
        out.append(k)
    return out


def chon_key(db: DbSession, *, category: Optional[str] = None,
             model: Optional[str] = None,
             thu_tu_provider: Optional[Sequence[str]] = None) -> ApiKey:
    """Chọn một API key khả dụng cho `category` (tuỳ `model`), CASCADE nhiều provider.

    `thu_tu_provider`: thứ tự ưu tiên provider (vd ["gemini","apiai"]); None = xét
    mọi provider. Xếp: provider theo thứ tự cho trước → `priority` cao → `health`
    cao → ít tải nhất (cửa sổ) → ít dùng nhất. Raise `ThieuKeyError` nếu cạn.
    """
    order = [(p or "").strip().lower() for p in (thu_tu_provider or []) if p]
    now = _bay_gio()
    ung_vien = _ung_vien(db, now, providers=(order or None),
                         category=category, model=model)
    if not ung_vien:
        raise ThieuKeyError(
            f"khong co API key kha dung: providers={order or 'moi'} "
            f"category={category} model={model}")

    def _rank_prov(p: str) -> int:
        if not order:
            return 0
        try:
            return order.index(p)
        except ValueError:
            return len(order)

    ung_vien.sort(key=lambda k: (_rank_prov(k.provider), -k.priority,
                                 -k.health_score, k.window_requests, k.total_requests))
    chon = ung_vien[0]
    chon.last_used_at = now
    chon.total_requests += 1
    _cuon_cua_so(chon, now)      # bảo đảm cửa sổ hợp lệ trước khi tăng
    chon.window_requests += 1
    db.flush()
    return chon


def lay_key(db: DbSession, provider: str, *, category: Optional[str] = None,
            model: Optional[str] = None) -> ApiKey:
    """Chọn key cho MỘT provider cụ thể (tương thích Pha 1). Nội bộ gọi `chon_key`
    với thứ tự provider = [provider], nên rpm/tpm/telemetry áp dụng như nhau."""
    provider = (provider or "").strip().lower()
    return chon_key(db, category=category, model=model, thu_tu_provider=[provider])


def danh_dau_thanh_cong(db: DbSession, key: ApiKey, *, tokens: int = 0) -> None:
    key.total_success += 1
    key.error_count = 0
    key.auth_error_count = 0
    key.health_score = min(100, key.health_score + 5)
    if tokens:
        now = _bay_gio()
        _cuon_cua_so(key, now)
        key.window_tokens += int(tokens)
        key.total_tokens += int(tokens)
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


def rpm(key: ApiKey, *, now: Optional[datetime] = None) -> int:
    """Số request trong cửa sổ 60s hiện tại (0 nếu cửa sổ đã cũ)."""
    now = now or _bay_gio()
    ws = _aware(key.window_start)
    if ws is None or (now - ws).total_seconds() >= WINDOW_S:
        return 0
    return key.window_requests


def tpm(key: ApiKey, *, now: Optional[datetime] = None) -> int:
    """Số token trong cửa sổ 60s hiện tại (0 nếu cửa sổ đã cũ)."""
    now = now or _bay_gio()
    ws = _aware(key.window_start)
    if ws is None or (now - ws).total_seconds() >= WINDOW_S:
        return 0
    return key.window_tokens
