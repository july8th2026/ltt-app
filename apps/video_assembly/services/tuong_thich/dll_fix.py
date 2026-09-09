"""`fix_torch_dll` — vá đường nạp DLL của torch trên Windows.

Bản của bot thêm `torch/lib` vào đường tìm DLL, vì một số bản CUDA không tự tìm
được. Giữ **chữ ký** và giữ **tính không-ném**: đây là một lớp vá cơ hội, và một
lỗi ở đây không được làm hỏng một job vốn chạy được.
"""
from __future__ import annotations

import logging
import os
import sys

log = logging.getLogger("apps.video_assembly.dll")


def fix_torch_dll() -> bool:
    """`True` nếu đã thêm được đường; `False` nếu không cần hoặc không làm được."""
    if sys.platform != "win32" or not hasattr(os, "add_dll_directory"):
        return False
    try:
        import torch
    except ImportError:
        return False
    thu_muc = os.path.join(os.path.dirname(torch.__file__), "lib")
    if not os.path.isdir(thu_muc):
        return False
    try:
        os.add_dll_directory(thu_muc)
    except OSError as e:
        # Ghi lại rồi đi tiếp: torch có thể vẫn nạp được bằng đường mặc định.
        log.warning("khong them duoc duong DLL %s: %s", thu_muc, e)
        return False
    return True
