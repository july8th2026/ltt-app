"""LTT VPS — bán máy chủ ảo Windows chạy trên Proxmox (Q103 + Q104).

Đây là một **app**, không phải năng lực nền tảng: mọi thứ ở đây thuộc về sản phẩm
VPS, không thuộc về tài khoản. Vì vậy cờ bật/tắt sống ở chính app này chứ không ở
`platform_core/` (khác Nexus — danh tính thiết bị thuộc tài khoản nên phải nằm ở
nền tảng).

## Fail-closed, và vì sao ở đây nó quan trọng hơn mọi app khác

Cờ mặc định **TẮT**. Một app AI bật nhầm thì tốn tiền API. Một app VPS bật nhầm
thì có người lạ tạo được máy ảo trên phần cứng ở nhà, có cổng ra Internet, và
mình chịu trách nhiệm về những gì máy đó làm. Sai lầm đầu tiên là sai lầm cuối cùng.

Có **hai** lớp chặn, như Nexus: `MANIFEST.enabled` quyết định app có hiện trong
catalog không; `routes.py` kiểm lại lần nữa để một URL gõ thẳng cũng không trả lời.
Một lớp là chỗ để quên.
"""
from __future__ import annotations

import os
from collections.abc import Mapping

#: Cờ bật/tắt toàn bộ app VPS. Thiếu biến hoặc giá trị lạ → TẮT.
FLAG_ENV = "LTT_VPS"

_BAT = ("1", "true", "yes", "on")
ROLLOUT_ENV = "LTT_VPS_ROLLOUT"
ROLLOUT_USER_IDS_ENV = "LTT_VPS_USER_IDS"


def enabled(env: dict | None = None) -> bool:
    """App VPS có đang bật không. Mặc định TẮT."""
    source = os.environ if env is None else env
    return str(source.get(FLAG_ENV, "")).strip().lower() in _BAT


def rollout_mode(env: Mapping[str, str] | None = None) -> str:
    """off/admin/allowlist/public, with a fail-closed production default."""
    source = os.environ if env is None else env
    configured = source.get(ROLLOUT_ENV)
    if configured is not None:
        mode = str(configured).strip().lower()
        return mode if mode in {"off", "admin", "allowlist", "public"} else "off"
    return "off" if str(source.get("LTT_ENV", "")).strip().lower() in {
        "production", "prod"} else "public"


def access_allowed(user, env: Mapping[str, str] | None = None) -> bool:
    """Authorize by canonical user ID; email is deliberately not an input."""
    source = os.environ if env is None else env
    mode = rollout_mode(source)
    role = str(getattr(user, "role", "") or "")
    user_id = str(getattr(user, "id", "") or "")
    if not user_id:
        return False
    if mode == "public":
        return True
    if mode == "admin":
        return role == "admin"
    if mode == "allowlist":
        allowed = {value.strip() for value in str(source.get(
            ROLLOUT_USER_IDS_ENV, "")).split(",") if value.strip()}
        return role == "admin" or user_id in allowed
    return False


__all__ = [
    "FLAG_ENV", "ROLLOUT_ENV", "ROLLOUT_USER_IDS_ENV", "access_allowed",
    "enabled", "rollout_mode",
]
