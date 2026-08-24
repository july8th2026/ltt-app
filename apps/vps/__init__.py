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

#: Cờ bật/tắt toàn bộ app VPS. Thiếu biến hoặc giá trị lạ → TẮT.
FLAG_ENV = "LTT_VPS"

_BAT = ("1", "true", "yes", "on")


def enabled(env: dict | None = None) -> bool:
    """App VPS có đang bật không. Mặc định TẮT."""
    source = os.environ if env is None else env
    return str(source.get(FLAG_ENV, "")).strip().lower() in _BAT


__all__ = ["FLAG_ENV", "enabled"]
