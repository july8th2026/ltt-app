"""
nhip_tim.py — chèn nhịp tim vào khoảng LẶNG của một luồng SSE. (H38, cắm CLI)

🔴 VÌ SAO CÓ FILE NÀY: KHÔNG CÓ NÓ THÌ CODEX VÀ CLAUDE CODE TỰ NGẮT.

   Cả hai CLI đều đặt đồng hồ trên **khoảng lặng của luồng**, không phải trên
   tổng thời gian:

     Codex CLI     `stream_idle_timeout_ms`, mặc định **300.000 ms**
     Claude Code   đếm **từng byte** cổng chuyển tiếp, kể cả sự kiện `ping` và
                   **dòng chú thích**, và bỏ luồng sau **300 giây** im lặng

   `llama-server` **không phát gì trong lúc prefill**. Ở ngữ cảnh dài, khoảng
   lặng đó chính là thời gian nạp prompt — và prompt hệ thống của một CLI agent
   không hề nhỏ: đo thật 23/08, **Codex gửi ~21.936 token mỗi lượt**. Cộng thêm
   một lần `llama-swap` đổi model là chạm trần 300 giây rất dễ.

   Đã thấy tận mắt: Codex gọi lúc 14:18:25, im lặng, rồi **thử lại đúng 14:23:27**
   — cách nhau 300 giây tròn. Nó không hỏng; nó làm đúng thứ nó nói sẽ làm.

⭐ DÙNG DÒNG CHÚ THÍCH SSE, KHÔNG DÙNG SỰ KIỆN `ping`. Chú thích (`: ...`) được
   **đặc tả SSE bảo đảm là bỏ qua**, nên nó an toàn cho cả ba giao thức mà cổng
   này phục vụ. Một sự kiện `ping` thì chỉ hợp lệ ở giao thức Anthropic, và gửi
   nó **trước** `message_start` là đặt cược vào việc client dễ tính. Chú thích
   mang đủ byte để giữ đồng hồ, mà không giả vờ là một sự kiện giao thức.

⛔ KHÔNG PHÂN TÍCH RỒI DỰNG LẠI LUỒNG. File này **chỉ chèn thêm** byte vào giữa
   các khối; nó không đọc, không cắt, không ghép nội dung. Xem `upstream.stream`.
"""
from __future__ import annotations

import queue
import threading
from typing import Iterator, Optional

#: Một dòng chú thích SSE. Kết thúc bằng hai dòng trống để chắc chắn nó là một
#: "sự kiện" trọn vẹn với mọi bộ phân tích, kể cả bộ nào gom theo khối.
NHIP_MAC_DINH = b": keep-alive\n\n"

#: Mặc định 15 giây. Trần của cả hai CLI là 300 giây, nên đây là **một phần hai
#: mươi** trần đó — đủ rộng để không tốn gì, đủ dày để không bao giờ chạm trần
#: kể cả khi mạng nhà chậm hoặc Cloudflare đệm một nhịp.
GIAY_MAC_DINH = 15.0


class _Het:
    """Dấu hết luồng. Một lớp riêng để không lẫn với bất kỳ khối byte nào."""


def boc_nhip_tim(luong: Iterator[bytes], *,
                 nhip: bytes = NHIP_MAC_DINH,
                 moi_giay: float = GIAY_MAC_DINH) -> Iterator[bytes]:
    """Trả lại `luong`, có chèn `nhip` mỗi khi nó lặng quá `moi_giay`.

    ⚠️ PHẢI DÙNG LUỒNG PHỤ, KHÔNG CÓ CÁCH NÀO KHÁC. `httpx.iter_raw()` **chặn**
       cho tới khi có byte; không có tham số nào bảo nó "chờ tối đa N giây rồi
       trả về tay không". Nên một luồng phụ bơm vào hàng đợi, còn generator này
       chờ hàng đợi **có thời hạn** — và mỗi lần hết hạn là một nhịp.

    ⛔ HÀNG ĐỢI KHÔNG GIỚI HẠN, CÓ CHỦ Ý. Đặt trần cho nó thì luồng bơm sẽ **kẹt**
       ở `put` khi khách ngắt giữa chừng, và luồng phụ đó không bao giờ chết.
       Lượng nhớ ở đây bị chặn bởi kích thước phản hồi, mà phản hồi đã bị chặn
       bởi `max_tokens` — vài chục KB, không phải thứ đáng đi đổi lấy một chỗ
       treo.

    ⛔ `moi_giay <= 0` ⇒ **tắt hẳn**, trả nguyên luồng gốc. Đừng để nó thành
       "nhịp mỗi 0 giây" — đó là một vòng lặp bận đốt CPU và làm ngập luồng.
    """
    if moi_giay <= 0:
        return luong
    return _di(luong, nhip, moi_giay)


def _di(luong: Iterator[bytes], nhip: bytes, moi_giay: float) -> Iterator[bytes]:
    hang: "queue.Queue" = queue.Queue()

    def bom() -> None:
        try:
            for khoi in luong:
                hang.put(khoi)
        except BaseException as e:                          # noqa: BLE001
            # Ném lại ở phía người đọc, ĐÚNG THỨ TỰ với các khối đã bơm. Nuốt ở
            # đây thì một luồng vỡ giữa chừng sẽ trông y hệt một luồng kết thúc
            # bình thường, và khách nhận nửa câu trả lời mà tưởng là đủ.
            hang.put(e)
        else:
            hang.put(_Het)

    t = threading.Thread(target=bom, daemon=True, name="llm-gateway-sse")
    t.start()

    try:
        while True:
            try:
                muc = hang.get(timeout=moi_giay)
            except queue.Empty:
                yield nhip
                continue
            if muc is _Het:
                return
            if isinstance(muc, BaseException):
                raise muc
            yield muc
    finally:
        # Khách ngắt giữa chừng: đóng luồng gốc để thượng nguồn biết mà dừng
        # sinh chữ. Không đóng thì `llama-server` chạy tiếp tới hết `max_tokens`
        # trên một câu trả lời không ai còn đọc, và GPU bị giữ vô ích.
        dong = getattr(luong, "close", None)
        if dong is not None:
            dong()
