"""Versioned, owner-neutral JSON schema for PROMPT AI OMMI projects."""
from __future__ import annotations

from platform_core.i18n import _ as _t
import copy
import re
import uuid

SCHEMA_VERSION = 1
MAX_SCENES = 20
MAX_RESOURCES = 24
MAX_VERSIONS = 8
ASPECTS = ("16:9", "9:16", "1:1", "4:3", "3:4", "21:9")
LANGUAGES = ("vi", "en")
RESOURCE_KINDS = ("character", "location", "prop", "style", "image", "video", "audio")


def _text(value, limit: int) -> str:
    return " ".join(str(value or "").replace("\x00", "").split())[:limit]


def _multiline(value, limit: int) -> str:
    return str(value or "").replace("\x00", "").strip()[:limit]


def _integer(value, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(number, maximum))


def _id(value: str, prefix: str) -> str:
    value = str(value or "")[:64]
    return value if re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", value) else f"{prefix}_{uuid.uuid4().hex[:12]}"


def empty_project(name: str = "Dự án mới") -> dict:
    return {
        "kind": "production", "version": SCHEMA_VERSION,
        "brief": {
            "title": _text(name, 160), "story": "", "goal": "",
            "audience": "", "duration_seconds": 30, "scene_count": 6,
            "aspect_ratio": "16:9", "language": "vi", "style_id": "cinematic",
            "style_custom": "", "meta_prompt_id": "", "snippet_ids": [],
            "notes": "",
        },
        "resources": [], "scenes": [],
        "storyboard": {"layout": "3x2", "frames": [], "selected_version": 0},
        "job_refs": [], "ui": {"active_step": "brief", "selected_scene_id": ""},
    }


def clean_resource(item: dict) -> dict:
    item = item if isinstance(item, dict) else {}
    kind = str(item.get("kind") or "prop")
    if kind not in RESOURCE_KINDS:
        kind = "prop"
    storage_key = str(item.get("storage_key") or "")[:500]
    return {
        "id": _id(item.get("id"), "res"), "kind": kind,
        "name": _text(item.get("name"), 120) or "Tài nguyên",
        "description": _multiline(item.get("description"), 1200),
        "storage_key": storage_key, "content_type": _text(item.get("content_type"), 100),
        "size": _integer(item.get("size"), 0, 0, 100 * 1024 * 1024),
    }


def clean_scene(item: dict, order: int) -> dict:
    item = item if isinstance(item, dict) else {}
    versions = []
    for version in list(item.get("versions") or [])[:MAX_VERSIONS]:
        if not isinstance(version, dict):
            continue
        versions.append({
            "id": _id(version.get("id"), "ver"),
            "prompt": _multiline(version.get("prompt"), 10000),
            "negative_prompt": _multiline(version.get("negative_prompt"), 3000),
            "feedback": _multiline(version.get("feedback"), 1000),
            "created_at": _text(version.get("created_at"), 40),
        })
    selected = _integer(item.get("selected_version"), 0, 0, max(0, len(versions) - 1))
    return {
        "id": _id(item.get("id"), "scene"), "order": order,
        "title": _text(item.get("title"), 160) or f"Cảnh {order + 1}",
        "duration_seconds": _integer(item.get("duration_seconds"), 5, 1, 60),
        "summary": _multiline(item.get("summary"), 1200),
        "prompt": _multiline(item.get("prompt"), 10000),
        "negative_prompt": _multiline(item.get("negative_prompt"), 3000),
        "camera": _text(item.get("camera"), 300),
        "lighting": _text(item.get("lighting"), 300),
        "mood": _text(item.get("mood"), 300),
        "continuity": _multiline(item.get("continuity"), 1000),
        "versions": versions, "selected_version": selected,
    }


