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
        handle = ""
        if kind in counters:
            counters[kind] += 1
            handle = f"@{kind.upper()}_{counters[kind]} "
        name = str(item.get("name") or "Tài nguyên").strip()
        desc = str(item.get("description") or "").strip()
        lines.append(f"- {handle}[{kind}] {name}: {desc}".rstrip())
    return lines


def preview(project: dict) -> dict:
    brief = project["brief"]
    style = style_description(brief.get("style_id", "cinematic"),
                              brief.get("style_custom", ""))
    resources = resource_lines(project.get("resources") or [])
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
        f"RESOURCES:\n{chr(10).join(resources) if resources else '- No explicit references'}\n"
        "CONTINUITY: preserve identity, wardrobe, geography, lighting logic and screen direction."
    )
    return {"valid": all(item["passed"] for item in checklist),
            "checklist": checklist, "master_prompt": text[:20000],
            "resource_count": len(resources), "scene_count": brief["scene_count"]}


def director_prompt(params: dict) -> tuple[str, str]:
    system = (PROMPTS / "director_system.txt").read_text(encoding="utf-8").strip()
    resources = resource_lines(list(params.get("resources") or []))
    existing = list(params.get("existing_scenes") or [])
    user = (PROMPTS / "director_user.txt").read_text(encoding="utf-8").format(
        operation=params.get("operation", "director"),
        title=params.get("title", ""), story=params.get("story", ""),
        goal=params.get("goal", ""), audience=params.get("audience", ""),
        duration=params.get("duration_seconds", 30), scenes=params.get("scene_count", 6),
        aspect=params.get("aspect_ratio", "16:9"), style=params.get("style", "cinematic"),
        language=params.get("language", "vi"),
        resources="\n".join(resources) if resources else "- none",
        existing=json.dumps(existing[:20], ensure_ascii=False),
    )
    return system, user[:30000]

