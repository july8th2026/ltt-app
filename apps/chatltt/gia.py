"""gia.py — `credit_cost` của ChatLTT, phân nhánh theo VIỆC. (H44 B6 bước 3)

## Vì sao cần tệp này

`registry.credit_for()` gọi `manifest.credit_cost(params)` — **một** hàm cho cả
app, và chữ ký **không** mang `job_type`. Tới B6 ChatLTT có hai loại job
(`trich_tep`, `nghien_cuu`) với hai cách tính hoàn toàn khác nhau, nên phải có
một chỗ phân nhánh.

## ⛔ Phân nhánh theo KHOÁ KHAI, không theo hình dạng dữ liệu

Cách dễ là *"có `tep_id` thì là trích, có `cau_hoi` thì là nghiên cứu"*. Đó đúng
cái §2 D1 của B6 cấm — và cấm vì một lỗi thật (`gpt-researcher` #1846 suy trạng
thái từ `len(raw_content) > 100`). Một hình dạng dữ liệu **không phải** một
trạng thái; ngày một tham số đổi tên, giá nhảy sang nhánh khác mà không ai biết.

⭐ Tiền lệ trong chính kho này làm đúng: `apps/autosubvideo/manifest.py::_cost`
   phân nhánh theo `params["operation"]` — một khoá **được khai** trong
   `params_schema`, nên `validate_tool_params` điền mặc định và không ai phải
   nhớ truyền nó.

## Không khai ⇒ NÉM, không đoán

Cùng luật `chieu_tool.lop_chinh_sach` (không khai ⇒ `DESTRUCTIVE`): mặc định
phải là phía **ngặt nhất**. Một việc mới quên khai `viec` thì hậu quả là *"job
không nộp được"* — phiền, sửa trong một dòng. Đoán bừa thì hậu quả là *"job chạy
với giá của việc khác"*, và cái đó không sửa lại được sau khi đã thu.
"""
from __future__ import annotations

from apps.chatltt import gia_nghien_cuu as _gia_nc, gia_trich as _gia_trich

#: Khoá phân loại. Khai trong `params_schema` của **mọi** tool của app này.
KHOA_VIEC = "viec"

VIEC_TRICH = "trich_tep"
VIEC_NGHIEN_CUU = "nghien_cuu"

#: Việc → hàm tính giá. Bánh cóc `test_841` chốt rằng bảng này phủ đúng
#: `MANIFEST.job_types`, không thiếu và không thừa.
BANG_GIA = {
    VIEC_TRICH: _gia_trich.credit_cost,
    VIEC_NGHIEN_CUU: _gia_nc.credit_cost,
}


class ViecLa(ValueError):
    """`viec` không có trong `BANG_GIA`. Fail-closed — xem docstring."""


def credit_cost(params: dict) -> int:
    viec = str((params or {}).get(KHOA_VIEC) or "").strip()
    ham = BANG_GIA.get(viec)
    if ham is None:
        raise ViecLa(
            f"khong biet tinh gia cho viec {viec!r} — khai no trong "
            f"`params_schema` va them vao `apps/chatltt/gia.py::BANG_GIA`")
    return int(ham(params))
