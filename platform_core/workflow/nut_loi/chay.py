"""Kết quả của một node INLINE, và sổ đăng ký bộ thi hành.

⭐ Tách khỏi `nut_loi/__init__.py` để các tệp node (`dieu_huong.py`,
   `foreach.py`…) import `KetQua` mà **không** import ngược vào gói cha đang
   nạp dở — vòng import là cách im lặng nhất để một node biến mất khỏi palette.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class KetQua:
    """Một lượt chạy inline nói ĐÚNG bốn điều, không hơn.

    - `sang`     trạng thái node sau lượt này (`SUCCEEDED` | `FAILED` | `WAITING`).
    - `output`   `output_ref` của ảnh chụp — chỉ cổng ra THẬT, không khoá `_`.
    - `nhanh`    tên nhánh đã chọn (§5.4). Rỗng ⇒ **không cạnh CONTROL nào**
                 kích hoạt; đó là một kết quả hợp lệ, không phải một lỗi.
    - `dung_run` khác rỗng ⇒ kết thúc CẢ run ở trạng thái đó (`core.stop`).

    ⛔ Không có trường "chi phí": node inline không tiêu tiền. Ngày một node
       inline cần tiêu tiền, nó phải thành `thi_hanh="job"` chứ không phải thêm
       một cột ở đây — vì bút toán sống ở `cau_noi`, không ở động cơ.
    """

    sang: str = "SUCCEEDED"
    output: dict = field(default_factory=dict)
    nhanh: str = ""
    dung_run: str = ""
    error: str = ""


__all__ = ["KetQua"]
