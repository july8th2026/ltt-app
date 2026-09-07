"""loi_ra_ngoai.py — MỘT cửa duy nhất biến một lỗi thành chữ cho NGƯỜI DÙNG.

## 🔴 Lỗ đã đo được 07/09, và nó ở trên đường ĐANG PHỤC VỤ KHÁCH

`platform_core/llm/luong_vlm.py` bọc **nguyên thân lỗi thượng nguồn** vào chuỗi
lỗi: `f"may B tra {code}: {than_loi[:600]}"`. Chuỗi ấy đi thẳng ra ngoài:

```
luong_vlm -> KhongMoDuoc(e.ly_do) -> luot.py {"ly_do": str(e)} -> SSE -> TRINH DUYET
                                  -> jobs.py LoiNghienCuu(str(e)) -> job.error
                                     -> _p_nghien_cuu.xem -> JSON -> TRINH DUYET
```

Đo với một thân lỗi `llama.cpp` **hình dạng bình thường**, bốn loại rò cùng lúc:

```
duong dan tep may chu : D:/models/<ten-model>.gguf
id model noi bo       : "model":"<id-that-cua-may-B>"
base_url noi bo       : "base_url":"http://192.168.1.50:8080/v1"
IP noi bo             : 192.168.1.50
```

⚠️ Hai dòng trên ĐÃ được che trong chính tệp này. Bản đầu tôi dán **id model nội
   bộ thật** vào docstring của một tệp mà cả mục đích là *"id model nội bộ không
   được lọt ra"* — và `test_614` bắt được ngay ở lượt gate đầu tiên.

⭐ Đó vừa là một lỗi buồn cười vừa là một bằng chứng: cái tên ấy rò được **qua
   mã nguồn** chứ không chỉ qua một phản hồi lỗi, và bánh cóc canh đúng chỗ.

⛔ Và nền tảng đã tự khai luật ngược lại. `runtime_noi_bo/luong.py`:
   *"Dịch alias → id nội bộ **ngay trước khi ra khỏi nền tảng**. Khách không bao
   giờ nhìn thấy id thật."*

## ⛔ Vì sao KHÔNG viết một bộ tẩy theo mẫu

`AGENTS.md` §4c câu 3: *"Tôi đang hỏi một **NHÃN** hay một **QUAN HỆ**? Nhãn thì
rẻ và **sai im lặng**."*

Một regex bắt IP/đường dẫn/`base_url` là một **nhãn**. Hình dạng rò tiếp theo —
một tên máy không có IP, một khoá API trong thân lỗi, một câu tiếng Anh kể tên
tệp — sẽ **không khớp**, và nó lọt **im lặng**. Đúng lớp lỗi đã hỏng ba lần
trong một đêm ở bộ đếm tiến trình.

⭐ Câu hỏi đúng là **quan hệ**: *"chuỗi này ĐẾN TỪ ĐÂU?"* Một chuỗi sinh ra từ
   thân phản hồi thượng nguồn, hay từ `str()` của một ngoại lệ bất kỳ, là
   **không tin được để hiển thị** — bất kể nó trông thế nào.

⇒ Nên bản vá không lọc nội dung. Nó **thay nguồn**: chữ cho người dùng dựng từ
  **mã lỗi** (một tập đóng, do ta viết), không dựng từ chuỗi ngoại lệ.

## Chi tiết KHÔNG mất, nó ĐỔI CHỖ

`luong_vlm` đã `log.warning("may B tra %s (day du): %s", …)`. Người trực vẫn có
đủ; chỉ khách là không. Đó là chỗ đúng của nó.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.i18n import _ as _t

#: Mã lỗi → câu cho người dùng. Tập **đóng**, và mỗi câu ở đây do ta viết —
#: không câu nào có nguồn gốc từ một hệ thống khác.
#:
#: ⚠️ Giữ khớp với `MA_LOI` trong `frontend/chatltt/src/App.tsx`. Giao diện chat
#:    dịch mã sang câu của riêng nó; hai bảng tồn tại vì hai bề mặt (SSE và
#:    JSON) và `test_846` chốt rằng chúng phủ cùng một tập mã.
CAU: dict = {
    "ban": N_('Model đang bận. Thử lại sau ít giây.'),
    "het_credit": N_('Không đủ credit cho lượt này.'),
    "qua_dai": N_('Nội dung vượt trần ngữ cảnh. Rút ngắn rồi thử lại.'),
    "khong_mo_duoc": N_('Không gọi được model lúc này.'),
    "khong_co_nang_luc": N_('Năng lực này chưa mở.'),
    "tham_so": N_('Yêu cầu không hợp lệ.'),
    "khong_tim_thay": N_('Không tìm thấy.'),
    "luong_cat": N_('Kết nối tới model đứt giữa chừng.'),
    "loi_noi_bo": N_('Có lỗi phía máy chủ. Việc này đã được ghi lại.'),
}

#: Câu cuối cùng khi không có mã nào khớp.
#:
#: 🔴 Fail-closed: một mã **lạ** ra câu chung chung, **không** ra `str(e)`. Đó
#:    đúng là chỗ một bản vá dễ hỏng nhất — nhánh "không biết" là nhánh người ta
#:    hay để lọt về hành vi cũ.
MAC_DINH = N_('Không chạy được. Thử lại, hoặc báo cho chúng tôi nếu còn lặp.')


def cau(ma: str) -> str:
    """Mã lỗi → câu cho người dùng. **Không** nhận chuỗi ngoại lệ.

    ⛔ Chữ ký chỉ nhận `ma` là có chủ đích: không có tham số nào để ai đó tiện
       tay truyền `str(e)` vào rồi nó chảy ra ngoài.
    """
    # ⛔ `_t()` o CHO DUNG, khong `_()` o bang: `_()` dich luc import,
    #    tuc dong bang ngon ngu tien trinh vao moi cau loi.
    return _t(CAU.get(str(ma or "").strip(), MAC_DINH))


def hinh_dang(e: BaseException) -> str:
    """Chữ an toàn cho **log/chẩn đoán trong sản phẩm**, không phải cho khách.

    ⭐ Trả về **tên lớp**, không trả nội dung. Một hình dạng nói được *"hỏng ở
       đâu"* mà không mang theo thứ thượng nguồn viết ra. `luot.py` đã dùng đúng
       cách này ở một nhánh (`"ly_do": type(e).__name__`) — hàm này chỉ làm nó
       thành luật chung thay vì một chỗ làm đúng lẻ loi.
    """
    return type(e).__name__


__all__ = ["CAU", "MAC_DINH", "cau", "hinh_dang"]
