"""Dependency plumbing for ``/api/v1``: kill switches, body cap, principal hook.

The authorization *rules* live in ``platform_core.public_api.principal``; the
credential *verification* lives in ``server/api/auth.py``. This module only
holds the seam between them, so a test can swap in a fake resolver without a
database and production can install the real one exactly once.

Two boundaries are enforced here rather than documented and hoped for:

* a principal is resolved from ``Authorization: Bearer`` **only**. Cookies and
  ``request.session`` are never read on this surface. A browser that is logged
  in must not be able to spend a customer's credit because another site made it
  issue a request — there is no CSRF token here to fall back on, and adding one
  would be meaningless for a machine API;
* with no resolver installed, every authenticated route answers 401. Fail-closed
  beats a helpful stub that quietly lets requests through.
"""
from __future__ import annotations

from typing import Callable, Optional

from platform_core.public_api import errors
from platform_core.public_api.config import PublicApiConfig
from platform_core.public_api.principal import Principal

_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_BEARER_PREFIX = "bearer "

# A resolver turns (request, db) into a Principal, or None when the credential
# is absent/invalid. ``server/api/auth.py`` installs the database-backed one.
PrincipalResolver = Callable[[object, object], Optional[Principal]]

_resolver: Optional[PrincipalResolver] = None


def set_principal_resolver(resolver: Optional[PrincipalResolver]) -> None:
    """Install the credential verifier. ``None`` restores the deny-all default."""
    global _resolver
    _resolver = resolver


def current_resolver() -> Optional[PrincipalResolver]:
    return _resolver


def bearer_token(request) -> str:
    """The raw token from ``Authorization: Bearer``; empty when absent.

    Never logged and never echoed: callers get the value only to verify it.
    """
    header = request.headers.get("authorization") or ""
    if header[:7].lower() != _BEARER_PREFIX:
        return ""
    return header[7:].strip()


def resolve_principal(request, db=None) -> Principal:
    """Resolve the caller or raise 401. Cookies are ignored on purpose."""
    resolver = _resolver
    if resolver is None:
        raise errors.unauthorized("API authentication is not enabled.")
    principal = resolver(request, db)
    if principal is None:
        raise errors.unauthorized("Invalid or missing API credential.")
    return principal


# Kept as the historical name used by Prompt 02's tests and docs.
require_principal = resolve_principal


def enforce_read_only(request, config: PublicApiConfig) -> None:
    """Emergency switch: reads keep working, writes are refused with 503."""
    if config.read_only and request.method.upper() in _WRITE_METHODS:
        raise errors.read_only(
            "The API is temporarily read-only; write operations are paused.")


def enforce_body_limit(request, config: PublicApiConfig) -> None:
    """Reject an oversized control-plane body from its declared length.

    Checking ``Content-Length`` rejects before the body is read, which is the
    point: the alternative is buffering whatever the caller decided to send.
    A missing/garbled header is treated as oversized rather than trusted — a
    chunked upload has no business on a JSON control-plane route.
    """
    if request.method.upper() not in _WRITE_METHODS:
        return
    raw = request.headers.get("content-length")
    if raw is None:
        if request.headers.get("transfer-encoding", "").lower() == "chunked":
            raise errors.payload_too_large(
                "A declared Content-Length is required on this endpoint.")
        return
    try:
        declared = int(raw)
    except (TypeError, ValueError) as exc:
        raise errors.invalid_request("Content-Length is not a number.") from exc
    if declared > config.max_body_bytes:
        # 🔴 XƯNG TÊN TRẦN. Ngày 30/08 bốn trần khác nhau (body-bytes, token
        #    vào, token ra, cửa sổ ngữ cảnh) từng CÙNG trả 413, và không trần
        #    nào tự xưng tên — bên gọi, và cả người sửa lỗi, phải đoán.
        #
        # ⛔ CẬP NHẬT 22/09 (R-08, `server/api/su_kien_loi.py`): ba trần TOKEN
        #    (vào/ra/ngữ cảnh) đã CHUYỂN sang HTTP 400 với câu đúng khuôn
        #    client thật đọc được (`prompt is too long: N tokens > M maximum`,
        #    `limit_name="input_tokens"`) để Claude Code/Codex tự nén — client
        #    thật không nhận ra 413 cho lỗi token (xem tài liệu ở đó). CHỈ còn
        #    ĐÚNG MỘT trần trả 413 thật: body-bytes, ở đây. Đoạn chú thích cũ
        #    nói "bốn trần cùng 413" không còn đúng mã đang chạy — giữ lại vì
        #    lịch sử, nhưng đừng lần theo nó để tìm trần token: nó không ở 413.
        raise errors.payload_too_large(
            "Request body exceeds the limit for this endpoint.",
            limit_name="body_bytes",
            limit_value=config.max_body_bytes,
            observed=declared,
            limit_bytes=config.max_body_bytes)


__all__ = ["Principal", "PrincipalResolver", "bearer_token", "current_resolver",
           "enforce_body_limit", "enforce_read_only", "require_principal",
           "resolve_principal", "set_principal_resolver"]
