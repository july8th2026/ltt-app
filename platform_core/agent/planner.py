"""Bounded one-shot planner using api_pool; execution never happens here."""
from __future__ import annotations

import json
from typing import Callable, Optional

from sqlalchemy.orm import Session as DbSession

from platform_core.agent.normalizer import normalize_plan
from platform_core.agent.tools import discover_tools, resolve_params_schema
from platform_core.models import APIKEY_CAT_CHAT

PLANNER_MODEL = "gemini-2.5-flash"

#: Thu tu thu provider cho viec lap ke hoach. MODEL NHA DI TRUOC: re hon nhieu,
#: va prompt khong roi may. May B ban thi `dieu_phoi` tu di tiep sang Gemini.
PLANNER_PROVIDERS = ("ltt_llm", "gemini")

#: Moi provider co id model rieng. Gui nham ten sang provider kia thi no tu choi,
#: va ben goi se tuong provider do "dang hong".
PLANNER_MODEL_THEO_PROVIDER = {"ltt_llm": "ltt_llm", "gemini": PLANNER_MODEL}
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


def _goi_model(db: DbSession, prompt: str) -> str:
    """Gọi model lập kế hoạch qua `platform_core.llm.dieu_phoi`. (H38)

    ⭐ TRƯỚC ĐÂY hàm này tự dựng HTTP tới `generativelanguage.googleapis.com` và
       ghi cứng `thu_tu_provider=["gemini"]`. Hai hệ quả:

         1. Thêm một provider vào `REGISTRY` **không làm chỗ này dùng nó**;
         2. Cùng đoạn mã đó bị chép ở `apps/autosubvideo` và `apps/kichban`.

       `dieu_phoi` gom việc dịch giao thức về một chỗ, nên nay đổi nhà cung cấp là
       đổi **một danh sách**, không phải sửa ba tệp.

    ⭐ MODEL NHÀ ĐI TRƯỚC. Nó rẻ hơn nhiều, và prompt lập kế hoạch **không rời máy**.
       Máy B bận thì `dieu_phoi` tự đi tiếp sang Gemini — và đó **không** phải
       "đổi model sau lưng khách" (D-010): việc lập kế hoạch là việc nội bộ, khách
       không mua "một kế hoạch do model X sinh ra", và thứ tự được **khai ra ở đây**.
    """
    from platform_core.llm import dieu_phoi

    try:
        kq = dieu_phoi.goi(
            db,
            messages=[{"role": "user", "content": prompt}],
            category=APIKEY_CAT_CHAT,
            thu_tu_provider=PLANNER_PROVIDERS,
            model_theo_provider=PLANNER_MODEL_THEO_PROVIDER,
            timeout_s=120.0,
        )
    except dieu_phoi.KhongCoProviderNao as exc:
        # ⛔ Mọi provider đều bận/không cấp được key. KHÔNG phải lỗi provider —
        #    `dieu_phoi` đã lo việc đánh dấu lỗi cho đúng trường hợp rồi.
        raise PlannerError(f"Planner: {exc}") from None

    van = (kq.noi_dung or "").strip()
    if not van:
        raise PlannerError("Planner provider không trả text.")
    return van


def plan_once(db: DbSession, *, goal: str, budget_max_credit: int,
              input_types: Optional[dict] = None,
              llm_call: Optional[Callable[[str], object]] = None) -> dict:
    prompt = build_prompt(goal, budget_max_credit=budget_max_credit,
                          input_types=input_types)
    raw = llm_call(prompt) if llm_call is not None else _goi_model(db, prompt)
    return normalize_plan(raw, fallback_goal=goal, fallback_budget=budget_max_credit)
