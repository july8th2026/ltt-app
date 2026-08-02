"""Parse and normalize untrusted planner output into Plan v1."""
from __future__ import annotations

import json
import re

MAX_PLAN_BYTES = 64 * 1024
MAX_JSON_DEPTH = 20
_STEP_ID = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


class PlanNormalizeError(ValueError):
    pass


def _depth(value, level=0) -> int:
    if level > MAX_JSON_DEPTH:
        return level
    if isinstance(value, dict):
        return max([level] + [_depth(v, level + 1) for v in value.values()])
    if isinstance(value, list):
        return max([level] + [_depth(v, level + 1) for v in value])
    return level


def extract_json(raw) -> dict:
    if isinstance(raw, dict):
        candidate = raw.get("arguments", raw)
        if isinstance(candidate, str):
            raw = candidate
        else:
            if len(json.dumps(candidate, ensure_ascii=False).encode("utf-8")) > MAX_PLAN_BYTES:
                raise PlanNormalizeError("Planner output vượt giới hạn 64 KiB.")
            if _depth(candidate) > MAX_JSON_DEPTH:
                raise PlanNormalizeError("Plan JSON lồng quá sâu.")
            return candidate
    if not isinstance(raw, str):
        raise PlanNormalizeError("Planner output phải là text hoặc object.")
    if len(raw.encode("utf-8")) > MAX_PLAN_BYTES:
        raise PlanNormalizeError("Planner output vượt giới hạn 64 KiB.")
    text = raw.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        text = text[first_newline + 1:] if first_newline >= 0 else text[3:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            if _depth(value) > MAX_JSON_DEPTH:
                raise PlanNormalizeError("Plan JSON lồng quá sâu.")
            return value
    raise PlanNormalizeError("Không tìm thấy Plan JSON hợp lệ.")


def normalize_plan(raw, *, fallback_goal: str = "", fallback_budget: int = 0) -> dict:
    obj = extract_json(raw)
    steps_raw = obj.get("steps", obj.get("nodes", []))
    if not isinstance(steps_raw, list):
        raise PlanNormalizeError("steps phải là danh sách.")
    steps = []
    for index, source in enumerate(steps_raw, 1):
        if not isinstance(source, dict):
            raise PlanNormalizeError(f"step {index} phải là object.")
        step_id = str(source.get("id") or f"s{index}").strip().lower()
        if not _STEP_ID.fullmatch(step_id):
            raise PlanNormalizeError(f"step id không hợp lệ: {step_id!r}")
        after = source.get("after", source.get("depends_on", [])) or []
        if isinstance(after, str):
            after = [after]
        params = source.get("params", source.get("inputs", {})) or {}
        steps.append({
            "id": step_id,
            "tool": str(source.get("tool", source.get("tool_name", ""))).strip(),
            "params": params,
            "after": list(after) if isinstance(after, list) else after,
            "fanout": source.get("fanout", 1),
            "verify": source.get("verify"),
            "on_fail": source.get("on_fail", "retry_same"),
            "max_retry": source.get("max_retry", 0),
        })
    return {
        "version": obj.get("version", 1),
        "goal": str(obj.get("goal") or fallback_goal).strip(),
        "budget_max_credit": obj.get("budget_max_credit", fallback_budget),
        "steps": steps,
    }
