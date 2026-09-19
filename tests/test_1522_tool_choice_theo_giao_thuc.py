"""test_1522 — `tool_choice` theo ĐÚNG giao thức của cửa stream. (phát hiện ở T4 P2, 19/09)

## Lỗi

`features.kiem_tham_so_sinh` (075af95e, 14/09) kiểm `tool_choice` theo khuôn
`/chat/completions` — **chỉ chuỗi** `none|auto|required` — rồi được gọi ở CẢ hai
cửa stream. Nhưng:

  * `/messages` (Anthropic) chỉ có dạng ĐỐI TƯỢNG: `{"type": "auto"|"any"|"tool"|"none",
    "name"?, "disable_parallel_tool_use"?}` ⇒ MỌI `tool_choice` hợp lệ bị từ chối.
    Claude Code 2.1.273 gửi `{"type":"tool","name":"web_search"}` (công cụ
    WebSearch) và `{"type":"auto"}` khi hạ cấp vì đang bật suy nghĩ.
  * `/responses` (OpenAI Responses) có thêm `{"type":"function","name":X}` — Codex
    ép một tool (đo 27/08, `streaming.py`) ⇒ cũng bị từ chối.

Và "từ chối" ở đây là **500**, không phải 400 (đo 19/09 trên giàn này): bộ kiểm
ném `features.ThamSoSai` của app, còn cửa HTTP chỉ bắt `luong.ThamSoSai`. Cùng lối
thoát đó làm `top_p=5` trên cửa stream thành 500 (ca cuối tệp).

## Máy B làm gì với từng dạng (tra nguồn, llama.cpp @ ec928150)

  * `/v1/messages`: `server_chat_convert_anthropic_to_oai` (`tools/server/server-chat.cpp`)
    chỉ đọc ĐỐI TƯỢNG: `auto`→`"auto"`, `any`/`tool`→`"required"` (**mất tên tool**),
    `none` **không ánh xạ** ⇒ mặc định auto; `disable_parallel_tool_use` bị bỏ.
  * `/v1/responses`: `tool_choice` chép nguyên sang chat; `json_value<std::string>`
    gặp đối tượng ⇒ cảnh báo, dùng `"auto"` (**ép tool mất im lặng**).

⇒ A phải chuẩn hoá: `tool`/`function` ⇒ thu `tools` còn đúng tool đó + "bắt buộc";
`none` (Anthropic) ⇒ gỡ `tools`; thứ B không làm được ⇒ 400 nói rõ.

Đối chứng (tiêm lỗi, chạy tay khi viết): mã cũ (HEAD) ⇒ 20/24 ĐỎ; gỡ lời gọi
`chuan_hoa_tool_choice` ở `tien_kiem` ⇒ 15 ĐỎ; bỏ bước thu `tools` ⇒ 4 ĐỎ.
"""
from __future__ import annotations

import json

import pytest

from tests import test_1511_so_request_phien as _t1511
from tests.test_1511_so_request_phien import (MSG, RSP, _account, _h_claude,
                                              _h_codex, _khoi, _than, _than_rsp)

api = _t1511.api

TOOL_A = {"name": "doc_tep", "description": "doc mot tep",
          "input_schema": {"type": "object", "properties": {"p": {"type": "string"}}}}
TOOL_B = {"name": "ghi_tep", "description": "ghi mot tep",
          "input_schema": {"type": "object", "properties": {"p": {"type": "string"}}}}
FN_A = {"type": "function", "name": "doc_tep",
        "parameters": {"type": "object", "properties": {}}}
FN_B = {"type": "function", "name": "ghi_tep",
        "parameters": {"type": "object", "properties": {}}}


def _bat_than(monkeypatch):
    from platform_core.llm import luong_vlm
    da_goi: list[dict] = []

    class GiaLuong:
        def __init__(self, ks):
            self.ma, self.content_type, self.luong = 200, "text/event-stream", ks

        def xong(self, tokens=0):
            pass

        def hong(self, exc):
            pass

        def dong(self):
            pass

    def gia(db, *, duong, than, timeout_s=900.0, request_id="", **_meta):
        da_goi.append(json.loads(json.dumps(than)))
        return GiaLuong(_khoi())

    monkeypatch.setattr(luong_vlm, "mo", gia)
    return da_goi


