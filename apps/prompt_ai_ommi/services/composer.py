"""Deterministic prompt preview and normalization."""
from __future__ import annotations

from platform_core.i18n import _ as _t
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "prompts"


def load_catalog() -> dict:
    data = json.loads((PROMPTS / "catalog.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(_t('catalog prompt không hợp lệ'))
    return data


def style_description(style_id: str, custom: str = "") -> str:
    if str(custom or "").strip():
        return str(custom).strip()[:500]
    for item in load_catalog().get("styles", []):
        if item.get("id") == style_id:
            return str(item.get("prompt") or item.get("label") or style_id)
    return str(style_id or "cinematic")[:120]


def resource_lines(resources: list[dict]) -> list[str]:
    lines = []
    counters: dict[str, int] = {"image": 0, "video": 0, "audio": 0}
    for item in resources[:24]:
        kind = str(item.get("kind") or "prop")
        tag = str(item.get("tag") or "").strip()
        if tag:
            handle = f"{tag} "
        else:
            handle = ""
            if kind in counters:
                counters[kind] += 1
                handle = f"@{kind.upper()}_{counters[kind]} "
        name = str(item.get("name") or "Tài nguyên").strip()
        desc = str(item.get("description") or "").strip()
        lines.append(f"- {handle}[{kind}] {name}: {desc}".rstrip())
    return lines


def preview(project: dict, *, style_override: str = "", style_negative: str = "",
            meta_prompt: str = "", snippets: list[str] | None = None,
            selection_names: dict | None = None) -> dict:
    brief = project["brief"]
    style = (str(brief.get("style_custom") or style_override).strip() or
             style_description(brief.get("style_id", "cinematic")))
    resources = resource_lines(project.get("resources") or [])
    snippet_rows = [str(item).strip() for item in (snippets or []) if str(item).strip()]
    names = selection_names or {}
    checklist = [
        {"id": "title", "label": "Tên dự án", "passed": bool(brief.get("title"))},
        {"id": "story", "label": "Nội dung tối thiểu 20 ký tự",
         "passed": len(str(brief.get("story") or "").strip()) >= 20},
        {"id": "scene_count", "label": "Số cảnh 1–20",
         "passed": 1 <= int(brief.get("scene_count") or 0) <= 20},
        {"id": "duration", "label": "Thời lượng 3–600 giây",
         "passed": 3 <= int(brief.get("duration_seconds") or 0) <= 600},
    ]
    text = (
        f"PROJECT: {brief['title']}\n"
        f"GOAL: {brief.get('goal') or 'Create a coherent cinematic sequence'}\n"
        f"STORY: {brief.get('story')}\n"
        f"AUDIENCE: {brief.get('audience') or 'general audience'}\n"
        f"FORMAT: {brief.get('scene_count')} scenes · {brief.get('duration_seconds')}s · "
        f"{brief.get('aspect_ratio')}\nSTYLE: {style}\n"
        f"NEGATIVE GUIDANCE: {style_negative or '- none'}\n"
        f"META DIRECTOR: {meta_prompt or '- default director'}\n"
        f"PROMPT BLOCKS:\n{chr(10).join(f'- {item}' for item in snippet_rows) if snippet_rows else '- none'}\n"
        f"RESOURCES:\n{chr(10).join(resources) if resources else '- No explicit references'}\n"
        "CONTINUITY: preserve identity, wardrobe, geography, lighting logic and screen direction."
    )
    return {"valid": all(item["passed"] for item in checklist),
            "checklist": checklist, "master_prompt": text[:20000],
            "resource_count": len(resources), "scene_count": brief["scene_count"],
            "selections": {
                "style": str(names.get("style") or brief.get("style_id") or "cinematic"),
                "meta": str(names.get("meta") or _t("Mặc định")),
                "snippets": list(names.get("snippets") or []),
            }}


def director_prompt(params: dict) -> tuple[str, str]:
    system = (PROMPTS / "director_system.txt").read_text(encoding="utf-8").strip()
    meta_prompt = str(params.get("meta_prompt") or "").strip()
    if meta_prompt:
        system = f"{system}\n\nSELECTED META DIRECTOR:\n{meta_prompt}"[:30000]
    resources = resource_lines(list(params.get("resources") or []))
    existing = list(params.get("existing_scenes") or [])
    resources_text = "\n".join(resources) if resources else "- none"
    # X-5 / spec Sec 8: khoi chu khoa nhan vat/boi canh PHAI di vao prompt gui
    # LLM -- luu `fixed_prompt_block` ma khong chen vao day thi tinh nang khoa
    # nhan vat khong lam gi ca (test_5342). Di TRUOC danh sach tai nguyen: LLM
    # doc tu tren xuong, va day la mot RANG BUOC phai giu o MOI canh, khong
    # phai mot goi y giua danh sach tham chieu.
    khoi = []
    for nhan, ten in (("CHARACTER LOCK (must match in EVERY scene)",
                       "character_block"),
                      ("BACKGROUND LOCK", "background_block")):
        gia_tri = str(params.get(ten) or "").strip()
        if gia_tri:
            khoi.append(f"{nhan}:\n{gia_tri}")
    resources_block = "\n\n".join(khoi + [resources_text])
    user = (PROMPTS / "director_user.txt").read_text(encoding="utf-8").format(
        operation=params.get("operation", "director"),
        title=params.get("title", ""), story=params.get("story", ""),
        goal=params.get("goal", ""), audience=params.get("audience", ""),
        duration=params.get("duration_seconds", 30), scenes=params.get("scene_count", 6),
        aspect=params.get("aspect_ratio", "16:9"), style=params.get("style", "cinematic"),
        language=params.get("language", "vi"),
        resources=resources_block,
        existing=json.dumps(existing[:20], ensure_ascii=False),
    )
    style_negative = str(params.get("style_negative") or "").strip()
    snippets = [str(item).strip() for item in list(params.get("snippets") or [])[:8]
                if str(item).strip()]
    if style_negative:
        user += f"\n\nAVOID / NEGATIVE STYLE:\n{style_negative}"
    if snippets:
        user += "\n\nREUSABLE PROMPT BLOCKS:\n" + "\n".join(
            f"- {item}" for item in snippets)
    return system, user[:30000]

