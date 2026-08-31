"""
upstream.py — lớp vận chuyển thật tới `llama-swap`, bằng `httpx`.

Tách khỏi phần còn lại để test chạy được **trên máy A, không cần GPU và không cần
llama-swap** — chỉ cần một đối tượng giả cùng hình dạng. Cùng lý do và cùng khuôn
với `render_gateway/http.py`.

⛔ `llama-swap` và `llama-server` chỉ nghe `127.0.0.1`. Lớp này **không bao giờ**
   được trỏ ra ngoài loopback, và **không bao giờ** làm proxy tới Internet: cổng
   trên máy B không được là một đường đi ra (Q102).
"""
from __future__ import annotations

from typing import Any, Iterator, Optional, Protocol


class Upstream(Protocol):
    """Hình dạng mà `api.py` cần. Bản giả trong test cài đúng hai hàm này."""

    def json(self, method: str, path: str, *, body: Any = None,
             timeout: float = 60.0) -> tuple[int, bytes]: ...

    def stream(self, method: str, path: str, *, body: Any = None,
               timeout: float = 900.0) -> tuple[int, str, Iterator[bytes]]: ...


class HttpxUpstream:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def json(self, method: str, path: str, *, body: Any = None,
             timeout: float = 60.0) -> tuple[int, bytes]:
        import httpx
        try:
            r = httpx.request(method, self.base_url + path, json=body, timeout=timeout)
        except httpx.HTTPError as e:
            # Trả 599 thay vì ném: `api.py` phân loại lỗi ở một chỗ duy nhất.
            return 599, str(e).encode("utf-8", "replace")
        return r.status_code, r.content

    def stream(self, method: str, path: str, *, body: Any = None,
               timeout: float = 900.0) -> tuple[int, str, Iterator[bytes]]:
        """Chuyển tiếp SSE **nguyên xi**, không phân tích, không gom lại.

        ⛔ TUYỆT ĐỐI KHÔNG tự phân tích rồi dựng lại SSE. Cộng đồng đã mất thời
           gian vì đúng lỗi này: một harness dùng regex cắt delta ở dấu nháy đã
           thoát, làm mất chữ giữa dòng, và người ta tưởng là lỗi của engine
           (vllm-project/vllm#52469 — đã đóng, engine vô can). Cổng này là đường
           ống, không phải bộ dịch.

        ⚠️ `timeout` phải rộng: ở ngữ cảnh 200K, prefill có thể mất VÀI PHÚT trước
           byte đầu tiên (cộng đồng đo prefill ~1.000 tok/s ở đầu vào 100k).
        """
        import httpx
        client = httpx.Client(timeout=timeout)
        try:
            ctx = client.stream(method, self.base_url + path, json=body)
            r = ctx.__enter__()
        except httpx.HTTPError as e:
            client.close()
            return 599, "text/plain", iter([str(e).encode("utf-8", "replace")])

        content_type = r.headers.get("content-type", "text/event-stream")

        def _di() -> Iterator[bytes]:
            try:
                for khoi in r.iter_raw():
                    yield khoi
            finally:
                dong()

        da_dong = [False]

        def dong() -> None:
            """Đóng kết nối thượng nguồn. Gọi bao nhiêu lần cũng được."""
            if da_dong[0]:
                return
            da_dong[0] = True
            try:
                ctx.__exit__(None, None, None)
            finally:
                client.close()

        # 🔴 VÌ SAO PHẢI GIAO RA MỘT HÀM ĐÓNG, KHÔNG CHỈ MỘT GENERATOR.
        #
        #    Kết nối đã MỞ ngay lúc này — `ctx.__enter__()` chạy ở trên, header
        #    đã về. Nhưng thứ đóng nó lại nằm trong `finally` của `_di`, và
        #    `finally` ấy chỉ tồn tại **sau khi generator chạy dòng đầu tiên**.
        #
        #    Không ai lặp qua `_di` thì khối `try` chưa từng được vào, nên
        #    `.close()` trên generator cũng **không** chạy `finally` — Python chỉ
        #    đánh dấu nó đã đóng. Kết quả: socket còn mở và `llama-server` sinh
        #    chữ tiếp cho một yêu cầu không còn ai đọc.
        #
        #    Đây đúng là đường đã gây sự cố 31/08 ở tầng trên (`boc_luong` giữ
        #    suất vĩnh viễn vì cùng lý do). Nên đường dọn phải gọi được **mà
        #    không cần generator khởi động**.
        return r.status_code, content_type, LuongUpstream(_di(), dong)


class LuongUpstream:
    """Luồng byte kèm một đường đóng gọi được **độc lập với việc lặp**.

    Vẫn là `Iterator[bytes]` nên `Upstream` protocol không đổi, và mọi bản giả
    trong test trả `iter([...])` vẫn dùng được — bên gọi hỏi `dong` bằng
    `getattr`, không đòi hỏi.
    """

    __slots__ = ("_it", "dong")

    def __init__(self, it: Iterator[bytes], dong):
        self._it = it
        self.dong = dong

    def __iter__(self) -> "LuongUpstream":
        return self

    def __next__(self) -> bytes:
        return next(self._it)

    def close(self) -> None:
        """`nhip_tim` tìm `.close()` để bảo thượng nguồn dừng sinh chữ.

        Đóng generator TRƯỚC (để `finally` của nó chạy nếu nó đã khởi động), rồi
        đóng thẳng — `dong` idempotent nên gọi hai lần vô hại.

        ⚠️ `getattr` chứ không gọi thẳng: **không phải iterator nào cũng có
           `close`**. Bản đầu của tôi gọi `self._it.close()` trần và vỡ với một
           `list_iterator` — tức nó chỉ chạy được với đúng generator thật, và
           mọi bản giả trong bộ test sẽ ném `AttributeError` **từ trong đường
           dọn dẹp**, nơi một ngoại lệ dễ nuốt mất cả việc đóng thượng nguồn.
        """
        dong_it = getattr(self._it, "close", None)
        try:
            if dong_it is not None:
                dong_it()
        finally:
            self.dong()
