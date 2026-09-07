"""
dinh_dang.py — quy ước đọc số của nền tảng, ở đúng MỘT chỗ.

## Vì sao tệp này tồn tại

`server/templating.py::_so` đã trả lời câu hỏi này cho **khuôn mẫu** từ 25/08,
và chú thích của nó ghi lại đúng lý do: đo hôm ấy khu API hiện `50000 credit`
trong khi trang VPS hiện `149.000` — cùng một sản phẩm, hai quy ước đọc số, và
đọc nhầm một bậc là hiểu sai giá gấp mười lần.

⛔ Nhưng filter chỉ tới được nơi có Jinja. **Thông điệp lỗi thì không.** Ngày
   05/09/2026 màn Studio hiện `0 / 100.000 ký tự` trong khi thông điệp lỗi của
   chính cửa ấy trả về *"vượt giới hạn 100000"* — hai quy ước cách nhau đúng
   một lượt POST, trên cùng một màn hình, về cùng một con số.

⭐ Nên hàm nằm ở đây, và `_so` của `templating.py` gọi nó. Một định nghĩa, ba
   nơi dùng: filter khuôn mẫu, thông điệp lỗi phía máy chủ, và — được nhân bản
   có ghi chú — `soViet()` trong `server/static/voice.js`, vì trình duyệt đếm
   lại lúc khách đang gõ và không hỏi máy chủ được cho mỗi phím.

⚠️ Bản nhân bản trong JS là bản sao thứ hai THẬT, và nó sẽ trôi nếu ai đó đổi
   quy ước ở đây mà quên nó. Nó được chấp nhận vì phương án còn lại — hỏi máy
   chủ mỗi lần gõ một chữ — tệ hơn hẳn. Chú thích ở cả hai đầu trỏ vào nhau.
"""
from __future__ import annotations


def so_viet(gt) -> str:
    """`100000` → `"100.000"`. Dấu **chấm**, theo quy ước Việt Nam.

    ⚠️ Chuỗi này **không** phải chuỗi cần dịch. Quy ước phân cách là chuyện của
       ngôn ngữ hiển thị chứ không phải của bản dịch, và tách nó ra thành một
       `msgid` chỉ tạo ra một chỗ để hai bản dịch nói hai kiểu.

    ⭐ HỎI TRƯỚC, KHÔNG BẮT NGOẠI LỆ. Chỉ có hai ca — số và không-phải-số — và
       cả hai hỏi được bằng `isinstance`. Bọc `try/except` ở đây là dùng cơ chế
       báo lỗi để làm việc của một câu `if`, và bánh cóc `check_silent_except`
       sẽ đỏ đúng như nó nên đỏ.
    """
    if isinstance(gt, str):
        rut = gt.strip()
        if not rut.lstrip("-").isdigit():
            return str(gt)
        gt = int(rut)
    # `bool` là con của `int`: để lọt thì `True` hiện ra thành `1`.
    if isinstance(gt, bool) or not isinstance(gt, (int, float)):
        return str(gt)
    return f"{int(gt):,}".replace(",", ".")
