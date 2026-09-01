"""
Uvicorn entrypoint (P3).

Always binds to loopback (127.0.0.1) by default — per AGENTS.md, "Public
ports are 80/443 through the reverse proxy. Application ports bind to
127.0.0.1." The reverse proxy (Caddy, ADR-007) is the only intended
public-facing surface; this process is never meant to be reachable
directly in production.
"""
from __future__ import annotations

import os

import uvicorn

from server.app import create_app
from platform_core import to_tien
from platform_core.observability import configure_logging


def _ai_dang_nghe(host: str, port: int) -> str | None:
    """PID đang nghe `port`, hoặc None nếu cổng trống.

    Dò bằng **connect**, không phải bind: bind rồi đóng để nhường cho uvicorn là
    một cuộc đua.
    """
    import socket
    import subprocess
    dich = "127.0.0.1" if host in ("0.0.0.0", "::", "") else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.5)
        if s.connect_ex((dich, port)) != 0:
            return None
    try:
        r = subprocess.run(["netstat", "-ano", "-p", "TCP"],
                           capture_output=True, text=True, timeout=20)
        for d in r.stdout.splitlines():
            p = d.split()
            if len(p) >= 5 and p[3] == "LISTENING" and p[1].endswith(f":{port}"):
                return p[4]
    except (OSError, subprocess.SubprocessError):
        pass
    return "?"


configure_logging(component="server")
app = create_app()

if __name__ == "__main__":
    host = os.environ.get("LTT_SERVER_HOST", "127.0.0.1")
    port = int(os.environ.get("LTT_SERVER_PORT", "8100"))

    # Chụp tổ tiên NSSM ở ĐÂY chứ không trong `create_app()`: đây là điểm vào của
    # dịch vụ thật, còn `create_app()` bị mọi phép kiểm gọi — và mỗi lượt chụp là
    # một lần khởi động PowerShell (~0,3 s).
    #
    # ⛔ Và không lười khởi tạo: chụp SAU khi vỏ bọc đã chết sẽ thấy một cây
    #    không có `nssm`, kết luận "đang chạy tay", rồi im lặng mãi. Xem `to_tien`.
    to_tien.khoi_tao()

    # 🔴 CỔNG ĐÃ CÓ NGƯỜI GIỮ = DỪNG NGAY, NÓI TO.
    #
    #    Đo trên máy B 01/09: vỏ bọc NSSM chết ⇒ tiến trình con sống sót mồ côi,
    #    giữ cổng, và bản mới không bind được. Dịch vụ đứng ở `Paused` **không
    #    một lời giải thích**, trong khi `/health` của con mồ côi vẫn trả 200.
    #
    #    Chỗ này không sửa được cái xanh giả đó — `/health/ready` lo phần ấy. Nó
    #    biến một `Paused` câm thành một dòng gọi đúng tên thủ phạm.
    giu = _ai_dang_nghe(host, port)
    if giu is not None:
        raise SystemExit(
            f"CONG {port} DA CO NGUOI GIU (pid {giu}) -- KHONG khoi dong. "
            f"Nhieu kha nang la mot tien trinh MO COI song sot sau khi vo boc "
            f"NSSM chet; /health cua no VAN XANH, dung tin. "
            f"Xu ly: Stop-Process -Id {giu} -Force  roi  "
            f"Start-Service LTTStudioWeb")

    uvicorn.run(app, host=host, port=port)
