"""Miền Tìm kiếm liên thực thể của khu quản trị.

Đây là thứ mở khoá mục **B** của `24_DEFERRED_POST_MVP.md`. Mục đó không nói
"chưa làm vì hết giờ"; nó nói **chưa có read-model**, và kèm một luật:

    ⛔ Không làm ô nhận cả đơn hàng/log rồi trả rỗng. Một ô hứa nhiều hơn nó làm
       được là một lỗi vận hành, không phải một thiếu sót thẩm mỹ.

`platform_core/admin_console.tim_lien_thuc_the()` nay là read-model đó, nên ô
tìm ở thanh trên được nới **đúng bằng** năm loại nó tra được — không hơn một
loại nào. Nhãn của ô liệt kê đúng năm thứ ấy.

⭐ Một kết quả thì đi thẳng. Bắt người đang xử sự cố bấm thêm một lần vào một
   danh sách có đúng một dòng là một bước thừa ở đúng lúc họ không có thời gian.

Hợp đồng trang: `docs/admin_mvp_v3/05_PAGE_CONTRACT_MATRIX.md` P2 (cùng miền
Khách hàng — nó là cửa vào, không phải một nơi chốn).
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqladmin import BaseView, expose

from platform_core import admin_console
from platform_core.db import get_session
from server.routes.admin._chung import AnTrongMenuSqlAdmin


class TimKiemView(AnTrongMenuSqlAdmin, BaseView):
    """Một chuỗi → năm loại thực thể → một đích."""

    name = "Tìm"
    icon = "fa-solid fa-magnifying-glass"

    @expose("/tim", methods=["GET"])
    async def trang(self, request: Request):
        from server.admin import _admin_shell
        from server.templating import templates

        q = (request.query_params.get("q") or "").strip()

        gen = get_session()
        db = next(gen)
        try:
            ket_qua = admin_console.tim_lien_thuc_the(db, q)
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

        # Một kết quả duy nhất trên toàn bộ năm loại ⇒ đi thẳng tới nó.
        if ket_qua["tong"] == 1:
            return RedirectResponse(ket_qua["nhom"][0]["dong"][0]["href"],
                                    status_code=303)

        than = templates.env.get_template("admin/tim_kiem.html").render(
            **ket_qua, toi_thieu=admin_console.TIM_TIEN_TO_TOI_THIEU,
            moi_loai=admin_console.TIM_MOI_LOAI)

        return HTMLResponse(_admin_shell(
            f"Tìm: {q}" if q else "Tìm", "tim_kiem", than,
            tieu_de="Kết quả tìm",
            # Mô tả này người VẬN HÀNH đọc, không phải người sửa mã — nên nó
            # nói phạm vi, không nói tên hàm. Lý do kỹ thuật ở docstring của
            # `admin_console.tim_lien_thuc_the`.
            mo_ta="Khách hàng · đơn nạp · job · lời gọi API · khoá của khách. "
                  "Tra theo định danh, không tìm toàn văn trong nội dung.",
            q_khach=q))


#: Các view của miền này. `setup_admin` lặp trên `server.routes.admin.VIEWS`.
VIEWS = (TimKiemView,)
