"""
co_v3.py — cờ tính năng của ChatLTT V3. Đọc mỗi lần, không nhớ. (H44 P03)

## Vì sao ĐỌC MỖI LẦN chứ không đọc lúc import

Một cờ đọc lúc import thì tắt nó phải **khởi động lại dịch vụ** — và lúc cần
tắt gấp là đúng lúc không ai muốn khởi động lại. Đọc mỗi lần tốn một lời gọi
`os.environ.get`, đổi lấy một cái van vặn được ngay.

⭐ Và nó làm test không phải `importlib.reload` để đổi cờ — chính `reload` là
   thứ đã làm 16 phép kiểm đỏ ở **bảy tệp khác** và sinh ra `test_631`.

## Hai cờ, hai việc khác nhau

    LTT_CHATLTT_V3_TOOLS        vong lap tool co chay khong
    LTT_CHATLTT_V3_PAID_TOOLS   model co duoc TU GOI tool CO PHI khong

⛔ Cờ thứ hai **không** tự bật theo cờ thứ nhất. Vòng lặp chạy với tool miễn
   phí là một mức rủi ro; model tự tiêu tiền của khách là mức khác hẳn. Gộp hai
   cờ lại là để một lần bật vô tình mở cả hai.

## Cờ KHÔNG phải cổng an toàn

`02_ADR_ORCHESTRATION.md` §7: cờ là **cổng phát hành**. Thứ chặn model tiêu tiền
là `chieu_tool.CHO_MODEL_GOI` + duyệt bền (P04), không phải một biến môi trường
mà bất kỳ ai sửa `app.env` cũng đổi được.
"""
from __future__ import annotations

import os

CO_TOOLS = "LTT_CHATLTT_V3_TOOLS"
CO_TOOL_CO_PHI = "LTT_CHATLTT_V3_PAID_TOOLS"

#: Giá trị được coi là BẬT. Fail-closed: mọi thứ khác là tắt, kể cả `"true"`
#: viết hoa lạ hay `"yes"` — một cờ nhận nhiều cách viết là một cờ mà người ta
#: tưởng đã bật trong khi chưa.
BAT = frozenset({"1", "true", "on"})


def _bat(ten: str) -> bool:
    return (os.environ.get(ten) or "").strip().lower() in BAT


def tool_bat() -> bool:
    """Vòng lặp tool có chạy không. **Mặc định TẮT.**"""
    return _bat(CO_TOOLS)


def tool_co_phi_bat() -> bool:
    """Model có được tự gọi tool có phí không. **Mặc định TẮT**, và độc lập.

    ⛔ `tool_bat()` bật **không** kéo theo cái này. Xem docstring module.
    """
    return _bat(CO_TOOL_CO_PHI)


def trang_thai() -> dict:
    """Cho `/api/danh-muc` và log — để người trực biết cờ nào đang bật."""
    return {"tools": tool_bat(), "tool_co_phi": tool_co_phi_bat()}


__all__ = ["tool_bat", "tool_co_phi_bat", "trang_thai", "CO_TOOLS", "CO_TOOL_CO_PHI"]
