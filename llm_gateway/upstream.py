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
                try:
                    ctx.__exit__(None, None, None)
                finally:
                    client.close()

        return r.status_code, content_type, _di()
