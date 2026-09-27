"""
chia_se.py - chia se mot muc thu vien/tai nguyen bang MA (Q-10, spec S6.6).

Khong co trang "kho cong khai" - chi ai co MA moi xem/nhan duoc. Muc duoc chia
se van thuoc so huu cu; "nhan" tao MOT BAN SAO rieng cho nguoi nhan, khong
chuyen quyen so huu (giong clone_from_catalog cua library.py, nhung tong quat
cho ca cac loai da khai trong TARGET_KINDS thay vi chi rieng tung loai).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.tables import (
    OmmiMetaPrompt, OmmiPromptSnippet, OmmiStyle, OmmiShareCode)
from apps.prompt_ai_ommi.tables.nhan_vat import (
    OmmiCharacter, OmmiBackground, OmmiPose)

#: kind (nhu client goi) -> lop model. Bo sung image_template/
#: storyboard_framework/sample/profile o Task 14 (phu thuoc Task 12, Lan G -
#: chua xong luc Lan F thi hanh Task 6/7/8, xem bao cao cuoi).
TARGET_KINDS: dict[str, type] = {
    "meta_prompt": OmmiMetaPrompt,
    "style": OmmiStyle,
    "snippet": OmmiPromptSnippet,
    "character": OmmiCharacter,
    "background": OmmiBackground,
    "pose": OmmiPose,
}

_VALID_LEVELS = {"private", "code", "catalog"}


class ShareError(ValueError):
    """Du lieu vao khong hop le - route tra 400."""


class ShareNotFound(LookupError):
    """Khong ton tai HOAC khong thuoc ve nguoi goi - route tra 404."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _model(target_kind: str) -> type:
    model = TARGET_KINDS.get((target_kind or "").strip().lower())
    if model is None:
        raise ShareError(
            f"Loai chia se khong hop le: {target_kind!r}. "
            f"Chon mot trong: {', '.join(TARGET_KINDS)}.")
    return model


def _gen_code() -> str:
    return secrets.token_urlsafe(8)[:12]


def sinh_ma(db: Session, *, owner_id: str, target_kind: str, target_id: str,
           max_uses: int | None = None, expires_in_days: int | None = None
           ) -> OmmiShareCode:
    model = _model(target_kind)
    row = db.get(model, target_id)
    if row is None or getattr(row, "owner_id", None) != owner_id:
        raise ShareNotFound("Khong tim thay muc de chia se.")

    code = None
    for _ in range(5):
        candidate = _gen_code()
        exists = db.execute(
            select(OmmiShareCode.id).where(OmmiShareCode.code == candidate)
        ).first()
        if exists is None:
            code = candidate
            break
    if code is None:
        raise ShareError("Khong sinh duoc ma chia se, thu lai.")

    expires_at = (_now() + timedelta(days=int(expires_in_days))
                 if expires_in_days else None)
    share = OmmiShareCode(
        owner_id=owner_id, code=code, target_kind=target_kind.strip().lower(),
        target_id=target_id, max_uses=max_uses, expires_at=expires_at)
    db.add(share)
    db.flush()
    return share


def _load(db: Session, code: str) -> OmmiShareCode:
    share = db.execute(
        select(OmmiShareCode).where(OmmiShareCode.code == code)
    ).scalar_one_or_none()
    if share is None:
        raise ShareNotFound("Ma chia se khong ton tai.")
    return share


def thu_hoi(db: Session, *, code: str, owner_id: str, is_admin: bool = False
           ) -> OmmiShareCode:
    share = _load(db, code)
    if share.owner_id != owner_id and not is_admin:
        # Tra ve giong "khong tim thay" - khong lo cho nguoi la biet ma nay
        # co ton tai va thuoc ve ai.
        raise ShareNotFound("Ma chia se khong ton tai.")
    share.revoked_at = _now()
    db.flush()
    return share