def clean_project(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError(_t('Project phải là object.'))
    if payload.get("kind", "production") != "production":
        raise ValueError(_t('Sai loại project PROMPT AI OMMI.'))
    source = copy.deepcopy(empty_project())
    brief = payload.get("brief") if isinstance(payload.get("brief"), dict) else {}
    snippet_ids = []
    for value in list(brief.get("snippet_ids") or [])[:8]:
        item_id = _text(value, 80)
        if item_id and item_id not in snippet_ids:
            snippet_ids.append(item_id)
    source["brief"] = {
        "title": _text(brief.get("title"), 160) or "Dự án mới",
        "story": _multiline(brief.get("story"), 12000),
        "goal": _multiline(brief.get("goal"), 1200),
        "audience": _text(brief.get("audience"), 300),
        "duration_seconds": _integer(brief.get("duration_seconds"), 30, 3, 600),
        "scene_count": _integer(brief.get("scene_count"), 6, 1, MAX_SCENES),
        "aspect_ratio": brief.get("aspect_ratio") if brief.get("aspect_ratio") in ASPECTS else "16:9",
        "language": brief.get("language") if brief.get("language") in LANGUAGES else "vi",
        "style_id": _text(brief.get("style_id"), 80) or "cinematic",
        "style_custom": _multiline(brief.get("style_custom"), 500),
        "meta_prompt_id": _text(brief.get("meta_prompt_id"), 80),
        "snippet_ids": snippet_ids,
        "notes": _multiline(brief.get("notes"), 2000),
    }
    source["resources"] = [clean_resource(item) for item in
                           list(payload.get("resources") or [])[:MAX_RESOURCES]]
    source["scenes"] = [clean_scene(item, i) for i, item in
                        enumerate(list(payload.get("scenes") or [])[:MAX_SCENES])]
    board = payload.get("storyboard") if isinstance(payload.get("storyboard"), dict) else {}
    frames = []
    for item in list(board.get("frames") or [])[:MAX_SCENES]:
        if not isinstance(item, dict):
            continue
        frames.append({
            "scene_id": _id(item.get("scene_id"), "scene"),
            "image_job_id": _text(item.get("image_job_id"), 64),
            "image_key": str(item.get("image_key") or "")[:500],
            "prompt": _multiline(item.get("prompt"), 4000),
            "status": _text(item.get("status"), 32),
        })
    source["storyboard"] = {
        "layout": board.get("layout") if board.get("layout") in {"2x2", "3x2", "3x3", "4x3"} else "3x2",
        "frames": frames,
        "selected_version": _integer(board.get("selected_version"), 0, 0, MAX_VERSIONS - 1),
    }
    source["job_refs"] = [_text(value, 64) for value in list(payload.get("job_refs") or [])[:80]
                          if _text(value, 64)]
    ui = payload.get("ui") if isinstance(payload.get("ui"), dict) else {}
    source["ui"] = {
        "active_step": ui.get("active_step") if ui.get("active_step") in
                       {"brief", "resources", "director", "storyboard", "export"} else "brief",
        "selected_scene_id": _text(ui.get("selected_scene_id"), 64),
    }
    return source


def prompt_job_params(project: dict, *, operation: str, model: str,
                      prompt_context: dict | None = None) -> dict:
    clean = clean_project(project); brief = clean["brief"]
    context = prompt_context or {}
    style = (brief["style_custom"] or context.get("style_override") or
             brief["style_id"])
    return {
        "operation": operation if operation in {"director", "storyboard"} else "director",
        "title": brief["title"], "story": brief["story"],
        "goal": brief["goal"], "audience": brief["audience"],
        "duration_seconds": brief["duration_seconds"],
        "scene_count": brief["scene_count"], "aspect_ratio": brief["aspect_ratio"],
        "style": style, "language": brief["language"],
        "style_negative": str(context.get("style_negative") or "")[:3000],
        "meta_prompt": str(context.get("meta_prompt") or "")[:24000],
        "snippets": [str(item)[:4000] for item in
                     list(context.get("snippets") or [])[:8]],
        "selection_names": dict(context.get("selection_names") or {}),
        "resources": clean["resources"], "existing_scenes": clean["scenes"],
        "model": model,
    }
