"""Miền Khách hàng của khu quản trị.

Đây là ví dụ sống của hợp đồng mở rộng (`04_EXTENSION_CONTRACT.md` §5): thêm một
trang là **hai chỗ trong cùng một tệp miền** — lớp view ở đây, một dòng ở
`_chung.SECTIONS`. Số tệp trung tâm phải sửa: 0.

Hợp đồng trang: `docs/admin_mvp_v3/05_PAGE_CONTRACT_MATRIX.md` P2.
"""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import HTMLResponse
from sqladmin import BaseView, expose

from platform_core import admin_console
from platform_core.db import get_session
from server.routes.admin._chung import AnTrongMenuSqlAdmin


class DanhSachKhachView(AnTrongMenuSqlAdmin, BaseView):
    """Danh sách khách hàng — cửa vào của GJ1.

    Trang này KHÔNG có mutation nào. Mọi thao tác lên một khách (cấp credit, thu
    hồi phiên, đổi vai trò) sống ở Hồ sơ 360, nơi người thao tác nhìn thấy đối
    tượng mình đang tác động. Một nút đỏ trên một dòng của bảng dài là cách bấm
    nhầm hàng — và `05` P2 chốt điều đó thành hợp đồng.
    """

    name = "Khách hàng"
    icon = "fa-solid fa-users"

    @expose("/khach-hang", methods=["GET"])
    async def danh_sach(self, request: Request):
        from server.admin import _admin_shell
        from server.templating import templates

        q = request.query_params
        tim = (q.get("q") or "").strip()
        trang_thai = (q.get("trang_thai") or "").strip()
        xac_thuc = (q.get("xac_thuc") or "").strip()
        sap_xep = (q.get("sap_xep") or "moi").strip()
        try:
            offset = max(0, int(q.get("offset") or 0))
        except ValueError:
            offset = 0

        gen = get_session()
        db = next(gen)
        try:
            trang = admin_console.danh_sach_khach(
                db, tim=tim, trang_thai=trang_thai, xac_thuc=xac_thuc,
                sap_xep=sap_xep, offset=offset)
            chu_y = admin_console.dem_chu_y_khach(db)
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

        def lien_ket_trang(vi_tri: int) -> str:
            tham_so = {k: v for k, v in
                       (("q", tim), ("trang_thai", trang_thai),
                        ("xac_thuc", xac_thuc),
                        ("sap_xep", trang["sap_xep"]
                         if trang["sap_xep"] != "moi" else "")) if v}
            if vi_tri > 0:
                tham_so["offset"] = vi_tri
            return "/admin/khach-hang" + (f"?{urlencode(tham_so)}" if tham_so else "")

        def lien_ket_sap(khoa: str) -> str:
            """Giữ nguyên bộ lọc khi đổi cách sắp — đổi thứ tự mà mất bộ lọc là
            một cách làm mất chỗ người ta đang đứng."""
            tham_so = {k: v for k, v in
                       (("q", tim), ("trang_thai", trang_thai),
                        ("xac_thuc", xac_thuc),
                        ("sap_xep", khoa if khoa != "moi" else "")) if v}
            return "/admin/khach-hang" + (f"?{urlencode(tham_so)}" if tham_so else "")

        than = templates.env.get_template("admin/khach_hang.html").render(
            dong=trang["dong"], tong=trang["tong"], limit=trang["limit"],
            offset=trang["offset"], tim=tim, trang_thai=trang_thai,
            xac_thuc=xac_thuc, chu_y=chu_y, lien_ket_trang=lien_ket_trang,
            sap_xep=trang["sap_xep"], lien_ket_sap=lien_ket_sap)

        return HTMLResponse(_admin_shell(
            "Khách hàng", "khach_hang", than,
            tieu_de="Khách hàng",
            mo_ta="Tìm khách cần hỗ trợ, rồi mở hồ sơ 360 của họ. "
                  "Mọi thao tác lên một khách đều nằm trong hồ sơ đó.",
            q_khach=tim))


#: Các view của miền này. `setup_admin` lặp trên `server.routes.admin.VIEWS`.
VIEWS = (DanhSachKhachView,)
