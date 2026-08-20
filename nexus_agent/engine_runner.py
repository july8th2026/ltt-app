"""Nối `nexus_agent.engine` (hàm thuần) với RustDesk thật trên máy khách.

`engine.py` chỉ dựng lệnh/nội dung — cố ý không chạm hệ thống, để test được. File
này là lớp mỏng còn lại: chạy lệnh thật bằng `subprocess`, tìm `rustdesk.exe`, và
gói lại thành một đối tượng có `chuan_bi_phien()` mà `NexusClient` gọi mỗi khi có
vé mới (W4).

**Chạy với quyền admin (Q99):** `xoay_mat_khau` gọi `--password`, đòi admin (V8).
Agent điều khiển không giám sát chạy như service/task admin, nên lớp này cũng vậy.
Nếu thiếu quyền, `engine.dat_mat_khau` ném thông điệp rõ (không nuốt lặng).
"""
from __future__ import annotations

import logging
import os
import subprocess

from nexus_agent import engine

log = logging.getLogger("nexus_agent")

#: Nơi bản cài chính thức đặt rustdesk.exe. Cho đổi bằng biến môi trường để bản
#: đóng gói riêng (fork LTT, Rổ 2) trỏ tới chỗ khác mà không sửa code.
EXE_MAC_DINH = r"C:\Program Files\RustDesk\rustdesk.exe"


def duong_exe() -> str:
    return os.environ.get("LTT_NEXUS_RUSTDESK_EXE", "").strip() or EXE_MAC_DINH


def _runner(argv: list) -> tuple:
    """Chạy một lệnh, trả `(returncode, stdout+stderr)`.

    Timeout để một `rustdesk.exe` treo (đã thấy khi nó lỡ mở GUI — V4) không giữ
    agent mãi. `list` chứ không chuỗi: không đi qua shell nên không có chỗ tiêm.
    """
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 1, "timeout"
    except OSError as exc:
        return 1, f"khong chay duoc: {exc}"


class RustDeskEngine:
    """Engine thật: mỗi phiên xoay một mật khẩu mới, trả kèm ID để báo lên server."""

    def __init__(self, exe: str | None = None):
        self.exe = exe or duong_exe()

    def chuan_bi_phien(self) -> tuple:
        """Xoay mật khẩu + lấy ID cho một phiên mới. Trả `(engine_id, secret)`.

        Thứ tự: lấy ID trước (không đặc quyền, ít hỏng) rồi mới xoay mật khẩu
        (đặc quyền). Nếu xoay hỏng thì ném — `NexusClient` bọc lỗi theo từng phiên.
        """
        engine_id = engine.lay_id(self.exe, runner=_runner)
        secret = engine.xoay_mat_khau(self.exe, runner=_runner)
        return engine_id, secret


__all__ = ["EXE_MAC_DINH", "RustDeskEngine", "duong_exe"]
