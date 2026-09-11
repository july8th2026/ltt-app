"""Durable PROMPT AI OMMI generation job."""
from __future__ import annotations

from platform_core.i18n import _ as _t
import uuid
from datetime import datetime, timezone

from apps.prompt_ai_ommi import provider
from apps.prompt_ai_ommi.project_schema import MAX_SCENES, clean_scene
from apps.prompt_ai_ommi.services.composer import director_prompt


def _normalize_result(raw: dict, params: dict) -> dict:
    requested = max(1, min(MAX_SCENES, int(params.get("scene_count") or 6)))
    raw_scenes = list(raw.get("scenes") or [])[:requested]
    if not raw_scenes:
        raise ValueError(_t('AI không trả cảnh nào.'))
    scenes = []
    stamp = datetime.now(timezone.utc).isoformat()
    for index, item in enumerate(raw_scenes):
        scene = clean_scene(item if isinstance(item, dict) else {}, index)
        version = {
            "id": f"ver_{uuid.uuid4().hex[:12]}", "prompt": scene["prompt"],
            "negative_prompt": scene["negative_prompt"], "feedback": "",
            "created_at": stamp,
        }
        scene["versions"] = [version]; scene["selected_version"] = 0
        scenes.append(scene)
    # Provider đôi khi trả thiếu cảnh; bổ sung placeholder trung thực thay vì
    # tuyên bố đủ rồi âm thầm lặp nội dung AI.
    while len(scenes) < requested:
        scenes.append(clean_scene({
            "title": f"Cảnh {len(scenes) + 1}",
            "summary": "Cảnh chưa được AI tạo; cần chỉnh hoặc tạo lại.",
            "continuity": "Giữ continuity từ cảnh trước.",
        }, len(scenes)))
    anchors = raw.get("anchors") if isinstance(raw.get("anchors"), dict) else {}
    package = {
        "summary": str(raw.get("summary") or "")[:3000],
        "anchors": {
            "characters": list(anchors.get("characters") or [])[:20],
            "locations": list(anchors.get("locations") or [])[:20],
            "style": str(anchors.get("style") or params.get("style") or "")[:1000],
            "continuity": list(anchors.get("continuity") or [])[:30],
        },
        "scenes": scenes,
    }
    return package


def handle(params: dict, ctx=None) -> dict:
    story = str(params.get("story") or "").strip()
    if len(story) < 20:
        raise ValueError(_t('Nội dung brief tối thiểu 20 ký tự.'))
    operation = str(params.get("operation") or "director")
    if operation not in {"director", "storyboard"}:
        raise ValueError(_t('Operation không hợp lệ.'))
    if ctx is not None:
        ctx.progress(10, "đang kiểm tra brief và consistency anchors")
    system, prompt = director_prompt(params)
    if ctx is not None:
        ctx.progress(30, "AI Director đang phân cảnh")
    # D09: không khai model ⇒ `provider` tự hỏi bản khai của app (`model_mac_dinh`).
    model = str(params.get("model") or provider.model_mac_dinh())
    raw, tokens = provider.generate_json(system, prompt, model=model)
    if ctx is not None:
        ctx.progress(85, "đang chuẩn hóa prompt package")
    package = _normalize_result(raw, params)
    from apps.prompt_ai_ommi.manifest import _cost
    result = {
        "operation": operation,
        "prompt_package": package,
        "storyboard": package if operation == "storyboard" else None,
        "master_prompt": prompt[:20000], "tokens_used": tokens,
        "model": model,
        "credit_cost": _cost(params),
    }
    if ctx is not None:
        ctx.progress(100, "hoàn tất prompt package")
    return result

