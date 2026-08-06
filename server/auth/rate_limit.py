"""
Bộ đếm lần thử trong bộ nhớ, dùng cho đăng nhập và một số endpoint khác.

Cố ý để trong bộ nhớ, không dùng Redis — theo ADR-005/ADR-011 (một tiến trình
điều phối, bản web đầu tiên không có Celery/Redis).

⚠️ **Hai ràng buộc phải nhớ khi đổi hạ tầng:**

1. Khởi động lại là mất sạch bộ đếm. Deploy tự nó xoá — chấp nhận được, vì kẻ
   tấn công không ép được máy chủ khởi động lại.
2. **Chỉ đúng khi web chạy MỘT tiến trình.** Hiện `uvicorn` chạy không có
   `--workers`, nên bộ đếm là chung cho toàn hệ thống. Thêm `--workers N` sẽ
   chia bộ đếm thành N phần độc lập và **nới trần lên N lần một cách lặng lẽ** —
   không lỗi, không cảnh báo, chỉ là phòng thủ yếu đi. Lúc đó phải chuyển bộ đếm
   xuống PostgreSQL.

Chú thích cũ nói module này dành cho "bảng điều khiển một người dùng, không phải
dịch vụ nhiều người dùng công khai". Giả định đó **đã hết hiệu lực** từ khi có
khách trả tiền — vì vậy phần leo thang ở `server/routes/auth.py` được thiết kế
lại theo hướng thách đố thay vì khoá tài khoản.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, *, max_attempts: int = 5, window_seconds: float = 60.0):
        self._max_attempts = max_attempts
        self._window = window_seconds
        self._attempts: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _don(self, key: str, now: float) -> deque:
        """Bỏ các lần thử đã ra khỏi cửa sổ. Gọi khi ĐANG giữ khoá."""
        bucket = self._attempts[key]
        while bucket and now - bucket[0] > self._window:
            bucket.popleft()
        return bucket

    def allow(self, key: str) -> bool:
        """Record an attempt for *key* and return True if it's within the
        allowed rate, False if the caller should be rejected."""
        now = time.monotonic()
        with self._lock:
            bucket = self._don(key, now)
            if len(bucket) >= self._max_attempts:
                return False
            bucket.append(now)
            return True

    def so_lan(self, key: str) -> int:
        """Số lần thử còn trong cửa sổ — CHỈ ĐỌC, không tính thêm một lần.

        Cần cho việc leo thang theo ngưỡng (vd: quá 3 lần thì hiện thách đố):
        chỗ quyết định phải xem được con số mà không tự làm nó tăng lên.
        """
        with self._lock:
            return len(self._don(key, time.monotonic()))

    def ghi_nhan(self, key: str) -> int:
        """Tính thêm một lần thử, trả về số lần trong cửa sổ sau khi tính.

        Khác `allow`: KHÔNG có trần. Dùng khi nơi gọi tự quyết định ngưỡng —
        `allow` gộp cả đếm lẫn phán quyết nên không diễn tả được nhiều mức
        (thách đố ở mức này, chặn cứng ở mức kia).
        """
        with self._lock:
            bucket = self._don(key, time.monotonic())
            bucket.append(time.monotonic())
            return len(bucket)

    def reset(self, key: str) -> None:
        """Call after a successful login so a legitimate user isn't
        penalized by their own prior failed attempts."""
        with self._lock:
            self._attempts.pop(key, None)
