"""tim.py — tra một năng lực theo **tên tool ổn định**, không theo tên app.

Nền tảng không được biết app nào tồn tại (`registry.py` câu mở đầu; test_60
chốt). Nên đường duy nhất từ một cái tên như `text.chat` tới bản khai của nó
là đi qua `registry.discover()` và so `ToolSpec.name`.
"""
from __future__ import annotations

from typing import Tuple

from platform_core import registry as _reg
from platform_core.registry import AppManifest, ToolSpec


class KhongCoNangLuc(LookupError):
    """Không có tool nào mang tên này trong một app **đang bật**.

    Fail-closed: một tên lạ, hay tool của một app đã tắt/lỗi nạp, đều là
    "không có" — không có nhánh nào trả về một tool "gần đúng".
    """


def tim_tool(tool_name: str) -> Tuple[AppManifest, ToolSpec]:
    """`(manifest, tool)` của tool tên `tool_name`. Ném `KhongCoNangLuc`."""
    ten = str(tool_name or "")
    # Tra qua thuộc tính module, không bind tên lúc import: bộ test cắm app thử
    # bằng `monkeypatch.setattr(registry, "discover", ...)` (khuôn `conftest.app_thu`).
    for loaded in _reg.discover():
        if loaded.error or not loaded.manifest.enabled:
            continue
        for spec in loaded.manifest.tools:
            if spec.name == ten:
                return loaded.manifest, spec
    raise KhongCoNangLuc(f"khong co nang luc {ten!r}")
