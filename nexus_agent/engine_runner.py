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
from pathlib import Path

from nexus_agent import engine

log = logging.getLogger("nexus_agent")

#: Nơi bản cài chính thức đặt rustdesk.exe. Cho đổi bằng biến môi trường để bản
#: đóng gói riêng (fork LTT, Rổ 2) trỏ tới chỗ khác mà không sửa code.
EXE_MAC_DINH = r"C:\Program Files\RustDesk\rustdesk.exe"

#: Điểm hẹn + relay của LTT (Q96). Khoá là khoá CÔNG KHAI của máy chủ — client
#: cần nó để không bị đứng giữa; **không bí mật**, nhúng thẳng được. Cho đổi bằng
#: biến môi trường để bản fork/hạ tầng khác trỏ nơi khác.
SERVER_MAC_DINH = "45.76.185.75"
KEY_MAC_DINH = "A1MZFm2igQwZ29CMGYlhmjP7JI3yXzpc0qV17IqFndI="

#: Hai bộ config RustDesk2.toml (V1: bộ DỊCH VỤ mới là bộ phục vụ truy cập không
#: giám sát; chỉ sửa bộ người dùng thì dịch vụ vẫn trỏ về rs-ny.rustdesk.com).
_CONFIG_DICH_VU = (r"C:\Windows\ServiceProfiles\LocalService\AppData\Roaming"
                   r"\RustDesk\config\RustDesk2.toml")


def duong_exe() -> str:
    return os.environ.get("LTT_NEXUS_RUSTDESK_EXE", "").strip() or EXE_MAC_DINH


def _server_key() -> tuple:
    s = os.environ.get("LTT_NEXUS_RELAY_SERVER", "").strip() or SERVER_MAC_DINH
    k = os.environ.get("LTT_NEXUS_RELAY_KEY", "").strip() or KEY_MAC_DINH
    return s, k


def duong_config() -> list:
    """Hai đường RustDesk2.toml cần sửa. Bộ người dùng theo `%APPDATA%`."""
    ds = [_CONFIG_DICH_VU]
    appdata = os.environ.get("APPDATA", "").strip()
    if appdata:
        ds.append(str(Path(appdata) / "RustDesk" / "config" / "RustDesk2.toml"))
    return ds


def _svc(action: str) -> None:
    """Dừng/khởi động dịch vụ RustDesk. Cần admin (Q99) — nếu thiếu, chỉ log."""
    try:
        subprocess.run(["sc", action, "RustDesk"], capture_output=True,
                       text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("khong %s duoc dich vu RustDesk: %s", action, exc)


def cau_hinh_server(server: str | None = None, key: str | None = None) -> int:
    """Trỏ RustDesk (nguyên bản) về hạ tầng LTT — không sửa binary (Rổ 1/V1).

    Idempotent (`engine.noi_dung_config` không nhân dòng), nên gọi mỗi lần khởi
    động agent là an toàn. **Phải dừng dịch vụ trước khi sửa** (V1 bẫy 2: dịch vụ
    ghi đè config lúc thoát), rồi bật lại. Trả số file đã ghi.

    Với bản fork LTT (Rổ 2) đã nhúng sẵn config thì hàm này thừa — nhưng vô hại,
    và nó giữ cho đường **stock client** (chạy thử nội bộ) hoạt động ngay không cần
    fork. Không tìm thấy config nào (RustDesk chưa cài) → trả 0, không ném.
    """
    srv, k = (server or _server_key()[0]), (key or _server_key()[1])
    duong = [d for d in duong_config() if Path(d).exists()]
    if not duong:
        log.info("chua thay config RustDesk — bo qua cau hinh server")
        return 0

    _svc("stop")
    enc = _ghi_khong_bom
    n = 0
    for d in duong:
        try:
            cu = Path(d).read_text(encoding="utf-8", errors="replace").splitlines()
            moi = engine.noi_dung_config(cu, srv, k)
            enc(d, moi)
            n += 1
        except OSError as exc:
            log.warning("khong ghi duoc config %s: %s", d, exc)
    _svc("start")
    log.info("da tro RustDesk ve %s (%d file)", srv, n)
    return n


def _ghi_khong_bom(duong: str, noi_dung: str) -> None:
    """Ghi UTF-8 KHÔNG BOM (bài học CLAUDE.md mục 1: BOM làm parser TOML/JSON vỡ)."""
    Path(duong).write_bytes(noi_dung.encode("utf-8"))


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
