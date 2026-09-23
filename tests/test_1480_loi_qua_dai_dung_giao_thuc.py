"""
test_1480 — "quá dài" TRƯỚC 200 phải nói đúng câu của từng giao thức (R-08, Task 8).

⭐ VÌ SAO (đã tra nguồn client thật, 18/09/2026):

  * **Claude Code 2.1.274** (nhị phân `claude.exe`): `bU(e)` coi một lỗi API là
    "prompt too long" khi thông điệp chứa ``prompt is too long`` (hoặc
    ``input is too long for requested model``) — BẤT KỂ mã HTTP; rồi
    ``/prompt is too long[^0-9]*(\\d+)\\s*tokens?\\s*>\\s*(\\d+)/i`` rút số token
    thật/trần để nén. Với 413, nó chỉ coi là prompt-too-long khi thông điệp có
    ``context window`` hoặc ``prompt is too long`` — câu cũ của ta
    ("exceeds the model's context limit") không có cả hai ⇒ client KHÔNG nén.
  * **Codex CLI** (`codex-rs/codex-api/src/sse/responses.rs` `is_context_window_error`,
    `api_bridge.rs` `map_api_error`): CHỈ sự kiện SSE ``response.failed`` với
    ``error.code == "context_length_exceeded"`` thành `ContextWindowExceeded`
    (đặt token đầy ⇒ tự nén lượt sau). HTTP 400 cùng thân ⇒ `InvalidRequest`
    (lỗi chết lượt); HTTP 413 ⇒ `UnexpectedStatus`. Nên cửa Responses stream trả
    200 + đúng MỘT ``response.failed``.
  * Codex bỏ qua ``response.in_progress`` (liệt kê tường minh trong nhánh
    "unhandled responses event") nhưng đồng hồ im lặng SSE của nó chỉ được nạp
    lại bởi một SỰ KIỆN — chú thích ``: ltt-cho`` không phải sự kiện
    (`eventsource-stream` nuốt comment). `openai-python` `responses.stream()`
    ném lỗi nếu sự kiện đầu không phải ``response.created``.
"""
from __future__ import annotations

import json
import re

import pytest

from tests import test_272_cua_streaming as _t272
from tests.test_272_cua_streaming import (
    MODEL, MSG, RSP, _account, _dat_luong, _giu_execution_slot, _h, _so_du,
    _than)

#: Dùng lại fixture `api` của test_272 (gán, không import — ruff F811).
api = _t272.api

#: Chính regex Claude Code 2.1.274 dùng để rút số (xem docstring).
REGEX_CLAUDE = re.compile(r"prompt is too long[^0-9]*(\d+)\s*tokens?\s*>\s*(\d+)",
                          re.I)


