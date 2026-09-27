"""
chia_se.py - chia se mot muc thu vien/tai nguyen bang MA (Q-10, spec S6.6).

Khong co trang "kho cong khai" - chi ai co MA moi xem/nhan duoc. Muc duoc chia
se van thuoc so huu cu; "nhan" tao MOT BAN SAO rieng cho nguoi nhan, khong
chuyen quyen so huu (giong clone_from_catalog cua library.py, nhung tong quat
cho ca cac loai da khai trong TARGET_KINDS thay vi chi rieng tung loai).
"""
from __future__ import annotations

import secrets
from typing import Any
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.tables import (
    OmmiMetaPrompt, OmmiPromptSnippet, OmmiStyle, OmmiShareCode,
    OmmiImageTemplate, OmmiStoryboardFramework, OmmiSample, OmmiProfile)
from apps.prompt_ai_ommi.tables.nhan_vat import (
    OmmiCharacter, OmmiBackground, OmmiPose)

#: kind (nhu client goi) -> lop model. 10 loai, HAI hinh dang chu so huu khac
#: nhau (Task 14, doc tu migration b64a39da941d + services/nhap_mau_goc.py,
#: KHONG doan theo plan):
#:   - meta_prompt/snippet/style: co CU, owner_id NULLABLE - catalog la
#:     owner_id IS NULL (khong dung toi trong module nay, chi library.py).
#:   - character/background/pose: owner_id NOT NULL (Pha 3), khong co catalog
#:     rieng - da co share_level tu truoc.
#:   - image_template/storyboard_framework/sample/profile: owner_id NOT NULL
#:     (bang MOI, Pha 4) - catalog la is_builtin=True + share_level="catalog",
#:     KHONG PHAI owner_id NULL (cot nay khong cho NULL).
#: Moi ham trong tep nay (sinh_ma/thu_hoi/dat_muc_chia_se) chi so sanh
#: `row.owner_id == owner_id` cua NGUOI GOI - dung cho CA HAI hinh dang vi
#: khong ai (ke ca None) trung owner_id that cua mot nguoi dung that, nen
#: khong can nhanh rieng theo hinh dang o day. Nhung `_model()` PHAI no (raise
#: ShareError) tren mot kind la, ⛔ khong duoc `continue`/tra rong - xem
#: test_5414 doi chung ca 10 khoa deu tro dung lop, va hai "khoa la" (rong,
#: sai chinh ta) deu bi tu choi thay vi bi bo qua.
TARGET_KINDS: dict[str, type] = {
    "meta_prompt": OmmiMetaPrompt,
    "style": OmmiStyle,
    "snippet": OmmiPromptSnippet,
    "character": OmmiCharacter,
    "background": OmmiBackground,
    "pose": OmmiPose,
    "image_template": OmmiImageTemplate,
    "storyboard_framework": OmmiStoryboardFramework,
    "sample": OmmiSample,
    "profile": OmmiProfile,
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


def _kiem_con_hieu_luc(share: OmmiShareCode) -> None:
    if share.revoked_at is not None:
        raise ShareError("Ma chia se da bi thu hoi.")
    if share.expires_at is not None and share.expires_at <= _now():
        raise ShareError("Ma chia se da het han.")


def xem_truoc(db: Session, *, code: str) -> dict:
    share = _load(db, code)
    _kiem_con_hieu_luc(share)
    model = TARGET_KINDS.get(share.target_kind)
    row = db.get(model, share.target_id) if model else None
    if row is None:
        raise ShareNotFound("Muc duoc chia se khong con ton tai.")
    return {
        "target_kind": share.target_kind,
        "name": getattr(row, "name", getattr(row, "title", "")),
        "uses": share.uses,
        "max_uses": share.max_uses,
        "expires_at": share.expires_at.isoformat() if share.expires_at else None,
    }


#: Cot he thong khong duoc sao khi clone - moi ban sao la BAN GHI MOI, doc lap.
_SYSTEM_COLUMNS = {
    "id", "owner_id", "created_at", "updated_at", "archived_at",
    "deprecated_at", "deprecated_note", "cloned_from_id", "version",
    "is_catalog", "is_builtin", "use_count", "share_level",
}


def _clone_row(model: Any, source, owner_id: str):
    """`model: Any` co y: day la mot lop SQLAlchemy DA MAP, va `__table__` chi
    ton tai sau khi declarative base map no. `type` tran thi mypy khong thay
    `__table__`; mot `Protocol` phu `Table` la nhieu may moc hon mot cho dung
    duy nhat xung dang."""
    data = {col.name: getattr(source, col.name) for col in model.__table__.columns
           if col.name not in _SYSTEM_COLUMNS}
    row = model(owner_id=owner_id, **data)
    if hasattr(row, "share_level"):
        row.share_level = "private"
    if hasattr(row, "cloned_from_id"):
        row.cloned_from_id = source.id
    return row


def nhan(db: Session, *, code: str, owner_id: str):
    share = _load(db, code)
    _kiem_con_hieu_luc(share)
    if share.max_uses is not None and share.uses >= share.max_uses:
        raise ShareError("Ma chia se da dung het luot.")
    model = TARGET_KINDS.get(share.target_kind)
    if model is None:
        raise ShareError(f"Loai chia se khong duoc ho tro: {share.target_kind!r}.")
    source = db.get(model, share.target_id)
    if source is None:
        raise ShareNotFound("Muc duoc chia se khong con ton tai.")
    copy = _clone_row(model, source, owner_id)
    db.add(copy)
    share.uses = int(share.uses or 0) + 1
    db.flush()
    return copy


def dat_muc_chia_se(db: Session, *, target_kind: str, item_id: str, owner_id: str,
                    is_admin: bool, level: str):
    if level not in _VALID_LEVELS:
        raise ShareError(f"Muc chia se khong hop le: {level!r}.")
    if level == "catalog" and not is_admin:
        raise ShareError("Chi admin duoc dat muc 'catalog'.")
    model = _model(target_kind)
    row = db.get(model, item_id)
    if row is None or (row.owner_id != owner_id and not is_admin):
        raise ShareNotFound("Khong tim thay muc.")
    row.share_level = level
    if hasattr(row, "updated_at"):
        row.updated_at = _now()
    db.flush()
    return row
