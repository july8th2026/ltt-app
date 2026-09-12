"""su_kien_loi.py — MỘT khối lỗi SSE đúng khuôn giao thức, cho lỗi xảy ra SAU 200. (multijob D-06)

⭐ VÌ SAO CÓ TỆP NÀY: cửa stream nay gửi 200 + mở SSE TRƯỚC khi được nhận vào máy B
   (chờ trong phòng chờ, có nhịp tim). Sau 200 thì không còn mã HTTP — mọi kết cục
   xấu (hết trần chờ, số dư tụt giữa chừng, máy B bận/hỏng) phải thành một SỰ KIỆN
   mà client của ĐÚNG giao thức đó hiểu.

⛔ Không nhét lý do thô của máy B vào thông điệp (bài học `streaming.py:659-667`:
   thân 429 của máy B mang dung lượng VRAM còn lại). Thông điệp ở đây là câu cố định.

⚠️ Cách Codex CLI và Claude Code phản ứng với các khối này phải kiểm bằng CLIENT
   THẬT trước khi mở 4 slot (D-10, `docs/multijob/09_TEST_GATES.md` B8) — `test_290`
   đã dạy: *API trả đúng khuôn ≠ client dùng được*.
"""
from __future__ import annotations

import json
import uuid

# ma nội bộ → (Anthropic error.type, OpenAI error.code)
_MA = {
    "overloaded": ("overloaded_error", "server_is_overloaded"),
    "insufficient_credit": ("invalid_request_error", "insufficient_quota"),
    "context_length": ("invalid_request_error", "context_length_exceeded"),
    "upstream": ("api_error", "server_error"),
}


def loi_sse(duong: str, ma: str, thong_diep: str) -> bytes:
    """Dựng khối SSE lỗi cho cửa `duong` (`/v1/messages`, `/v1/responses`, còn lại)."""
    loai_anthropic, ma_openai = _MA.get(ma, ("api_error", "server_error"))
    if duong.endswith("/messages"):
        than = {"type": "error", "error": {"type": loai_anthropic, "message": thong_diep}}
        return b"event: error\ndata: " + json.dumps(than).encode("utf-8") + b"\n\n"
    if duong.endswith("/responses"):
        than = {"type": "response.failed",
                "response": {"id": "resp_ltt_" + uuid.uuid4().hex[:24],
                             "object": "response", "status": "failed",
                             "error": {"code": ma_openai, "message": thong_diep}}}
        return (b"event: response.failed\ndata: " + json.dumps(than).encode("utf-8")
                + b"\n\n")
    than = {"error": {"type": ma_openai, "code": ma_openai, "message": thong_diep}}
    return b"data: " + json.dumps(than).encode("utf-8") + b"\n\n"
