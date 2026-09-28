"""
nhap_mau_goc.py - nhap 12 meta prompt + 13 snippet + 21 image template + 5
storyboard framework tu Prompt Seedance Studio vao catalog PROMPT AI.

Nguon la 4 tep JSON tinh dong goi cung code (prompts/mau_goc/*.json) - khong
doc CSDL/dia cua BOT GEMINI luc chay (tach hoan toan khoi kho CHI DOC do; xem
<scratchpad>/xuat_mau_goc.py da chay MOT LAN thu cong de tao 4 tep nay, ket
qua la du lieu tinh, khong phai ma san pham).

So dem da xac nhan TRUC TIEP tren ban sao Studio (27/09/2026, doc lap voi con
so trong plan): meta_prompts=12, prompt_snippets (loai snippet-%%)=13,
image_gen_templates (is_builtin=1)=21 (7 character/7 prop/7 background -
KHONG PHAI 7/8/9=24 nhu mot bao cao cu ghi), storyboard_frameworks
(is_builtin=1)=5.

Idempotent (R-3, spec S8.1), theo khoa rieng cho tung loai vi cac bang khong
dung chung mot co che catalog:
  - meta_prompt: (owner_id IS NULL, target_format, name) - dung dung khoa R-3
    ("idempotent theo (target_format, name)"), them dieu kien owner_id IS
    NULL vi day la co che catalog CU cua bang nay (khac 4 bang moi ben duoi).
  - snippet: (owner_id IS NULL, name) - snippet khong co cot target_format
    nen khong ap dung duoc khoa nguyen van cua R-3; dung ten thay the (ten la
    duy nhat trong 13 muc that, da xac nhan truc tiep tren nguon).
  - image_template / storyboard_framework: (is_builtin=True, name) - hai bang
    MOI nay co owner_id NOT NULL (migration b64a39da941d, khac ba bang cu o
    tren), nen KHONG dua owner_id vao khoa: hai admin khac nhau goi lai
    khong duoc tao hai ban ghi khac nhau cho CUNG mot mau he thong. Catalog-
    ness o day dung is_builtin=True + share_level="catalog", KHONG dung
    owner_id NULL (bang khong cho NULL).

Khoa la SELECT-roi-BO-QUA, khong phai upsert/merge: neu ban ghi da ton tai
(du la ban goc chua sua hay ban nguoi dung DA SUA TAY), lan nhap sau khong
dung toi no. Day la dieu kien song cua ca "goi lai khong nhan doi" lan "goi
lai sau khi nguoi dung da sua khong bi ghi de".
"""
from __future__ import annotations

import json
import re
from importlib.resources import files

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.tables import (
    OmmiMetaPrompt, OmmiPromptSnippet, OmmiImageTemplate,
    OmmiStoryboardFramework)

_PACKAGE = "apps.prompt_ai_ommi.prompts.mau_goc"

#: Placeholder cua IMAGE TEMPLATE la mot bo KHAC voi meta prompt (spec S7.2:
#: {SUBJECT}/{STYLE}/{EXTRA}/{EQUIPMENT}, khong giao voi bang quy doi S7).
#: image_gen_templates cua ban goc khong co cot rieng luu san ten nay, nen ta
#: tu suy tu chinh prompt_text luc nhap - khong lam vay thi cot `placeholders`
#: cua OmmiImageTemplate (them 26/09) se la mot COT CHET: co trong schema,
#: ghi duoc, nhung khong ai ghi.
_TOKEN_RE = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")


def _load(filename: str) -> list[dict]:
    raw = files(_PACKAGE).joinpath(filename).read_text(encoding="utf-8")
    payload = json.loads(raw)
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise ValueError(f"{filename}: khong doc duoc danh sach 'items'.")
    return items


def _suy_placeholders(prompt_text: str) -> list[str]:
    return sorted(set(_TOKEN_RE.findall(str(prompt_text or ""))))


def _nhap_meta_prompts(db: Session) -> dict:
    them = bo_qua = 0
    for item in _load("meta_prompts.json"):
        target_format = str(item["target_format"])
        name = str(item["name"])
        exists = db.execute(select(OmmiMetaPrompt.id).where(
            OmmiMetaPrompt.owner_id.is_(None),
            OmmiMetaPrompt.target_format == target_format,
            OmmiMetaPrompt.name == name)).first()
        if exists is not None:
            bo_qua += 1
            continue
        db.add(OmmiMetaPrompt(
            owner_id=None, name=name, body=str(item["body"]),
            target_format=target_format,
            is_default=bool(item.get("is_default", False)),
            placeholders=list(item.get("placeholders") or []),
            is_catalog=True, share_level="catalog"))
        them += 1
    return {"them": them, "bo_qua": bo_qua}


