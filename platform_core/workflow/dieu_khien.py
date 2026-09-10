"""Tám loại node ĐIỀU KHIỂN — chạy trong scheduler, KHÔNG sinh Job (`G15`).

🔴 Khiếm khuyết đang có: hôm nay mỗi bước đều đi qua hàng đợi job, nên một node
   `IF` cũng sinh một job — và **một job là một bút toán**. Rẽ nhánh tạo một
   dòng trong sổ tiền, dù nó chỉ so sánh hai giá trị.

⇒ Tám loại dưới đây chạy **trong** vòng scheduler: không hàng đợi, không lease,
  không bút toán. Chúng là *luồng điều khiển*, không phải *việc*.
"""
from __future__ import annotations

#: Tám loại, và con số **tám** là một phần của hợp đồng: thêm loại thứ chín là
#: một quyết định kiến trúc (nó chạy trong lõi, tức nó không thể là một app),
#: không phải một lần thêm dòng.
LOAI_DIEU_KHIEN = frozenset({
    "IF",       # re nhanh theo dieu kien
    "SWITCH",   # re nhieu nhanh theo gia tri
    "MERGE",    # gom nhieu duong ve mot
    "FOREACH",  # lap tren mot tap
    "JOIN",     # cho nhieu nhanh (ALL / ANY / N-of-M)
    "DELAY",    # cho mot khoang thoi gian
    "SET_VAR",  # dat bien trong pham vi run
    "NOOP",     # cho giu cho / diem neo
})


def sinh_job(loai_node: str) -> bool:
    """Node loại này có sinh một Job trong hàng đợi không?

    ⚠️ Mặc định là **có**. Một loại lạ phải sinh job, vì bỏ sót một job là bỏ
       sót một **bút toán**, còn thêm một job thừa chỉ là chậm. Sai số đẩy về
       phía an toàn của **sổ sách**, không phải phía an toàn của hiệu năng.
    """
    return loai_node not in LOAI_DIEU_KHIEN
