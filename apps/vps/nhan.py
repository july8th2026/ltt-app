"""Nhãn người đọc cho các mã trạng thái của máy.

## Vì sao có file riêng thay vì viết thẳng trong template

`trang_thai` là **mã trong CSDL** — `dang_chay`, `bi_treo`, `da_xoa`. Hiện nguyên
mã đó ra trang là bắt khách đọc thứ được viết cho máy đọc; và một khách nhìn thấy
`bi_treo` không biết máy còn dữ liệu hay đã mất, không biết phải làm gì tiếp.

Đặt ở đây, không trong template, vì **hai trang cùng hiện trạng thái này**
(`vps.html` và `vps_chi_tiet.html`). Hai bản sao của cùng một bảng nhãn thì lần
sửa sau chỉ sửa một bản, và trang còn lại nói một câu khác về cùng một máy.

Nhãn khai bằng `N_()` — **đánh dấu để trích, không dịch ngay**. Gọi `_()` ở đây
sẽ đóng băng ngôn ngữ theo lần nạp module đầu tiên, tức mọi người dùng đều thấy
ngôn ngữ của người vào trước nhất. Dịch thật xảy ra lúc hiển thị, trong template.
"""
from __future__ import annotations

from platform_core.i18n import N_

#: Mã trong CSDL → câu người đọc.
TRANG_THAI = {
    "dang_tao": N_("Đang tạo"),
    "dang_chay": N_("Đang chạy"),
    "da_tat": N_("Đã tắt"),
    "bi_treo": N_("Bị tạm dừng"),
    "loi": N_("Lỗi"),
    "da_xoa": N_("Đã xoá"),
}


def trang_thai(ma: str) -> str:
    """Nhãn cho một mã trạng thái.

    Mã lạ thì **trả về chính nó**, không trả chuỗi rỗng: một ô trống trên trang
    làm khách tưởng máy không có trạng thái, còn một mã lạ hiện ra ít nhất cho
    ta thứ để tra khi họ chụp màn hình gửi tới.
    """
    ma = str(ma or "").strip()
    return TRANG_THAI.get(ma, ma)
