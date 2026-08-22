"""
http.py — lớp vận chuyển thật bằng `httpx`.

Tách khỏi phần còn lại để test chạy được **trên máy A, không cần ComfyUI và không
cần GPU** — chỉ cần một đối tượng giả cùng hình dạng. Đó là điều kiện để G6 đóng
được trong khi máy B đang bận việc khác.
"""
from __future__ import annotations

from typing import Any, Optional


class HttpxTransport:
    """Vận chuyển tới ComfyUI (`comfy.Transport`)."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, *, json: Any = None,
                params: Optional[dict] = None, timeout: float = 30.0) -> tuple[int, bytes]:
        import httpx
        try:
            r = httpx.request(method, self.base_url + path, json=json,
                              params=params, timeout=timeout)
        except httpx.HTTPError as e:
            # Trả 599 thay vì ném: `ComfyClient` phân loại lỗi ở một chỗ duy nhất.
            return 599, str(e).encode("utf-8", "replace")
        return r.status_code, r.content


class HttpxFetcher:
    """Tải ảnh tham chiếu và đẩy kết quả (`storage_io.HttpFetcher`)."""

    def get(self, url: str, *, timeout: float) -> tuple[int, bytes]:
        import httpx
        try:
            r = httpx.get(url, timeout=timeout, follow_redirects=True)
        except httpx.HTTPError as e:
            return 599, str(e).encode("utf-8", "replace")
        return r.status_code, r.content

    def put(self, url: str, *, data: bytes, content_type: str,
            timeout: float) -> tuple[int, bytes]:
        import httpx
        try:
            # ⛔ `Content-Type` phải ĐÚNG chuỗi đã ký lúc tạo vé, nếu không R2 trả
            #    403. `platform_core/storage.py` đã ghi lại điều này.
            r = httpx.put(url, content=data, timeout=timeout,
                          headers={"Content-Type": content_type})
        except httpx.HTTPError as e:
            return 599, str(e).encode("utf-8", "replace")
        return r.status_code, r.content
