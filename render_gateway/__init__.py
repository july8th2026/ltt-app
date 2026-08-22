"""
render_gateway — cổng render chạy trên MÁY B, biến GPU nhà thành một API.

Nền tảng (máy A) gọi tới đây y như gọi một nhà cung cấp API bên ngoài. Bên trong,
cổng này dựng workflow JSON rồi đẩy sang ComfyUI ở `127.0.0.1:8188`.

⛔ RANH GIỚI KIẾN TRÚC (Q102): module này **không được** biết gì về nền tảng —
   không mật khẩu CSDL, không khoá R2, không khoá mã hoá, không mô hình người dùng.
   Ảnh vào bằng presigned GET, ảnh ra bằng presigned PUT. Máy A cấp cả hai vé.

⛔ ComfyUI KHÔNG có xác thực. Nó chỉ được nghe `127.0.0.1`, vĩnh viễn. Chỉ cổng này
   nghe LAN, có bearer token, và tường lửa chỉ mở cho máy A.

Mã nguồn nằm trong repo LTTSTUDIOSAPP và deploy sang máy B bằng script — **không
bao giờ sửa tay tại chỗ** (cùng khuôn `codex_sidecar/`).
"""
from __future__ import annotations

__all__ = ["__version__"]

#: Đổi khi hợp đồng HTTP đổi. `/health` trả về để `kiem_tra.ps1` so với repo.
__version__ = "0.1.0"
