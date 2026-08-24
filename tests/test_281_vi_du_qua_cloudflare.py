"""Mọi ví dụ mã ta phát ra phải chạy được **qua Cloudflare**, không chỉ ở loopback.

🔴 VÌ SAO TỆP NÀY TỒN TẠI — MỘT LỖI THẬT, TÌM RA 24/08.

   `examples.python_snippet()` sinh ví dụ Python cho **mọi tool** trên cổng nhà
   phát triển. Nó dùng `urllib` và **không đặt `User-Agent`**. Đo thật hôm đó:

     urllib mac dinh      -> 403   <== Cloudflare chan
     requests / openai / anthropic / curl / Go / node-fetch / PowerShell -> 401

   Tức khách chép ví dụ của **chính ta** thì nhận 403 trước khi chạm máy chủ, và
   403 đó **không phải của ta** nên không có `request_id`, không có gì tra được.

⭐ ĐIỀU LÀM NÓ THÀNH MỘT LỚP LỖI CHỨ KHÔNG PHẢI MỘT LỖI:
   `python_chat_snippet()` **đã** đặt `User-Agent`, kèm chú thích giải thích đúng
   lý do. Nghĩa là có người đã gặp, đã hiểu, đã sửa — **ở đúng một chỗ**. Không có
   gì bắt chỗ thứ hai phải theo, nên nó nằm lại đó.

⛔ VÀ VÌ SAO TEST CŨ KHÔNG THẤY: test hợp đồng kiểm ví dụ **cú pháp có đúng không**
   và **có khớp schema không**. Cả hai đều xanh — ví dụ hoàn toàn hợp lệ. Thứ sai
   nằm ở tầng khác: nó hợp lệ nhưng **không đi qua được biên**. Loopback không có
   Cloudflare, nên không phép thử nào trong bộ test chạm tới điều này.
   Đây chính là quy tắc 5b của dự án, ở dạng test.
"""
from __future__ import annotations

import pytest

from platform_core.public_api import examples


def _tool_gia():
    return type("T", (), {
        "name": "image.ltt",
        "input_schema": {"properties": {"prompt": {"type": "string"}},
                         "required": ["prompt"]},
    })()


#: Ví dụ nào dùng `urllib` thì **bắt buộc** đặt `User-Agent`.
#: Danh sách này cố ý liệt kê từng hàm thay vì quét cả module: thêm một hàm sinh
#: ví dụ mới mà quên thêm vào đây thì `test_khong_bo_sot_ham_nao` bắt được.
SINH_VI_DU = {
    "python_snippet": lambda: examples.python_snippet(_tool_gia()),
    "python_chat_snippet": examples.python_chat_snippet,
}


@pytest.mark.parametrize("ten", sorted(SINH_VI_DU))
def test_vi_du_dung_urllib_phai_dat_user_agent(ten):
    ma = SINH_VI_DU[ten]()
    if "urllib" not in ma:
        pytest.skip(f"{ten} khong dung urllib")
    assert "User-Agent" in ma, (
        f"{ten}() sinh vi du dung urllib ma khong dat User-Agent. "
        f"Cloudflare tra 403 cho User-Agent mac dinh cua urllib TRUOC khi request "
        f"toi duoc may chu, nen khach chep vi du nay se hong ngay dong dau tien.")


def test_khong_bo_sot_ham_nao():
    """Mọi hàm sinh ví dụ dùng `urllib` phải có mặt trong `SINH_VI_DU`.

    Không có chốt này thì tệp test bên trên chỉ bảo vệ được hai hàm đã biết, và
    hàm thứ ba viết tháng sau sẽ lặp lại đúng lỗi cũ trong im lặng.
    """
    import inspect
    nguon = inspect.getsource(examples)
    dung_urllib = {
        ten for ten, ham in vars(examples).items()
        if callable(ham) and getattr(ham, "__module__", "") == examples.__name__
        and "urllib" in (inspect.getsource(ham) if _lay_duoc(ham) else "")
    }
    thieu = dung_urllib - set(SINH_VI_DU)
    assert not thieu, (
        f"Ham sinh vi du dung urllib nhung chua duoc chot: {sorted(thieu)}. "
        f"Them vao SINH_VI_DU o tep nay.")
    assert nguon


def _lay_duoc(ham) -> bool:
    import inspect
    try:
        inspect.getsource(ham)
        return True
    except (OSError, TypeError):
        return False
