"""Nhan vat / trang phuc / dang / boi canh, va buoc KHOA.

⭐ Buoc khoa la manh PROMPT AI dang thieu, va la goc cua viec nhat quan nhan vat
   xuyen canh. No den tu `apps/prompt_canh` (buoc 1: character_lock) -- app do
   se duoc xem xet xoa o Task E5 SAU KHI buoc nay chay dung va co doi chung
   (spec X-5). ⛔ Task E5 KHONG nam trong pham vi lan nay.

⚠️ `apps/prompt_canh` that ra la MOT CHUOI BA BUOC (khoa nhan vat -> liet ke
   canh -> JSON prompt tung canh, xem `services/kich_ban.py`), khong chi mot
   buoc khoa nhan vat. Module nay CHI mang buoc 1 (khoa nhan vat/boi canh,
   nhap tay tung nhan vat) sang -- day la mot thiet ke lai co CHU Y theo
   spec Sec 6.5 (CRUD + nut khoa cho tung nhan vat), khong phai mot ban port
   ca chuoi. Xem bao cao E4 de biet nang luc nao CHUA co mat.
"""
from __future__ import annotations

import pathlib

from sqlalchemy import select

from platform_core.i18n import _ as _t
from apps.prompt_ai_ommi.services import placeholders as ph
from apps.prompt_ai_ommi.tables import (OmmiBackground, OmmiCharacter,
                                        OmmiOutfit, OmmiPose)

_LOI_NHAC = (pathlib.Path(__file__).resolve().parents[1]
             / "prompts" / "khoa_nhan_vat.txt")

_TRUONG_CHU = ("gender", "age_range", "face_description", "body_description",
               "hair_description", "outfit_description", "personality",
               "expression_style", "movement_style", "fixed_prompt_block",
               "negative_notes")


def tao(db, owner_id: str, du_lieu: dict) -> OmmiCharacter:
    row = OmmiCharacter(owner_id=owner_id,
                        name=str(du_lieu.get("name") or "")[:160])
    db.add(row)
    return sua(db, row, du_lieu)


def sua(db, row: OmmiCharacter, du_lieu: dict) -> OmmiCharacter:
    if "name" in du_lieu:
        row.name = str(du_lieu["name"] or "")[:160]
    for ten in _TRUONG_CHU:
        if ten in du_lieu:
            setattr(row, ten, str(du_lieu[ten] or ""))
    if "reference_variant_ids" in du_lieu:
        row.reference_variant_ids = [
            str(x) for x in list(du_lieu["reference_variant_ids"] or [])[:40]]
    return row


def doc(db, cid: str, owner_id: str) -> OmmiCharacter:
    row = db.get(OmmiCharacter, str(cid or ""))
    if row is None or row.owner_id != owner_id:
        raise KeyError(cid)
    return row


def liet_ke(db, owner_id: str) -> list[OmmiCharacter]:
    return list(db.execute(
        select(OmmiCharacter).where(OmmiCharacter.owner_id == owner_id,
                                    OmmiCharacter.archived_at.is_(None))
        .order_by(OmmiCharacter.updated_at.desc())).scalars())


def tao_boi_canh(db, owner_id: str, du_lieu: dict) -> OmmiBackground:
    row = OmmiBackground(owner_id=owner_id,
                         name=str(du_lieu.get("name") or "")[:160])
    db.add(row)
    for ten in ("location_type", "environment_description",
                "lighting_description", "color_palette", "camera_feel",
                "important_objects", "fixed_prompt_block", "negative_notes"):
        if ten in du_lieu:
            setattr(row, ten, str(du_lieu[ten] or ""))
    return row


def doc_boi_canh(db, bid: str, owner_id: str) -> OmmiBackground:
    row = db.get(OmmiBackground, str(bid or ""))
    if row is None or row.owner_id != owner_id:
        raise KeyError(bid)
    return row


def liet_ke_boi_canh(db, owner_id: str) -> list[OmmiBackground]:
    return list(db.execute(
        select(OmmiBackground).where(OmmiBackground.owner_id == owner_id,
                                     OmmiBackground.archived_at.is_(None))
        .order_by(OmmiBackground.updated_at.desc())).scalars())


