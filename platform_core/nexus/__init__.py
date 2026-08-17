"""LTT Nexus — danh tính thiết bị và uỷ quyền phiên điều khiển từ xa (Q93).

Đây là **platform capability**, không phải một app trong `apps/`: danh tính thiết
bị thuộc về **tài khoản**, không thuộc app, và app không được cấp phát credential
toàn hệ thống (`AGENTS.md` 8.4). Tiền lệ đúng là Q92.

Ranh giới của gói này, và nó hẹp có chủ ý:

* **có** — thiết bị là của ai, có được tin không, đang online không, ai được mở
  phiên vào nó, và việc đó đã được ghi lại chưa;
* **không** — không bắt màn hình, không truyền dữ liệu, không biết engine nào
  đang chạy. Luồng điều khiển **không bao giờ** đi qua control plane (Q93 ràng
  buộc 3), nên không có một dòng nào ở đây chạm tới nó.

Nhờ ranh giới đó, gói này **giống nhau dù engine là RustDesk, MeshCentral hay
WebRTC tự viết** — và đó là lý do nó được làm trước, trong lúc quyết định hạ
tầng relay (D2) và legal review AGPL còn đang mở.
"""
from __future__ import annotations

#: Cờ bật/tắt toàn bộ Nexus. Mặc định TẮT (Q93 fail-closed): cờ tắt thì không
#: thiết bị nào ghép được. Một bề mặt cho phép điều khiển máy người khác mà mặc
#: định mở thì sai lầm đầu tiên là sai lầm cuối cùng.
FLAG_ENV = "LTT_NEXUS"


def enabled(env: dict | None = None) -> bool:
    """Nexus có đang bật không. Thiếu biến, giá trị lạ → TẮT."""
    import os

    source = os.environ if env is None else env
    return str(source.get(FLAG_ENV, "")).strip().lower() in ("1", "true", "yes", "on")


__all__ = ["FLAG_ENV", "enabled"]