def _msg(api, token, **g):
    r = api.post(MSG, json=_than(tools=[TOOL_A, TOOL_B], **g), headers=_h_claude(token))
    r.read()
    return r


# ── /messages stream ───────────────────────────────────────────────────────

def test_messages_auto_di_qua_nguyen_dang_anthropic(api, monkeypatch):
    goi = _bat_than(monkeypatch)
    _u, token = _account()
    r = _msg(api, token, tool_choice={"type": "auto"})
    assert r.status_code == 200, r.text
    (g,) = goi
    assert g["tool_choice"] == {"type": "auto"}
    assert [t["name"] for t in g["tools"]] == ["doc_tep", "ghi_tep"]


def test_messages_any_giu_tools(api, monkeypatch):
    goi = _bat_than(monkeypatch)
    _u, token = _account()
    assert _msg(api, token, tool_choice={"type": "any"}).status_code == 200
    (g,) = goi
    assert g["tool_choice"] == {"type": "any"} and len(g["tools"]) == 2


def test_messages_tool_co_ten_thu_tools_con_dung_tool_do(api, monkeypatch):
    """B ánh xạ `tool` → `required` và MẤT tên ⇒ A thu `tools` còn đúng tool được ép."""
    goi = _bat_than(monkeypatch)
    _u, token = _account()
    r = _msg(api, token, tool_choice={"type": "tool", "name": "ghi_tep"})
    assert r.status_code == 200, r.text
    (g,) = goi
    assert g["tool_choice"] == {"type": "any"}
    assert [t["name"] for t in g["tools"]] == ["ghi_tep"]


def test_messages_none_go_tools(api, monkeypatch):
    """B không ánh xạ `none` (mặc định auto) ⇒ A gỡ `tools`: không tool thì không gọi được."""
    goi = _bat_than(monkeypatch)
    _u, token = _account()
    assert _msg(api, token, tool_choice={"type": "none"}).status_code == 200
    (g,) = goi
    assert "tool_choice" not in g and "tools" not in g


@pytest.mark.parametrize("tc, chu", [
    ({"type": "tool", "name": "khong_co"}, "khong_co"),
    ({"type": "tool"}, "name"),
    ({"type": "bua"}, "bua"),
    ({"type": "auto", "disable_parallel_tool_use": True}, "disable_parallel_tool_use"),
    ({"type": "auto", "disable_parallel_tool_use": "co"}, "disable_parallel_tool_use"),
    ("required", "tool_choice"),
])
def test_messages_sai_thi_400_noi_ro_va_khong_goi_B(api, monkeypatch, tc, chu):
    goi = _bat_than(monkeypatch)
    _u, token = _account()
    r = _msg(api, token, tool_choice=tc)
    assert r.status_code == 400, (tc, r.status_code, r.text)
    assert chu in r.text, r.text
    assert goi == [], "tham so sai ma van goi may B"


def test_messages_any_khong_tools_thi_400(api, monkeypatch):
    goi = _bat_than(monkeypatch)
    _u, token = _account()
    r = api.post(MSG, json=_than(tool_choice={"type": "any"}), headers=_h_claude(token))
    assert r.status_code == 400 and "tools" in r.text
    assert goi == []


def test_messages_disable_parallel_false_van_qua(api, monkeypatch):
    goi = _bat_than(monkeypatch)
    _u, token = _account()
    r = _msg(api, token, tool_choice={"type": "auto", "disable_parallel_tool_use": False})
    assert r.status_code == 200, r.text
    assert goi[0]["tool_choice"] == {"type": "auto"}


# ── /responses stream ──────────────────────────────────────────────────────

def _rsp(api, token, **g):
    r = api.post(RSP, json=_than_rsp(tools=[FN_A, FN_B], **g), headers=_h_codex(token))
    r.read()
    return r


