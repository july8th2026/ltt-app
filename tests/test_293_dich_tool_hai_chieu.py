"""Dịch **công cụ** giữa hợp đồng Anthropic và giao thức OpenAI.

🔴 VÌ SAO TỆP NÀY TỒN TẠI — ĐO 25/08, VÀ NÓ LÀ LỖI IM LẶNG THỨ TƯ TRONG TUẦN.

   `_mot_cuc` dựng `{"model", "messages", "max_tokens"}` rồi thôi — **`tools`
   không đi đâu cả**. Tác tử của khách khai đủ công cụ, gửi lên, và model **không
   bao giờ nhìn thấy chúng**. Không lỗi, không cảnh báo: model chỉ trả lời bằng
   chữ như thể khách chưa từng có tool.

⛔ Triệu chứng khách thấy: *"model này kém, không biết dùng tool"*. Nguyên nhân
   thật: cổng đánh rơi phần khai báo. Lại một lần nữa **triệu chứng không chỉ về
   phía nguyên nhân** — đúng họ với ba lỗi hôm 24/08.

⚠️ Ba cái bẫy của phép dịch này, và cả ba đều hỏng ở tận trong mã của khách:

   1. `arguments` của OpenAI là **chuỗi JSON**; `input` của Anthropic là **object**.
   2. `any` của Anthropic = `required` của OpenAI. Không trùng tên.
   3. Một tin `user` chứa **nhiều** `tool_result` phải tách thành **nhiều** tin
      `role="tool"`, mỗi tin mang `tool_call_id` riêng. Gộp lại là mất liên kết
      giữa kết quả và lượt gọi.
"""
from __future__ import annotations

import json

import pytest

from server.api import tool_dich as td


# ── Chiều đi: Anthropic → OpenAI ─────────────────────────────────────────────

def test_khai_bao_tool_doi_dung_ten_truong():
    ra = td.sang_openai_tools([{
        "name": "doc_tep",
        "description": "doc mot tep",
        "input_schema": {"type": "object",
                         "properties": {"duong": {"type": "string"}}},
    }])
    assert ra == [{
        "type": "function",
        "function": {
            "name": "doc_tep",
            "description": "doc mot tep",
            "parameters": {"type": "object",
                           "properties": {"duong": {"type": "string"}}},
        },
    }]


def test_thieu_input_schema_van_ra_object_rong_chu_khong_bo_trong():
    """Bỏ trắng `parameters` làm một số bộ giải mã từ chối cả lượt."""
    ra = td.sang_openai_tools([{"name": "khong_tham_so"}])
    assert ra[0]["function"]["parameters"] == {"type": "object", "properties": {}}


def test_bo_qua_tool_PHIA_MAY_CHU_cua_anthropic():
    """`web_search_…` chạy trên hạ tầng Anthropic — ta không chạy được.

    Gửi lên máy B một thứ nó chắc chắn không hiểu thì tệ hơn là bỏ qua.
    """
    ra = td.sang_openai_tools([{"type": "web_search_20260209", "name": "web_search"},
                               {"name": "cua_khach", "input_schema": {}}])
    assert [t["function"]["name"] for t in ra] == ["cua_khach"]


def test_khong_khai_tool_thi_tra_None_chu_khong_phai_danh_sach_rong():
    """`None` = "khách không khai gì"; `[]` là một lời khai **có** mà rỗng."""
    for x in (None, [], "khong phai danh sach"):
        assert td.sang_openai_tools(x) is None


@pytest.mark.parametrize("anthropic,openai", [
    ("auto", "auto"),
    ("any", "required"),        # ⚠️ KHONG trung ten
    ("none", "none"),
    ({"type": "auto"}, "auto"),
    ({"type": "any"}, "required"),
    ({"type": "tool", "name": "doc_tep"},
     {"type": "function", "function": {"name": "doc_tep"}}),
])
def test_tool_choice_doi_dung(anthropic, openai):
    assert td.sang_openai_tool_choice(anthropic) == openai


# ── Vòng gọi tool trong `messages` ───────────────────────────────────────────

def test_khoi_tool_use_thanh_tool_calls_va_input_thanh_CHUOI_JSON():
    ra = td.sang_openai_messages([
        {"role": "user", "content": "doc tep a.txt"},
        {"role": "assistant", "content": [
            {"type": "text", "text": "de toi doc"},
            {"type": "tool_use", "id": "toolu_1", "name": "doc_tep",
             "input": {"duong": "a.txt"}},
        ]},
    ])
    assert ra[0] == {"role": "user", "content": "doc tep a.txt"}
    g = ra[1]["tool_calls"][0]
    assert g["id"] == "toolu_1" and g["function"]["name"] == "doc_tep"
    # ⚠️ CHUOI, khong phai object.
    assert isinstance(g["function"]["arguments"], str)
    assert json.loads(g["function"]["arguments"]) == {"duong": "a.txt"}


