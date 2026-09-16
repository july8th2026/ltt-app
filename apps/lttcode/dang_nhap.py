"""Đăng nhập LTT Studios cho ứng dụng desktop LTTCODE (PKCE S256 + loopback).

Luồng (spec LTTCODEAPP `docs/LTTCODE/specs/2026-09-17-dang-nhap-lttcode-design.md`):
trình duyệt đã đăng nhập bấm Cho phép → `tao_ma` → ứng dụng gửi mã + verifier →
`doi_ma` → `cap_khoa` (một khoá `ltt_sk_` riêng cho máy đó, thu hồi được ở
Developers › Keys).

Mọi lý do `doi_ma` từ chối (mã sai, hết hạn, đã dùng, sai port, sai verifier)
trả CÙNG `None`: phân biệt được là cho kẻ dò biết mình đang tới gần. Mã bị tiêu
TRƯỚC khi so verifier, nên một mã lộ không cho thử verifier lần hai.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update

from apps.lttcode.tables import LttcodeAuthCode
from platform_core.public_api import keys as devkeys
from platform_core.public_api import projects
from platform_core.public_api.scopes import SCOPE_JOBS_CREATE, SCOPE_JOBS_READ, SCOPE_TOOLS_READ

HAN_MA_S = 120
HAN_KHOA = timedelta(days=365)
LUOT_TOKEN_MOI_PHUT = 10
SCOPES_KHOA = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ)
TIEN_TO_TEN_KHOA = "LTTCODE – "

_STATE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_CHALLENGE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_KY_TU_MAY = re.compile(r"[^A-Za-z0-9 ._-]")


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


def _utc(t: datetime) -> datetime:
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def s256(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii", "replace")).digest()).rstrip(b"=").decode()


def _digest(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8", "replace")).hexdigest()


def kiem_tham_so(port: str, state: str, challenge: str, method: str,
                 device: str) -> tuple[int, str, str, str] | None:
    """Chuẩn hoá tham số của `/authorize`; `None` khi bất kỳ tham số nào sai."""
    try:
        cong = int(port)
    except (TypeError, ValueError):
        return None
    if not (1024 <= cong <= 65535) or method != "S256":
        return None
    if not _STATE.match(state or "") or not _CHALLENGE.match(challenge or ""):
        return None
    may = " ".join(_KY_TU_MAY.sub("", device or "").split())[:48].strip() or "PC"
    return cong, state, challenge, may


def url_loopback(port: int, **tham_so: str) -> str:
    from urllib.parse import urlencode
    return f"http://127.0.0.1:{port}/callback?{urlencode(tham_so)}"


def don_ma_het_han(db, *, now: datetime | None = None) -> int:
    """Xoá mã đã hết hạn quá một giờ. Trả số dòng đã xoá. Không commit.

    Gọi ở hai chỗ: `tao_ma` (mỗi lượt đăng nhập) và `bao_tri.chay` (mỗi giờ) —
    không có lượt đăng nhập nào thì chỉ còn đường thứ hai (governance.STORES).
    """
    now = now or _bay_gio()
    kq = db.execute(delete(LttcodeAuthCode)
                    .where(LttcodeAuthCode.expires_at < now - timedelta(hours=1)))
    return int(getattr(kq, "rowcount", 0) or 0)


def tao_ma(db, *, user_id: str, challenge: str, port: int, device: str) -> str:
    now = _bay_gio()
    don_ma_het_han(db, now=now)
    code = secrets.token_urlsafe(32)
    db.add(LttcodeAuthCode(
        id=str(uuid.uuid4()), code_digest=_digest(code), user_id=str(user_id),
        code_challenge=challenge, port=int(port), device=device[:64],
        created_at=now, expires_at=now + timedelta(seconds=HAN_MA_S), used_at=None))
    db.flush()
    return code


def doi_ma(db, *, code: object, verifier: object, port: int) -> tuple[str, str] | None:
    """Tiêu mã rồi mới kiểm verifier. Trả `(user_id, device)` hoặc `None`."""
    if not isinstance(code, str) or not isinstance(verifier, str) or not code or len(code) > 256:
        return None
    now = _bay_gio()
    row = db.execute(select(LttcodeAuthCode).where(
        LttcodeAuthCode.code_digest == _digest(code))).scalar_one_or_none()
    if row is None or row.used_at is not None or _utc(row.expires_at) <= now:
        return None
    # Một câu UPDATE có điều kiện: hai request cùng lúc thì chỉ một cái đếm được 1.
    tieu = db.execute(update(LttcodeAuthCode)
                      .where(LttcodeAuthCode.id == row.id, LttcodeAuthCode.used_at.is_(None))
                      .values(used_at=now))
    if (tieu.rowcount or 0) != 1:
        return None
    if row.port != port or not hmac.compare_digest(row.code_challenge, s256(verifier)):
        return None
    return row.user_id, row.device


def cap_khoa(db, *, user_id: str, device: str):
    """Khoá `ltt_sk_` riêng cho máy — trả `(row, plaintext)`; plaintext chỉ có lúc này."""
    project = projects.default_for(db, user_id=user_id)
    return devkeys.issue(
        db, user_id=user_id, name=(TIEN_TO_TEN_KHOA + device)[:120], scopes=SCOPES_KHOA,
        project_id=project.id, expires_at=_bay_gio() + HAN_KHOA, mode="live")
