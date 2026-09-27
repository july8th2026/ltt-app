"""Bundle -- render meta-prompt + danh sach asset, KHONG goi LLM.

Mien phi (chu du an chot 26/09, Q-6). Khach xem/copy duoc khoi chu ta gui cho
LLM. Doi lai: khach tin ta dung prompt the nao, va co duong tu lam.

Tep nay KHONG duoc import `provider`. Mot lan goi LLM o day la mot lan khach
dung tien cua ta ma khong tra -- va `test_bundle_KHONG_goi_LLM` se do.
"""
from __future__ import annotations

from apps.prompt_ai_ommi.services import placeholders as ph


def khai_bao_cua(meta) -> list[str]:
    """Danh sach placeholder mau NAY khai.

    Doc duoc o CA hai doi schema: pha 3 chua co cot `placeholders` (no o
    pha 4), nen roi ve `variables["placeholders"]`. Dung sua cho goi khi
    pha 4 them cot -- `getattr` bat duoc ngay (P-5).
    """
    thuc = getattr(meta, "placeholders", None)
    if thuc:
        return [str(x) for x in thuc]
    bien = getattr(meta, "variables", None) or {}
    return [str(x) for x in (bien.get("placeholders") or [])]


def _dong_asset(bindings, kind: str) -> list[str]:
    """Mot dong mot the, dung the DA LUU trong `ommi_binding`.

    Khong tu danh so lai o day: `ommi_binding` la nguon chan ly cua the
    (spec N-2). Danh so hai cho la hai ket qua khac nhau cho cung mot canh.
    """
    return [f"- {b.tag} [{b.kind}] variant={b.variant_id}"
            for b in bindings if b.kind == kind]


def gia_tri_cho(db, brief, *, project_name: str = "", style=None,
                canh=None) -> dict:
    """Gia tri cho tung placeholder he thong (bang spec Sec 7)."""
    from apps.prompt_ai_ommi.services import bindings as bd
    from apps.prompt_ai_ommi.services.composer import style_description

    ds = bd.list_bindings(db, project_id=brief.project_id, owner_id=brief.owner_id) if brief.project_id else []
    mo_ta_style = style_description(getattr(style, "id", "") or "cinematic",
                                   getattr(style, "body", "") or "")
    return {
        "TITLE": brief.title,
        "PROJECT_NAME": project_name,
        "BRIEF_VI": brief.story_vi,
        "DURATION": brief.target_duration_sec,
        "SCENES": brief.target_scenes,
        "ASPECT_RATIO": brief.aspect_ratio,
        "ASPECT": brief.aspect_ratio,
        "STYLE_FULL": mo_ta_style,
        "STYLE_POSITIVE": getattr(style, "body", "") or "",
        "STYLE_NEGATIVE": getattr(style, "negative", "") or "",
        "ASSET_LIST": "\n".join(_dong_asset(ds, "image")),
        "VIDEO_LIST": "\n".join(_dong_asset(ds, "video")),
        "PROMPT": getattr(canh, "prompt", "") or "",
        "REF_NOTE": getattr(canh, "continuity", "") or "",
        "CHARACTER_DESCRIPTION": "",
    }


def dung_bundle(db, brief, meta, style, *, project_name: str = "",
                gia_tri_them: dict | None = None, canh=None) -> dict:
    """Ghep chu. Tra ca `missing_placeholders` -- KHONG im lang render hong."""
    khai = khai_bao_cua(meta)
    gia_tri = gia_tri_cho(db, brief, project_name=project_name, style=style,
                          canh=canh)
    gia_tri.update(gia_tri_them or {})
    body = getattr(meta, "body", "") or ""
    thieu = ph.kiem_placeholder(body, khai, gia_tri)
    from apps.prompt_ai_ommi.services import bindings as bd
    ds = bd.list_bindings(db, project_id=brief.project_id, owner_id=brief.owner_id) if brief.project_id else []
    return {
        "rendered": ph.render(body, gia_tri),
        "asset_list": _dong_asset(ds, "image"),
        "video_list": _dong_asset(ds, "video"),
        "bindings": [{"tag": b.tag, "kind": b.kind, "variant_id": b.variant_id}
                     for b in ds],
        "missing_placeholders": thieu,
    }
