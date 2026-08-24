"""
llm_gateway — cổng VLM chạy trên MÁY B, biến model nhà thành một API dùng được.

Nền tảng (máy A), Codex và Claude Code gọi tới đây y như gọi một nhà cung cấp API
bên ngoài. Bên trong, cổng đẩy sang `llama-swap` ở `127.0.0.1`, và llama-swap bật
đúng hồ sơ `llama-server` cần thiết.

    [3] llm_gateway  :8299  (module này — nghe LAN, có bearer)
          v loopback
    [2] llama-swap   :8280  (vòng đời model, ttl tự nhả VRAM)
          v loopback
    [1] llama-server :8281  (CHỈ 127.0.0.1)

⛔ RANH GIỚI KIẾN TRÚC (Q102) — giống hệt `render_gateway`: module này **không**
   biết gì về nền tảng. Không mật khẩu CSDL, không khoá R2, không khoá mã hoá,
   không mô hình người dùng. Nó chỉ biết: token bearer, danh mục model, ngân sách.

⛔ `llama-server` KHÔNG có xác thực. Nó chỉ được nghe `127.0.0.1`, vĩnh viễn. Chỉ
   cổng này nghe LAN, và tường lửa chỉ mở cho máy A (192.168.2.17).

⛔ BẬN THÌ TRẢ **429**, KHÔNG PHẢI LỖI. Nếu máy A hiểu nhầm bận thành lỗi thì
   `api_pool` sẽ cooldown rồi `disable` key `ltt_llm` sau 5 lần — và một tối
   máy B chạy video sẽ **tự tắt vĩnh viễn model nhà**. Cạm bẫy này đã ghi ở D-005
   cho cổng render; nó áp dụng y nguyên ở đây.

Mã nguồn nằm trong repo LTTSTUDIOSAPP và deploy sang máy B bằng script — **không
bao giờ sửa tay tại chỗ**.
"""
from __future__ import annotations

__all__ = ["__version__"]

#: Đổi khi hợp đồng HTTP đổi. `/health` trả về để script nghiệm thu so với repo.
__version__ = "0.1.0"