def tao_trang_phuc(db, character_id: str, du_lieu: dict) -> OmmiOutfit:
    """`owner_id` TRA TU nhan vat, ⛔ khong nhan qua tham so.

    Nhan qua tham so la mot cho de truyen SAI chu, va mot hang sai chu trong
    bang nay thi moi phep loc theo owner se bo qua no hoac tra no cho nguoi
    khac. Tra tu chinh nhan vat thi hai gia tri KHONG THE lech nhau.
    Nhan vat khong ton tai => no ngay, ⛔ khong tao hang mo coi.
    """
    chu = db.execute(select(OmmiCharacter.owner_id)
                     .where(OmmiCharacter.id == character_id)).scalar()
    if not chu:
        raise KeyError(character_id)
    row = OmmiOutfit(owner_id=chu, character_id=character_id,
                     name=str(du_lieu.get("name") or "")[:160],
                     description=str(du_lieu.get("description") or ""))
    if "reference_variant_ids" in du_lieu:
        row.reference_variant_ids = [
            str(x) for x in list(du_lieu["reference_variant_ids"] or [])[:40]]
    db.add(row)
    return row


def liet_ke_trang_phuc(db, character_id: str) -> list[OmmiOutfit]:
    return list(db.execute(
        select(OmmiOutfit).where(OmmiOutfit.character_id == character_id)
        .order_by(OmmiOutfit.created_at.desc())).scalars())


def tao_dang(db, owner_id: str, du_lieu: dict) -> OmmiPose:
    row = OmmiPose(owner_id=owner_id, name=str(du_lieu.get("name") or "")[:160],
                   description=str(du_lieu.get("description") or ""),
                   pose_block=str(du_lieu.get("pose_block") or ""))
    if "tags" in du_lieu:
        row.tags = [str(x) for x in list(du_lieu["tags"] or [])[:20]]
    if "reference_variant_ids" in du_lieu:
        row.reference_variant_ids = [
            str(x) for x in list(du_lieu["reference_variant_ids"] or [])[:40]]
    db.add(row)
    return row


def liet_ke_dang(db, owner_id: str) -> list[OmmiPose]:
    return list(db.execute(
        select(OmmiPose).where(OmmiPose.owner_id == owner_id)
        .order_by(OmmiPose.created_at.desc())).scalars())


def _gia_tri_khoa(params: dict) -> dict:
    """Bien cua `prompts/khoa_nhan_vat.txt`. Them bien ⇒ sua CA HAI cho."""
    return {
        "NAME": params.get("name"), "GENDER": params.get("gender"),
        "AGE_RANGE": params.get("age_range"),
        "FACE": params.get("face_description"),
        "BODY": params.get("body_description"),
        "HAIR": params.get("hair_description"),
        "OUTFIT": params.get("outfit_description"),
        "PERSONALITY": params.get("personality"),
        "EXPRESSION": params.get("expression_style"),
        "MOVEMENT": params.get("movement_style"),
        "NEGATIVE_NOTES": params.get("negative_notes") or "khong co",
    }


def chay_khoa_nhan_vat(params: dict, ctx=None) -> dict:
    """Than job cho `operation="character_lock"`.

    ⛔ PHAI nem exception khi loi -- nen tang dua vao exception de hoan credit
       (spec G-9). Dung tra rong hay `{}` roi coi nhu "xong".
    """
    from apps.prompt_ai_ommi import provider

    if not str(params.get("name") or "").strip():
        raise ValueError(_t('Cần tên nhân vật.'))
    if not str(params.get("face_description") or "").strip():
        raise ValueError(_t('Cần mô tả khuôn mặt để khoá nhân vật.'))
    body = _LOI_NHAC.read_text(encoding="utf-8")
    gia_tri = _gia_tri_khoa(params)
    thieu = ph.kiem_placeholder(body, list(gia_tri), gia_tri)
    if thieu:
        raise ValueError(_t('Thiếu thông tin: ') + ", ".join(thieu))
    loi_nhac = ph.render(body, gia_tri)
    if ctx is not None:
        ctx.progress(30, _t('đang khoá nhân vật'))
    model = str(params.get("model") or provider.model_mac_dinh())
    raw, tokens = provider.generate_json(
        "Ban la chuyen gia thiet ke nhan vat cho phim.", loi_nhac, model=model)
    khoi = str((raw or {}).get("fixed_prompt_block") or "").strip()
    if not khoi:
        raise ValueError(_t('AI không trả khối mô tả nhân vật.'))
    if ctx is not None:
        ctx.progress(100, _t('hoàn tất'))
    return {"operation": "character_lock", "fixed_prompt_block": khoi,
            "negative_notes": str((raw or {}).get("negative_notes") or ""),
            "tokens_used": tokens, "model": model}
