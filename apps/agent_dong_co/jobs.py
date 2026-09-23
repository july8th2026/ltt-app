"""Cửa nhận job của `workflow.dong_co`. Xem docstring `manifest.py` cùng thư
mục này: handler thật sống trong `apps.agent.jobs` — cùng file xử lý
`agent.advance`, dùng chung than thi hành — đây chỉ forward sang đó.
"""
from __future__ import annotations

from apps.agent.jobs import handle as _agent_handle


def handle(params: dict, ctx=None) -> dict:
    return _agent_handle(params, ctx)
