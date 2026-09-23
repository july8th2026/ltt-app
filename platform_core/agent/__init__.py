"""Năng lực LTT Agent dùng chung; không chứa runtime hay hàng đợi riêng."""

from platform_core.agent.tools import (discover_tools, resolve_params_schema,
                                       validate_tool_params)
from platform_core.agent.validator import validate_plan

# 🗑️ `approve`/`cancel`/`quote`/`settle` đi cùng `budget.py` và `runs.py` ngày
#    23/09/2026 (plan 01b Task 9, spec §17.3+§17.5): cả bốn là ranh giới tiền
#    của `AgentRun`, mà bảng `agent_runs` đã ngừng được dùng. Ranh giới tiền
#    của lượt chạy v3 nằm ở `platform_core/workflow/`.

__all__ = ["discover_tools", "resolve_params_schema", "validate_tool_params",
           "validate_plan"]
