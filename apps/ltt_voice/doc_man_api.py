"""
doc_man_api.py — những gì MÀN API của Voice cần biết, và không gì hơn.

## Màn này tồn tại để làm gì, khi đã có cả khu `/developers`

Khu Lập trình viên trả lời mọi câu hỏi **chung**: khoá, hạn mức, giá, nhật ký,
playground. Nó không trả lời được ba câu **riêng của giọng nói**, và đó là toàn
bộ lý do màn này có mặt:

1. **Mã giọng của tôi là gì?** Giọng nhân bản chỉ tồn tại trong tài khoản này;
   `/developers/tools` mô tả tham số `voice_id` nhưng không biết khách có giọng
   nào. Không có màn này thì khách phải sang màn Giọng, chép từng mã, rồi quay
   lại — hoặc đoán.
2. **Tên giọng dựng sẵn nào hợp lệ?** Hai mươi tên, và gõ sai một chữ thì lỗi
   hiện ra ở tận lúc gọi, dưới dạng "không tìm thấy giọng".
3. **Trần 1.500 ký tự là trần gì?** Nó là trần **chất lượng**, không phải trần
   kỹ thuật (Q118) — và một dòng trong bảng tham số không nói được điều đó.

⛔ **KHÔNG chép lại bất cứ thứ gì khu Lập trình viên đã có.** Không bảng giá thứ
   hai, không danh sách khoá thứ hai, không nhật ký thứ hai. Hai bản của cùng
   một sự thật thì bản nào cũng sai được một mình, và bản sai sẽ là bản không ai
   nhớ phải cập nhật.

## 🔴 Trạng thái phải là SỰ THẬT ĐANG CHẠY, không phải một hằng số

`speech.ltt` khai `api_exposed=True` trong bản khai — điều đó **không** có nghĩa
nó đang mở. Cổng thật là `LTT_PUBLIC_API_TOOLS`, và hôm nay công cụ này **không**
có trong đó. Một màn nói "gọi thế này" trong khi cửa đóng sẽ đẩy khách vào một
lượt 404 mà họ đọc thành "khoá của tôi sai".

⚠️ Đây đúng là lớp lỗi mà `CLAUDE.md` đã dính **hai lần** với chính khu API: tài
   liệu ghi "chưa mở" trong khi máy chủ đang bán. Bài học đã ghi ở đó là *đừng
   đọc con số trong tài liệu, hỏi máy chủ* — nên màn này hỏi cấu hình đang chạy
   mỗi lần dựng trang, không cache, không hằng số.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

#: Tên công cụ trên `/api/v1`. Cùng chuỗi với `manifest.ToolSpec.name`.
TEN_TOOL = "speech.ltt"


def trang_thai_tool(ten: str = TEN_TOOL) -> dict:
    """`{khu_bat, tool_mo, chi_doc}` — đọc từ cấu hình ĐANG CHẠY.

    Trả về trạng thái "đóng" nếu không đọc được, chứ không nổ: một màn hướng dẫn
    hỏng không được phép làm khách mất luôn danh sách mã giọng bên dưới. Và đóng
    là phía an toàn — nó khiến khách hỏi, thay vì khiến khách gọi rồi thất bại.
    """
    try:
        from platform_core.public_api.config import load_public_api_config
        cau_hinh = load_public_api_config()
    except Exception:  # noqa: BLE001
        log.exception("khong doc duoc cau hinh public api")
        return {"khu_bat": False, "tool_mo": False, "chi_doc": False}
    return {
        "khu_bat": bool(cau_hinh.enabled),
        "tool_mo": bool(cau_hinh.enabled and cau_hinh.tool_exposed(ten)),
        "chi_doc": bool(cau_hinh.read_only),
    }


def ma_giong_cua_toi(db, owner_id: str) -> list:
    """Mã giọng nhân bản còn dùng được, kèm tên hiển thị — để chép vào mã nguồn.

    ⚠️ Chỉ giọng `active`. Một giọng đã gỡ vẫn còn hàng trong CSDL (bút toán trỏ
       về nó), nhưng đưa mã của nó vào một trang hướng dẫn gọi API là mời khách
       viết một lời gọi chắc chắn hỏng.
    """
    try:
        from . import tham_chieu
        # `gom_dung_chung=True`: kho giong chung goi duoc qua API — chinh
        # `features.py` mo `cho_dung_chung=True` o cua DUNG. Thieu no o day
        # thi trang nay noi "Ban chua co giong nhan ban nao" voi mot khach
        # dang dung duoc 25 giong o man Tao tieng noi.
        cac = tham_chieu.danh_sach(db, owner_id=owner_id,
                                   gom_dung_chung=True)
    except Exception:  # noqa: BLE001
        log.exception("khong doc duoc danh sach giong")
        return []
    return [{"ma": g.public_id, "ten": g.ten_hien_thi}
            for g in cac if g.trang_thai == "active"]


def vi_du_van_ban(ten: str = TEN_TOOL) -> str:
    """Câu ví dụ cho tham số `text`, lấy từ CHÍNH `api_contract`.

    ⛔ Không gõ lại vào khuôn mẫu. `/developers/tools` in ví dụ từ bản khai; nếu
       màn này có bản riêng thì một ngày khách thấy hai câu khác nhau cho cùng
       một tham số và không biết tin câu nào.
    """
    try:
        from .manifest import MANIFEST
        for t in MANIFEST.tools:
            if t.name == ten:
                return str((t.api_contract or {}).get("params", {})
                           .get("text", {}).get("example") or "")
    except Exception:  # noqa: BLE001
        log.exception("khong doc duoc vi du tu ban khai")
    return ""