def _nhap_snippets(db: Session) -> dict:
    them = bo_qua = 0
    for item in _load("snippets.json"):
        name = str(item["name"])
        exists = db.execute(select(OmmiPromptSnippet.id).where(
            OmmiPromptSnippet.owner_id.is_(None),
            OmmiPromptSnippet.name == name)).first()
        if exists is not None:
            bo_qua += 1
            continue
        db.add(OmmiPromptSnippet(
            owner_id=None, name=name, body=str(item["body"]),
            category=str(item.get("category") or ""),
            is_catalog=True, share_level="catalog"))
        them += 1
    return {"them": them, "bo_qua": bo_qua}


def _nhap_image_templates(db: Session, admin_owner_id: str) -> dict:
    them = bo_qua = 0
    for item in _load("image_templates.json"):
        name = str(item["name"])
        exists = db.execute(select(OmmiImageTemplate.id).where(
            OmmiImageTemplate.is_builtin.is_(True),
            OmmiImageTemplate.name == name)).first()
        if exists is not None:
            bo_qua += 1
            continue
        prompt_text = str(item["prompt_text"])
        db.add(OmmiImageTemplate(
            owner_id=admin_owner_id, name=name,
            icon=str(item.get("icon") or ""),
            description=str(item.get("description") or ""),
            prompt_text=prompt_text,
            n_outputs=int(item.get("n_outputs") or 1),
            aspect=str(item.get("aspect") or "1:1"),
            asset_type=str(item["asset_type"]),
            asset_subtype=str(item.get("asset_subtype") or ""),
            grid_layout=str(item.get("grid_layout") or ""),
            output_mode=str(item.get("output_mode") or "grid"),
            requires_ref=bool(item.get("requires_ref", False)),
            multi_ref_max=int(item.get("multi_ref_max") or 1),
            bg_style=str(item.get("bg_style") or ""),
            negative_lock=str(item.get("negative_lock") or ""),
            placeholder_hint=str(item.get("placeholder_hint") or ""),
            placeholders=_suy_placeholders(prompt_text),
            is_builtin=True, share_level="catalog"))
        them += 1
    return {"them": them, "bo_qua": bo_qua}


def _nhap_storyboard_frameworks(db: Session, admin_owner_id: str) -> dict:
    them = bo_qua = 0
    for item in _load("storyboard_frameworks.json"):
        name = str(item["name"])
        exists = db.execute(select(OmmiStoryboardFramework.id).where(
            OmmiStoryboardFramework.is_builtin.is_(True),
            OmmiStoryboardFramework.name == name)).first()
        if exists is not None:
            bo_qua += 1
            continue
        db.add(OmmiStoryboardFramework(
            owner_id=admin_owner_id, name=name,
            icon=str(item.get("icon") or ""),
            description=str(item.get("description") or ""),
            composite_header=str(item.get("composite_header") or ""),
            composite_rules=str(item.get("composite_rules") or ""),
            composite_negative_footer=str(
                item.get("composite_negative_footer") or ""),
            breakdown_llm_prompt=str(item.get("breakdown_llm_prompt") or ""),
            default_aspect=str(item.get("default_aspect") or "16:9"),
            default_n_scenes=int(item.get("default_n_scenes") or 3),
            is_builtin=True, share_level="catalog"))
        them += 1
    return {"them": them, "bo_qua": bo_qua}


def nhap(db: Session, *, admin_owner_id: str) -> dict:
    """Nhap ca 4 loai mot luot. Idempotent - goi lai chi bao cao them=0.

    KHONG tu commit — goi lai qua route/service goi ham nay chiu trach nhiem
    commit (hoac rollback) trong transaction cua no.
    """
    ket_qua = {
        "meta_prompt": _nhap_meta_prompts(db),
        "snippet": _nhap_snippets(db),
        "image_template": _nhap_image_templates(db, admin_owner_id),
        "storyboard_framework": _nhap_storyboard_frameworks(db, admin_owner_id),
    }
    db.flush()
    return ket_qua
