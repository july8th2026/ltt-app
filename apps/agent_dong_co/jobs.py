"""Cửa nhận job của `workflow.dong_co`. Xem docstring `manifest.py` cùng thư
mục này: handler thật sống trong `apps.agent.jobs` — nó dùng chung thân thi
hành với phần còn lại của app Agent, nên đây chỉ forward sang đó.

⏭️ `agent.advance` (job thứ hai mà tệp kia từng xử lý) đã gỡ 23/09/2026 cùng
   runtime v1 — spec §17.5. `apps.agent.jobs.handle` giờ chỉ nhận đúng một
   `job_type`, và từ chối mọi thứ khác.
"""
from __future__ import annotations

from apps.agent.jobs import handle as _agent_handle


def handle(params: dict, ctx=None) -> dict:
    return _agent_handle(params, ctx)
