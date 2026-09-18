"""su_kien_loi.py — MỘT chỗ dựng lỗi đúng khuôn giao thức: sự kiện SSE (sau 200),
thân HTTP "quá dài" (trước 200), và nhịp chờ của từng cửa. (multijob D-06, R-08)

⭐ VÌ SAO CÓ TỆP NÀY: cửa stream nay gửi 200 + mở SSE TRƯỚC khi được nhận vào máy B
   (chờ trong phòng chờ, có nhịp tim). Sau 200 thì không còn mã HTTP — mọi kết cục
   xấu (hết trần chờ, số dư tụt giữa chừng, máy B bận/hỏng) phải thành một SỰ KIỆN
   mà client của ĐÚNG giao thức đó hiểu.

⛔ Không nhét lý do thô của máy B vào thông điệp (bài học `streaming.py:659-667`:
   thân 429 của máy B mang dung lượng VRAM còn lại). Thông điệp ở đây là câu cố định.

## 🔴 "Quá dài" — client nhận ra bằng CÂU CHỮ và KHUÔN, không bằng mã 413 (R-08)

Tra nguồn client thật 18/09/2026 (`tests/test_1480`):

  * Claude Code 2.1.274 (`claude.exe`): lỗi là "prompt too long" khi thông điệp
    chứa ``prompt is too long`` — bất kể mã HTTP — và rút số bằng
    ``/prompt is too long[^0-9]*(\\d+)\\s*tokens?\\s*>\\s*(\\d+)/i``. Đúng câu của
    API Anthropic: ``prompt is too long: N tokens > M maximum``, HTTP 400.
  * Codex CLI (`codex-rs/codex-api/src/sse/responses.rs`, `api_bridge.rs`): CHỈ
    SSE ``response.failed`` + ``error.code == "context_length_exceeded"`` thành
    `ContextWindowExceeded` (⇒ tự nén). HTTP 400/413 thành lỗi chết lượt.

⇒ Trước bản này cả ba cửa trả ``413 problem+json`` với câu "exceeds the model's
  context limit" — không client nào trong hai nhận ra, nên không client nào nén.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Callable, Optional

from starlette.responses import JSONResponse, Response, StreamingResponse

# ma nội bộ → (error.type — Anthropic và OpenAI dùng chung từ vựng, error.code OpenAI)
_MA = {
    "overloaded": ("overloaded_error", "server_is_overloaded"),
    "insufficient_credit": ("invalid_request_error", "insufficient_quota"),
    "context_length": ("invalid_request_error", "context_length_exceeded"),
    "upstream": ("api_error", "server_error"),
}

#: Tiền tố Claude Code dò (xem docstring tệp). ⛔ Đừng dịch, đừng viết hoa lại.
CAU_QUA_DAI = "prompt is too long"


def cau_qua_dai(token: Optional[int] = None, tran: Optional[int] = None) -> str:
    """Câu "quá dài" DUY NHẤT: đúng chữ API Anthropic, có số khi biết số."""
    if token is not None and tran is not None:
        return (f"{CAU_QUA_DAI}: {int(token)} tokens > {int(tran)} maximum. "
                f"The input exceeds this model's context window; compact or drop "
                f"older turns and retry.")
    return (f"{CAU_QUA_DAI}: the input exceeds this model's context window; "
            f"compact or drop older turns and retry.")


def _chuan_thong_diep(ma: str, thong_diep: str) -> str:
    # Mọi lỗi "quá dài" — kể cả do nơi gọi truyền câu riêng — mang tiền tố client dò.
    if ma == "context_length" and CAU_QUA_DAI not in thong_diep.lower():
        return f"{CAU_QUA_DAI}: {thong_diep}"
    return thong_diep


def _loi_anthropic(ma: str, thong_diep: str) -> dict:
    loai, _ = _MA.get(ma, ("api_error", "server_error"))
    return {"type": "error", "error": {"type": loai, "message": thong_diep}}


def _loi_openai(ma: str, thong_diep: str, param: Optional[str] = None) -> dict:
    loai, ma_openai = _MA.get(ma, ("api_error", "server_error"))
    return {"message": thong_diep, "type": loai, "param": param, "code": ma_openai}


def _id_response() -> str:
    return "resp_ltt_" + uuid.uuid4().hex[:24]


def loi_sse(duong: str, ma: str, thong_diep: str) -> bytes:
    """Dựng khối SSE lỗi cho cửa `duong` (`/v1/messages`, `/v1/responses`, còn lại)."""
    thong_diep = _chuan_thong_diep(ma, thong_diep)
    if duong.endswith("/messages"):
        than = _loi_anthropic(ma, thong_diep)
        return b"event: error\ndata: " + json.dumps(than).encode("utf-8") + b"\n\n"
    if duong.endswith("/responses"):
        loi = _loi_openai(ma, thong_diep)
        than = {"type": "response.failed",
                "response": {"id": _id_response(), "object": "response",
                             "status": "failed",
                             "error": {"code": loi["code"], "message": loi["message"]}}}
        return (b"event: response.failed\ndata: " + json.dumps(than).encode("utf-8")
                + b"\n\n")
    than = {"error": _loi_openai(ma, thong_diep)}
    return b"data: " + json.dumps(than).encode("utf-8") + b"\n\n"


def loi_qua_dai(duong: str, *, stream: bool, token: Optional[int] = None,
                tran: Optional[int] = None, request=None) -> Response:
    """Phản hồi "quá dài" TRƯỚC 200 cho cửa `duong` — 0 khoản giữ, chưa chạm máy B.

    `/v1/messages` ⇒ 400 khuôn Anthropic · `/v1/responses` stream ⇒ 200 + MỘT
    `response.failed` (đường duy nhất Codex hiểu là tràn cửa sổ) · còn lại ⇒ 400
    khuôn OpenAI. `limit_name`/`limit_value` giữ ở thân (tài liệu `LOI_413`).
    """
    if duong.endswith("/responses") and stream:
        if request is not None:
            request.state.api_error_code = "context_length_exceeded"
        khoi = loi_sse(duong, "context_length", cau_qua_dai(token, tran))
        return StreamingResponse(iter([khoi]), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store",
                                          "X-Accel-Buffering": "no"})
    return loi_qua_dai_json(duong, token=token, tran=tran, request=request)


def loi_qua_dai_json(duong: str, *, token: Optional[int] = None,
                     tran: Optional[int] = None, request=None) -> JSONResponse:
    """Nhánh HTTP 400 của `loi_qua_dai` (mọi cửa trừ Responses stream)."""
    thong_diep = cau_qua_dai(token, tran)
    if request is not None:
        # Nhật ký request ghi mã ổn định như mọi `ApiError` (`server/api/errors.py`).
        request.state.api_error_code = "context_length_exceeded"
    headers = {"Cache-Control": "no-store"}
    them: dict = {"limit_name": "input_tokens"}
    if tran is not None:
        them["limit_value"] = int(tran)
    if duong.endswith("/messages"):
        than = _loi_anthropic("context_length", thong_diep)
    else:
        param = "input" if duong.endswith("/responses") else "messages"
        than = {"error": _loi_openai("context_length", thong_diep, param)}
    return JSONResponse({**than, **them}, status_code=400, headers=headers)


def bo_nhip(duong: str) -> Callable[[str], bytes]:
    """Bộ dựng nhịp chờ cho MỘT lượt: `nhip(ly_do) -> bytes`.

    `/v1/responses` ⇒ SỰ KIỆN hợp lệ: lần đầu `response.created` (status
    `queued`), rồi `response.in_progress` — Codex nạp lại đồng hồ im lặng SSE chỉ
    khi có sự kiện (comment bị bộ phân tích nuốt), và `openai-python`
    `responses.stream()` đòi `response.created` là sự kiện đầu. Luồng máy B sau đó
    phát `response.created` của nó: Codex giữ id cuối, `openai-python` bỏ qua bản
    thứ hai. Các cửa khác ⇒ chú thích SSE như cũ (mọi client bỏ qua).
    """
    if not duong.endswith("/responses"):
        def _chu_thich(ly_do: str) -> bytes:
            return f": ltt-cho {ly_do}\n\n".encode("ascii", "replace")
        return _chu_thich

    rid = _id_response()
    tao_luc = int(time.time())
    dem = {"so": 0}

    def _su_kien(ly_do: str) -> bytes:
        so = dem["so"]
        dem["so"] = so + 1
        loai = "response.created" if so == 0 else "response.in_progress"
        than = {"type": loai, "sequence_number": so,
                "response": {"id": rid, "object": "response", "created_at": tao_luc,
                             "status": "queued" if so == 0 else "in_progress",
                             "output": []}}
        khoi = (f"event: {loai}\ndata: ".encode("ascii")
                + json.dumps(than).encode("utf-8") + b"\n\n")
        if so == 0:
            # Lần đầu: created RỒI in_progress ngay, để mọi nhịp đều có in_progress.
            return khoi + _su_kien(ly_do)
        return khoi

    return _su_kien