def _qua_dai() -> str:
    # Đo bằng CHÍNH hàm ước của cổng (Task 7, `uoc_token`) — không tự quy đổi
    # ký tự/token, vì hệ số nay theo loại chữ.
    from apps.ltt_llm.executor import EXECUTOR
    from platform_core.llm.uoc_token import uoc_chuoi
    muc_tieu = EXECUTOR.input_cap(MODEL) + 5_000
    mau = "x"  # ~1 byte/token ước ⇒ vượt trần token mà thân vẫn < 1 MiB
    s = mau * (muc_tieu // max(1, uoc_chuoi(mau * 1000) // 1000) + 1)
    while uoc_chuoi(s) <= muc_tieu:
        s += mau * 1000
    return s


def _tran() -> int:
    from apps.ltt_llm.executor import EXECUTOR
    return int(EXECUTOR.input_cap(MODEL))


def _su_kien(noi_dung: bytes) -> list[dict]:
    ra = []
    for dong in noi_dung.decode("utf-8").splitlines():
        if dong.startswith("data: "):
            ra.append(json.loads(dong[6:]))
    return ra


# ── /v1/messages (Anthropic) ────────────────────────────────────────────────

@pytest.mark.parametrize("stream", [True, False])
def test_messages_qua_dai_la_400_dung_cau_Claude_Code(api, monkeypatch, stream):
    called = _dat_luong(monkeypatch)
    user_id, token = _account()
    truoc = _so_du(user_id)
    than = _than(stream=stream,
                 messages=[{"role": "user", "content": _qua_dai()}])

    r = api.post(MSG, json=than, headers=_h(token))

    assert r.status_code == 400, r.text[:300]
    body = r.json()
    assert body["type"] == "error"
    assert body["error"]["type"] == "invalid_request_error"
    m = REGEX_CLAUDE.search(body["error"]["message"])
    assert m, body["error"]["message"]
    assert int(m.group(1)) > int(m.group(2)) == _tran()
    # Số trần vẫn ở thân cho SDK của ta / khách đọc (tài liệu LOI_413).
    assert body["limit_name"] == "input_tokens"
    assert body["limit_value"] == _tran()
    assert called == [] and _so_du(user_id) == truoc


# ── /v1/responses (OpenAI Responses) ────────────────────────────────────────

def test_responses_stream_qua_dai_la_response_failed_context_length(api, monkeypatch):
    called = _dat_luong(monkeypatch)
    user_id, token = _account()
    truoc = _so_du(user_id)

    r = api.post(RSP, json={"model": MODEL, "stream": True, "input": _qua_dai()},
                 headers=_h(token))

    assert r.status_code == 200, r.text[:300]
    assert r.headers["content-type"].startswith("text/event-stream")
    ev = _su_kien(r.content)
    assert [e["type"] for e in ev] == ["response.failed"]
    resp = ev[0]["response"]
    assert resp["status"] == "failed" and resp["object"] == "response"
    assert resp["error"]["code"] == "context_length_exceeded"
    assert REGEX_CLAUDE.search(resp["error"]["message"])
    assert called == [] and _so_du(user_id) == truoc


def test_responses_KHONG_stream_qua_dai_la_400_khuon_OpenAI(api, monkeypatch):
    _dat_luong(monkeypatch)
    _user_id, token = _account()

    r = api.post(RSP, json={"model": MODEL, "input": _qua_dai()},
                 headers=_h(token))

    assert r.status_code == 400, r.text[:300]
    err = r.json()["error"]
    assert err["code"] == "context_length_exceeded"
    assert err["type"] == "invalid_request_error"
    assert REGEX_CLAUDE.search(err["message"])


# ── /v1/chat/completions (OpenAI) ───────────────────────────────────────────

def test_chat_completions_qua_dai_la_400_khuon_OpenAI(api, monkeypatch):
    import uuid
    user_id, token = _account()
    truoc = _so_du(user_id)
    r = api.post("/api/v1/chat/completions",
                 json={"model": MODEL, "max_tokens": 500,
                       "messages": [{"role": "user", "content": _qua_dai()}]},
                 headers={**_h(token), "Idempotency-Key": uuid.uuid4().hex})

    assert r.status_code == 400, r.text[:300]
    body = r.json()
    assert body["error"]["code"] == "context_length_exceeded"
    assert body["error"]["type"] == "invalid_request_error"
    assert body["error"]["param"] == "messages"
    assert REGEX_CLAUDE.search(body["error"]["message"])
    assert body["limit_value"] == _tran()
    assert _so_du(user_id) == truoc


# ── Sau 200 (vượt pool KV lúc mở) cũng phải có câu Claude Code nhận ra ─────

def test_loi_sse_context_length_mang_cau_prompt_is_too_long():
    from platform_core.llm.model_failure import model_failure
    from server.api import su_kien_loi
    for code in ("context_window_exceeded", "input_tokens_exceeded"):
        failure = model_failure(code, http_status=400, field="context",
                                limit=_tran(), actual=_tran() + 1)
        for duong in ("/v1/messages", "/v1/responses", "/v1/chat/completions"):
            khoi = su_kien_loi.loi_sse(duong, failure)
            ev = _su_kien(khoi)[0]
            err = ev.get("error") or ev["response"]["error"]
            m = REGEX_CLAUDE.search(err["message"])
            assert m and int(m.group(1)) > int(m.group(2)) == _tran(), khoi
            if duong == "/v1/responses":
                assert err["code"] == "context_length_exceeded"


# ── Nhịp chờ của Responses: một SỰ KIỆN hợp lệ, không chỉ comment ───────────

def test_bo_nhip_responses_mo_bang_created_roi_in_progress():
    from server.api import su_kien_loi
    nhip = su_kien_loi.bo_nhip("/v1/responses")
    ev = _su_kien(nhip("cho_slot") + nhip("cho_slot"))
    assert [e["type"] for e in ev] == ["response.created", "response.in_progress",
                                       "response.in_progress"]
    ids = {e["response"]["id"] for e in ev}
    assert len(ids) == 1
    assert all(e["response"]["object"] == "response" for e in ev)
    assert [e["sequence_number"] for e in ev] == [0, 1, 2]
    assert ev[1]["response"]["status"] == "in_progress"


def test_bo_nhip_messages_van_la_comment():
    from server.api import su_kien_loi
    assert su_kien_loi.bo_nhip("/v1/messages")("cho_slot").startswith(b": ")


def _cho_responses(api, monkeypatch, nhip_s: str) -> bytes:
    monkeypatch.setenv("LTT_LLM_CHO_STREAM_S", "1.2")
    monkeypatch.setenv("LTT_LLM_NHIP_TIM_CHO_S", nhip_s)
    _giu_execution_slot()
    _dat_luong(monkeypatch)
    _user_id, token = _account()
    r = api.post(RSP, json={"model": MODEL, "stream": True, "input": "xin chao"},
                 headers=_h(token))
    assert r.status_code == 200, r.text[:300]
    return r.content


def test_responses_cho_lau_hon_nhip_phat_response_in_progress(api, monkeypatch):
    from platform_core.llm import tham_so_da_luot
    noi_dung = _cho_responses(api, monkeypatch, "0.2")
    assert tham_so_da_luot.doc().nhip_tim_cho_s == 0.2   # đọc núm, không gõ số
    loai = [e["type"] for e in _su_kien(noi_dung)]
    assert "response.in_progress" in loai, noi_dung[:500]
    assert loai[0] == "response.created"
    assert loai[-1] == "response.failed"                  # hết trần chờ


def test_DOI_CHUNG_cho_ngan_hon_nhip_thi_khong_co_in_progress(api, monkeypatch):
    """Đối chứng: nhịp dài hơn cả hạn chờ ⇒ không có nhịp nào (không phát bừa)."""
    loai = [e["type"] for e in _su_kien(_cho_responses(api, monkeypatch, "30"))]
    assert "response.in_progress" not in loai
    assert loai == ["response.failed"]
