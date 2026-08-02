"""Bounded one-shot planner using api_pool; execution never happens here."""
from __future__ import annotations

import json
from typing import Callable, Optional

from sqlalchemy.orm import Session as DbSession

from platform_core.agent.normalizer import normalize_plan
from platform_core.agent.tools import discover_tools, resolve_params_schema
from platform_core.models import APIKEY_CAT_CHAT

PLANNER_MODEL = "gemini-2.5-flash"
MAX_GOAL_CHARS = 8000


class PlannerError(RuntimeError):
    pass


def build_prompt(goal: str, *, budget_max_credit: int, input_types: dict | None = None) -> str:
    tools = discover_tools()
    lines = ["[AVAILABLE TOOLS]"]
    for name, spec in sorted(tools.items()):
        schema = resolve_params_schema(name)
        compact = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
        returns = json.dumps(spec.returns, ensure_ascii=False, separators=(",", ":"))
        lines.append(f"- {name}: {spec.description}\n  params={compact}\n  returns={returns}")
    lines.extend([
        "[INPUT PORTS] " + json.dumps(input_types or {}, ensure_ascii=False),
        f"[BUDGET] maximum {max(0, int(budget_max_credit))} credits",
        "[USER GOAL] " + (goal or "").strip()[:MAX_GOAL_CHARS],
        "[OUTPUT] Return one Plan JSON object, version=1. No markdown or commentary.",
    ])
    return "\n".join(lines)


def _gemini_call(db: DbSession, prompt: str) -> str:
    import httpx
    from platform_core import api_keys, api_pool
    key = api_pool.chon_key(db, category=APIKEY_CAT_CHAT, model=PLANNER_MODEL,
                            thu_tu_provider=["gemini"])
    credential = api_keys.lay_credential(db, key)
    try:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{PLANNER_MODEL}:generateContent",
            headers={"x-goog-api-key": credential},
            json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        if response.status_code != 200:
            api_pool.danh_dau_loi(db, key, http_status=response.status_code)
            raise PlannerError(f"Planner provider HTTP {response.status_code}.")
        api_pool.danh_dau_thanh_cong(db, key)
        for part in (response.json().get("candidates") or [{}])[0].get("content", {}).get("parts", []):
            if part.get("text"):
                return part["text"]
        raise PlannerError("Planner provider không trả text.")
    except httpx.HTTPError as exc:
        raise PlannerError(f"Planner provider connection error: {type(exc).__name__}.") from None
    finally:
        credential = ""


def plan_once(db: DbSession, *, goal: str, budget_max_credit: int,
              input_types: Optional[dict] = None,
              llm_call: Optional[Callable[[str], object]] = None) -> dict:
    prompt = build_prompt(goal, budget_max_credit=budget_max_credit,
                          input_types=input_types)
    raw = llm_call(prompt) if llm_call is not None else _gemini_call(db, prompt)
    return normalize_plan(raw, fallback_goal=goal, fallback_budget=budget_max_credit)
