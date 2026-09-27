"""services/bindings.py — nguon chan ly the <-> variant (spec Sec 4.2, 6.1, 6.3).

Mot binding gan MOT THE (`@IMAGE_1`, `@VIDEO_1`...) voi dung mot
`ommi_resource_variant`, trong pham vi mot project (va, khi co, mot canh cu
the — `scene_id=None` la binding cap project). Day la bang CHUA loi N-2:
truoc day so the duoc dem lai moi lan build prompt (`composer.resource_lines`)
va dem KHAC DI luc build refs giao bai — hai lan dem doc lap troi khoi nhau
khong ai biet. Tu nay CHI ham o day duoc ghi bang; moi noi khac chi DOC.

Quy tac dung PUT (spec Sec 6.1): moi lan goi la GHI DE TOAN BO danh sach
binding cua (project_id, scene_id) — "danh so lai toan bo", khong phai them/
bot tung the.

⚠️ Lech giua test va ma vi du cua plan (bao dieu phoi, DA CHOT 26/09): plan
`2026-09-26-prompt-ai-pha1-cho-noi-dung.md` Task 4 Step 3 dua `_clean_role()`
goi thang `image_role()` va KHONG BAO GIO nem `BindingError` — nhung chinh
test cua Step 1 (`test_role_khong_hop_le_bi_tu_choi`, tep nay) doi hoi
`BindingError` khi role la chuoi khong hop le. Ham duoi day GIU nguyen y
"dung lai image_role() de chuan hoa + remap ten cu" nhung THEM buoc tu choi
truoc: chuoi da chuan hoa (strip) khong rong, khong phai mot ten hop le, va
khong phai mot ten cu ta tu khai (`_ROLE_ALIAS_CU` duoi day) thi nem
`BindingError`. KHONG doc `apps.taovideo.refs._ROLE_REMAP` — ten rieng tu,
khong nam trong be mat da khai o `.importlinter`/`BE_MAT_CONG_KHAI`, va
`getattr(..., {})` se that bai IM LANG neu ben kia doi ten. Thay vao do khai
literal roi banh coc `tests/test_5122_role_alias_khop_taovideo.py` ep no
KHOP `_ROLE_REMAP` that (do tu tep test, noi import ca hai app la hop le).
"""
from __future__ import annotations

from datetime import datetime, timezone

from platform_core.i18n import _ as _t
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.tables.binding import OmmiBinding
from apps.prompt_ai_ommi.tables.tai_nguyen import OmmiResource, OmmiResourceVariant
from apps.taovideo.refs import VALID_IMAGE_ROLES, image_role

_KINDS = ("image", "video", "audio")
_PREFIX = {"image": "IMAGE", "video": "VIDEO", "audio": "AUDIO"}

#: Ten role CU con nhan, anh xa sang ten chuan. Khai literal o day chu KHONG doc
#: `_ROLE_REMAP` cua taovideo: do la ten RIENG TU, khong nam trong be mat da khai,
#: va `getattr(..., {})` that bai IM LANG khi ben kia doi ten.
#: ⭐ Banh coc `tests/test_5122_role_alias_khop_taovideo.py` ep bo nay khop
#: `_ROLE_REMAP` cua taovideo.
_ROLE_ALIAS_CU = {
    "reference": "reference_image",
    "character": "reference_image",
    "start_frame": "first_frame",
    "end_frame": "last_frame",
}


class BindingError(ValueError):
    """Du lieu vao khong hop le — route tra 400."""


