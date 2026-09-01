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

# 🔴 PHẢI Ở MỨC MODULE, KHÔNG PHẢI TRONG `if __name__ == "__main__"`.
#
#    NSSM khởi động dịch vụ bằng `python -m uvicorn server.run:app`, tức tệp này
#    được **import** và `__main__` **không bao giờ chạy**. Bản đầu tôi đặt lời
#    gọi trong `__main__` và nó nằm trong mã chết suốt — production trả về
#    `"chua goi khoi_tao() luc khoi dong ung dung"` sau khi deploy.
#
# ⭐ Và đó chính là lý do `to_tien.trang_thai()` **từ chối tự chụp muộn**: nếu nó
#    lười khởi tạo thì trường này đã im lặng chụp ở lượt gọi `/health/ready` đầu
#    tiên, cho ra một câu trả lời **trông hoàn toàn bình thường**, và lỗi wiring
#    này sẽ không bao giờ lộ ra. Một phép đo thành thật về sự vắng mặt của chính
#    nó đã bắt được lỗi của người viết ra nó.
#
# ⚠️ Cái giá: hai phép kiểm import `server.run` nay trả thêm ~0,3 s cho một lượt
#    gọi PowerShell. Chấp nhận được — `create_app()` (thứ mọi phép kiểm khác
#    dùng) vẫn không đụng tới.
to_tien.khoi_tao()

if __name__ == "__main__":
    host = os.environ.get("LTT_SERVER_HOST", "127.0.0.1")
    port = int(os.environ.get("LTT_SERVER_PORT", "8100"))

    # ⚠️ CHỐT CỔNG NÀY CHỈ CHE ĐƯỜNG `python server/run.py` TRỰC TIẾP.
    #
    #    Dưới NSSM thì uvicorn là bên bind, và nó tự báo lỗi bind của nó. Không
    #    đưa chốt này lên mức module được: hai phép kiểm import `server.run`, và
    #    cổng 8100 lúc đó **đang có production giữ** ⇒ chốt sẽ giết chúng.
    #
    #    Nên giá trị của nó ở đây nhỏ hơn bản máy B (nơi cổng tự chạy `main()`).
    #    Phần bắt mồ côi thật sự nằm ở `/health/ready` → `duoi_dich_vu`.
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