@pytest.mark.parametrize("tc", ["auto", "required", "none"])
def test_responses_chuoi_di_qua(api, monkeypatch, tc):
    goi = _bat_than(monkeypatch)
    _u, token = _account()
    assert _rsp(api, token, tool_choice=tc).status_code == 200
    assert goi[0]["tool_choice"] == tc and len(goi[0]["tools"]) == 2


def test_responses_ep_function_thu_tools(api, monkeypatch):
    """Codex ép một tool. B gặp đối tượng ⇒ dùng "auto" im lặng ⇒ A dịch sang chuỗi."""
    goi = _bat_than(monkeypatch)
    _u, token = _account()
    r = _rsp(api, token, tool_choice={"type": "function", "name": "doc_tep"})
    assert r.status_code == 200, r.text
    (g,) = goi
    assert g["tool_choice"] == "required"
    assert [t["name"] for t in g["tools"]] == ["doc_tep"]


def test_responses_allowed_tools(api, monkeypatch):
    goi = _bat_than(monkeypatch)
    _u, token = _account()
    r = _rsp(api, token, tool_choice={"type": "allowed_tools", "mode": "auto",
                                      "tools": [{"type": "function", "name": "ghi_tep"}]})
    assert r.status_code == 200, r.text
    assert goi[0]["tool_choice"] == "auto"
    assert [t["name"] for t in goi[0]["tools"]] == ["ghi_tep"]


@pytest.mark.parametrize("tc", [
    {"type": "function", "name": "khong_co"},
    {"type": "web_search_preview"},
    "bat_buoc",
])
def test_responses_sai_thi_400(api, monkeypatch, tc):
    goi = _bat_than(monkeypatch)
    _u, token = _account()
    r = _rsp(api, token, tool_choice=tc)
    assert r.status_code == 400, (tc, r.text)
    assert "tool_choice" in r.text
    assert goi == []


# ── /messages KHÔNG stream: hành vi có sẵn, chốt lại ──────────────────────────

def test_messages_mot_cuc_auto_qua_con_ep_tool_400_noi_ro(api, monkeypatch):
    _t1511._dat_mot_cuc(monkeypatch)
    _u, token = _account()
    for tc, ma in (({"type": "auto"}, 200), ({"type": "any"}, 400)):
        than = _than(max_tokens=2_000, tools=[TOOL_A], tool_choice=tc)
        than.pop("stream")
        r = api.post(MSG, json=than, headers=_h_claude(token))
        assert r.status_code == ma, (tc, r.text)
        if ma == 400:
            assert "non-streaming" in r.text


# ── Hàm thuần ───────────────────────────────────────────────────────────────

def test_ham_thuan_khong_sua_than_goc_va_giu_thu_tu_tools():
    from platform_core.runtime_noi_bo.luong import chuan_hoa_tool_choice

    goc = {"tools": [TOOL_A, TOOL_B], "tool_choice": {"type": "tool", "name": "doc_tep"}}
    gui = {"tools": list(goc["tools"]), "tool_choice": dict(goc["tool_choice"])}
    chuan_hoa_tool_choice(gui, "/v1/messages")
    assert gui["tools"] == [TOOL_A] and len(goc["tools"]) == 2
    vang = {"model": "m"}
    chuan_hoa_tool_choice(vang, "/v1/messages")
    assert vang == {"model": "m"}, "khong khai tool_choice thi khong duoc them gi"


# ── Lỗi tham số của app ở cửa stream: 400, không 500 ─────────────────────────

@pytest.mark.parametrize("duong", ["msg", "rsp"])
def test_top_p_sai_o_cua_stream_la_400_khong_phai_500(api, monkeypatch, duong):
    """`features.ThamSoSai` không phải `luong.ThamSoSai` — trước 19/09 thoát thành 500."""
    goi = _bat_than(monkeypatch)
    _u, token = _account()
    if duong == "msg":
        r = api.post(MSG, json=_than(top_p=5), headers=_h_claude(token))
    else:
        r = api.post(RSP, json=_than_rsp(top_p=5), headers=_h_codex(token))
    assert r.status_code == 400, r.text
    assert "top_p" in r.text and goi == []
