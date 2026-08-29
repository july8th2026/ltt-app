"""Miền Hệ thống: tình trạng nền tảng + khu dữ liệu thô (Data Explorer).

Hợp đồng trang: `docs/admin_mvp_v3/05_PAGE_CONTRACT_MATRIX.md` P10.

⛔ Đây KHÔNG phải một bộ observability. Ảnh mockup vẽ uptime 30 ngày, P95 từng
   dịch vụ, Redis, Object Storage, "Worker 32/32", queue depth và lịch bảo trì —
   nền tảng không có nguồn cho một cái nào trong số đó. Trang này chỉ hiện thứ
   đọc được thật: bảng `platform_info`, và đường dẫn tới `/status` (đã có sẵn,
   có authority riêng).
"""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import HTMLResponse
from sqladmin import BaseView, expose

from platform_core.db import get_session
from server.routes.admin._chung import AnTrongMenuSqlAdmin

_log = logging.getLogger(__name__)

#: Các bảng thô của SQLAdmin, và vai trò của từng bảng.
#:
#: ⭐ Danh sách này là **nội dung** của khu Data Explorer, không phải điều hướng
#:    thứ hai: nó nói *bảng nào có gì và dùng để làm gì*, thứ mà thanh bên trần
#:    của SQLAdmin (chỉ có tên bảng) không nói được. Ba bảng đã lên thanh bên
#:    chính (`credit-entry`, `job`, `nhat-ky-admin`) cố ý KHÔNG có ở đây —
#:    chúng là workflow chính, không phải dữ liệu thô.
BANG_THO = (
    ("/admin/user/list", "Người dùng",
     "Bảng tài khoản. Đây cũng là nơi đổi vai trò và vô hiệu hoá tài khoản — "
     "hai thao tác đó có ghi nhật ký admin."),
    ("/admin/session/list", "Phiên đăng nhập",
     "Xoá một dòng = thu hồi đúng phiên đó. Thu hồi TẤT CẢ phiên của một khách "
     "thì làm ở Hồ sơ 360, nơi thao tác được ghi nhật ký."),
    ("/admin/app-access/list", "Quyền app",
     "Quyền riêng của từng khách với từng app."),
    ("/admin/api-key/list", "Provider credentials (bảng thô)",
     "Bảng dữ liệu thô của kho khoá nền tảng. Chỗ làm việc là Vận hành → "
     "Provider Credentials; ở đây không tạo được key."),
    ("/admin/platform-info/list", "Thông tin nền tảng",
     "Phiên bản và thời điểm cài đặt."),
)


class HeThongView(AnTrongMenuSqlAdmin, BaseView):
    """Tình trạng nền tảng — chỉ sự thật đọc được."""

    name = "Hệ thống"
    icon = "fa-solid fa-server"

    @expose("/he-thong", methods=["GET"])
    async def he_thong(self, request: Request):
        from platform_core.models import PlatformInfo
        from server.admin import _admin_shell
        from server.templating import templates

        gen = get_session()
        db = next(gen)
        try:
            thong_tin = db.query(PlatformInfo).order_by(
                PlatformInfo.installed_at.desc()).first()
        except Exception as exc:
            # Trang vẫn mở được khi không đọc được bảng, nhưng lý do phải đi vào
            # log — nuốt nó là làm lỗi biến mất ở đúng chỗ khó tìm nhất.
            _log.warning("Trang He thong: khong doc duoc platform_info: %s", exc)
            thong_tin = None
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

        than = templates.env.get_template("admin/he_thong.html").render(
            thong_tin=thong_tin, bang_tho=BANG_THO)
        return HTMLResponse(_admin_shell(
            "Hệ thống", "he_thong", than,
            tieu_de="Hệ thống",
            mo_ta="Thông tin nền tảng và đường vào dữ liệu thô."))


class NangCaoView(AnTrongMenuSqlAdmin, BaseView):
    """Mục lục khu dữ liệu thô.

    Thanh bên của SQLAdmin liệt kê tên bảng và không gì khác. Trang này nói mỗi
    bảng dùng để làm gì, và **cái gì KHÔNG nên làm ở đó** — vì cả năm bảng đều
    sửa/xoá được, và ba trong số đó là dữ liệu tiền hoặc an ninh.
    """

    name = "Nâng cao"
    icon = "fa-solid fa-database"

    @expose("/nang-cao", methods=["GET"])
    async def nang_cao(self, request: Request):
        from server.admin import _admin_shell
        from server.templating import templates

        than = templates.env.get_template("admin/nang_cao.html").render(
            bang_tho=BANG_THO)
        return HTMLResponse(_admin_shell(
            "Nâng cao", "nang_cao", than,
            tieu_de="Nâng cao / Data Explorer",
            mo_ta="Bảng dữ liệu thô. Dùng để tra cứu và sửa chữa, không phải để "
                  "làm việc hằng ngày — mỗi bảng có một trang nghiệp vụ tương "
                  "ứng an toàn hơn."))


VIEWS = (HeThongView, NangCaoView)