class BindingNotFound(LookupError):
    """Khong ton tai HOAC khong thuoc ve nguoi goi — route tra 404."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_kind(value: str | None) -> str:
    kind = (value or "").strip().lower()
    if kind not in _KINDS:
        raise BindingError(
            f"Loai khong hop le: {value!r}. Chon mot trong: {', '.join(_KINDS)}.")
    return kind


def _clean_role(kind: str, value: str | None) -> str:
    """Anh: dung lai `image_role()` cua taovideo de chuan hoa + remap ten cu,
    nhung tu choi chuoi la (xem doc o dau tep). Video/audio: chi cat do dai,
    khong co bo gia tri dong."""
    if kind != "image":
        return (str(value or "").strip() or "reference_image")[:24]
    raw = str(value or "").strip()
    if not raw:
        return "reference_image"
    if raw in VALID_IMAGE_ROLES:
        return raw
    if raw in _ROLE_ALIAS_CU:
        return image_role(raw)
    raise BindingError(
        f"Role anh khong hop le: {raw!r}. Chon mot trong: "
        f"{', '.join(sorted(VALID_IMAGE_ROLES))}.")


def list_bindings(db: Session, *, project_id: str, owner_id: str,
                  scene_id: str | None = None) -> list[OmmiBinding]:
    stmt = (select(OmmiBinding)
            .where(OmmiBinding.project_id == project_id,
                   OmmiBinding.owner_id == owner_id,
                   OmmiBinding.scene_id == scene_id)
            .order_by(OmmiBinding.kind, OmmiBinding.position))
    return list(db.execute(stmt).scalars().all())


def replace_bindings(db: Session, *, project_id: str, owner_id: str,
                     scene_id: str | None, items: list[dict]
                     ) -> tuple[list[OmmiBinding], int]:
    """Xoa het binding cu cua (project_id, scene_id) roi ghi lai theo `items`,
    danh so lai TOAN BO theo Sec 6.3 quy tac 1-2.

    Quy tac 2: variant khong con ban ghi (hoac khong phai cua owner_id) =>
    KHONG tieu so — loai khoi danh sach TRUOC khi dem, khong chi bo qua sau.
    """
    validated: list[tuple[str, str, str]] = []  # (kind, variant_id, role)
    for item in items:
        kind = _clean_kind(item.get("kind"))
        variant_id = str(item.get("variant_id") or "").strip()
        if not variant_id:
            raise BindingError("Thieu variant_id.")
        variant = db.get(OmmiResourceVariant, variant_id)
        if variant is None or variant.owner_id != owner_id:
            continue  # quy tac 2: khong tieu so
        role = _clean_role(kind, item.get("role"))
        validated.append((kind, variant_id, role))

    db.execute(delete(OmmiBinding).where(
        OmmiBinding.project_id == project_id, OmmiBinding.owner_id == owner_id,
        OmmiBinding.scene_id == scene_id))

    counters = {"image": 0, "video": 0, "audio": 0}
    created: list[OmmiBinding] = []
    for kind, variant_id, role in validated:
        counters[kind] += 1
        row = OmmiBinding(
            owner_id=owner_id, project_id=project_id, scene_id=scene_id,
            tag=f"@{_PREFIX[kind]}_{counters[kind]}", kind=kind,
            variant_id=variant_id, position=counters[kind], role=role)
        db.add(row)
        created.append(row)
    db.flush()
    return created, len(created)


def delete_binding(db: Session, *, project_id: str, owner_id: str,
                   scene_id: str | None, tag: str) -> list[OmmiBinding]:
    row = db.execute(select(OmmiBinding).where(
        OmmiBinding.project_id == project_id, OmmiBinding.owner_id == owner_id,
        OmmiBinding.scene_id == scene_id, OmmiBinding.tag == tag)).scalars().first()
    if row is None:
        raise BindingNotFound("Khong tim thay binding.")
    db.delete(row)
    db.flush()
    return list_bindings(db, project_id=project_id, owner_id=owner_id, scene_id=scene_id)


def binding_lines(db: Session, *, project_id: str, owner_id: str,
                  scene_id: str | None = None) -> list[dict]:
    """Dong tai nguyen DA GAN THE, de `composer.resource_lines()` khong tu
    dem nua (quyet dinh D-2, dau plan). Diem noi cho pha 2/3 (bundle/placeholder)."""
    items = []
    for binding in list_bindings(db, project_id=project_id, owner_id=owner_id,
                                 scene_id=scene_id):
        variant = db.get(OmmiResourceVariant, binding.variant_id)
        resource = db.get(OmmiResource, variant.resource_id) if variant else None
        name = (variant.label if variant and variant.label else
               (resource.name if resource else _t("Tài nguyên")))
        items.append({"tag": binding.tag, "kind": binding.kind, "name": name,
                     "description": resource.description if resource else ""})
    return items