def test_NHIEU_tool_result_tach_thanh_NHIEU_tin_role_tool():
    """🔴 Gộp lại là mất liên kết giữa kết quả và lượt gọi.

    Model sẽ không biết kết quả nào của tool nào — và nó **không** báo lỗi, nó
    chỉ suy luận sai.
    """
    ra = td.sang_openai_messages([
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": "noi dung A"},
            {"type": "tool_result", "tool_use_id": "toolu_2", "content": [
                {"type": "text", "text": "noi dung B"}]},
        ]},
    ])
    assert len(ra) == 2
    assert ra[0] == {"role": "tool", "tool_call_id": "toolu_1",
                     "content": "noi dung A"}
    assert ra[1] == {"role": "tool", "tool_call_id": "toolu_2",
                     "content": "noi dung B"}


def test_chu_di_kem_tool_result_khong_bi_nuot():
    """Khách vừa trả kết quả tool vừa nói thêm — cả hai đều phải tới model."""
    ra = td.sang_openai_messages([
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": "xong"},
            {"type": "text", "text": "gio tom tat giup"},
        ]},
    ])
    assert [m["role"] for m in ra] == ["tool", "user"]
    assert ra[1]["content"] == "gio tom tat giup"


def test_thu_tu_duoc_giu_nguyen():
    """`tool` phải đứng ngay sau tin assistant đã gọi nó."""
    ra = td.sang_openai_messages([
        {"role": "user", "content": "x"},
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "t1", "name": "f", "input": {}}]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]},
        {"role": "assistant", "content": "xong roi"},
    ])
    assert [m["role"] for m in ra] == ["user", "assistant", "tool", "assistant"]


# ── Chiều về: OpenAI → Anthropic ─────────────────────────────────────────────

def test_tool_calls_thanh_khoi_tool_use_va_input_thanh_OBJECT():
    khoi = td.sang_anthropic_content("de toi doc", [
        {"id": "call_1", "type": "function",
         "function": {"name": "doc_tep", "arguments": '{"duong": "a.txt"}'}},
    ])
    assert khoi[0] == {"type": "text", "text": "de toi doc"}
    assert khoi[1] == {"type": "tool_use", "id": "call_1", "name": "doc_tep",
                       "input": {"duong": "a.txt"}}


def test_JSON_hong_KHONG_lam_bien_mat_khoi_tool_use():
    """Model sinh JSON hỏng là chuyện có thật.

    ⛔ Bỏ cả khối là quay về đúng ca "hứa `tool_use` mà không có khối" — client
       treo. Giữ khối lại, đưa nguyên chuỗi vào để khách còn nhìn thấy.
    """
    khoi = td.sang_anthropic_content("", [
        {"id": "c1", "function": {"name": "f", "arguments": "{khong phai json"}}])
    tu = [k for k in khoi if k["type"] == "tool_use"]
    assert len(tu) == 1
    assert tu[0]["input"]["_raw"] == "{khong phai json"


def test_content_KHONG_BAO_GIO_rong():
    """Mảng rỗng làm một số client coi là lỗi giải mã."""
    assert td.sang_anthropic_content("", []) == [{"type": "text", "text": ""}]
    assert td.sang_anthropic_content("   ", None)


# ── Nối vào đường thật ───────────────────────────────────────────────────────

@pytest.fixture()
def st():
    import importlib
    return importlib.import_module("server.api.streaming")


class _Kq:
    noi_dung, finish_reason = "de toi doc", "tool_calls"
    token_vao = token_ra = token_vao_cache = 1
    do_duoc = True
    tool_calls = ({"id": "call_1", "type": "function",
                   "function": {"name": "doc_tep",
                                "arguments": '{"duong": "a.txt"}'}},)


def test_phan_hoi_that_co_khoi_tool_use_va_stop_reason_khop(st):
    d = st._dang_anthropic(_Kq(), "ltt_llm", "ms-x")
    assert d["stop_reason"] == "tool_use"
    loai = [k["type"] for k in d["content"]]
    assert "tool_use" in loai, "khai tool_use ma khong co khoi -> client treo"


def test_co_khoi_tool_use_thi_stop_reason_PHAI_la_tool_use(st):
    """Ngược lại cũng phải đúng: thượng nguồn báo `stop` mà vẫn có lời gọi tool.

    Nói `end_turn` trong khi vừa đưa ra một lời gọi tool là bảo client **đừng
    chạy** nó — vòng lặp tác tử dừng ngay ở bước đầu.
    """
    kq = _Kq()
    kq.finish_reason = "stop"
    d = st._dang_anthropic(kq, "ltt_llm", "ms-x")
    assert d["stop_reason"] == "tool_use"


def test_ma_nguon_CO_truyen_tools_len_model(st):
    """🔴 Chốt chính lỗi đã có: `tools` phải đi tiếp, không được rơi ở cổng."""
    import pathlib
    ma = pathlib.Path(st.__file__).read_text(encoding="utf-8")
    than = ma.split("def _mot_cuc", 1)[1].split("\ndef ", 1)[0]
    assert "sang_openai_tools" in than, (
        "`tools` cua khach khong duoc truyen len model -> tac tu khong dung "
        "duoc cong cu, va KHONG co trieu chung nao")
