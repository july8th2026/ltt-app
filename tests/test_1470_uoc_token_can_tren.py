"""test_1470 — ước token vào là CẬN TRÊN thật, A và B cùng một hàm (Task 7, R-2 Phương án C).

Số thật: ``tests/fixtures/ngu_lieu_token/ky_vong_engine.json`` (9cc80640) — ``count_tokens`` /
``input_tokens`` của engine, lấy MAX qua hai model (qwen38-api, qwen35-api), nên một
phép so ở đây phủ cả hai model.

Bộ ước cũ ``ký tự / 2,5`` ước THIẾU: code 0,74× · chữ Trung 0,42× · hex 0,45× · emoji 0,16×
— giữ chỗ nhỏ hơn thật ⇒ tràn KV giết luồng SAU 200. Và ước THỪA văn xuôi Anh 2,25× ⇒ phí suất.
"""
from __future__ import annotations

import json
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
NGU_LIEU = GOC / "tests" / "fixtures" / "ngu_lieu_token"
KY_VONG = json.loads((NGU_LIEU / "ky_vong_engine.json").read_text(encoding="utf-8"))
MAU = sorted(KY_VONG)
VAN_XUOI = ("en_prose", "vi_markdown")


def _than(ten: str) -> dict:
    return json.loads((NGU_LIEU / f"{ten}.json").read_text(encoding="utf-8"))["than"]


def _that(ten: str) -> int:
    return int(KY_VONG[ten]["engine_tokens"])


def _uoc_a_luong(than: dict) -> int:
    """Máy A, cửa stream/đồng bộ công khai: ``uoc_tin_nhan`` → ``executor.estimate_input``."""
    from apps.ltt_llm.executor import EXECUTOR
    from platform_core.runtime_noi_bo.luong import uoc_tin_nhan
    return int(EXECUTOR.estimate_input(uoc_tin_nhan(than)))


def _uoc_a_job(than: dict) -> int:
    """Máy A, cửa job (``manifest._cost``): ``uoc_token_vao(messages, tools)``."""
    from apps.ltt_llm.features import uoc_token_vao
    return int(uoc_token_vao(than.get("messages"), than.get("tools")))


def _uoc_b(than: dict) -> int:
    """Máy B: ``llm_gateway.ngan_sach.do_yeu_cau`` (không ảnh ⇒ token_vao = văn bản + khuôn)."""
    from llm_gateway.ngan_sach import do_yeu_cau
    return int(do_yeu_cau(than).token_vao)


DUONG = {"a_luong": _uoc_a_luong, "a_job": _uoc_a_job, "b": _uoc_b}


def test_ngu_lieu_co_du_cac_lop_da_do():
    assert {"en_prose", "vi_markdown", "code_py", "cjk_zh", "hex", "emoji", "base64",
            "json_minified", "numbers_csv", "tools_60", "tool_calls_history"} <= set(MAU)


# ── Step 1: cận trên trên MỌI mẫu, MỌI đường ước ────────────────────────────

@pytest.mark.parametrize("duong", sorted(DUONG))
@pytest.mark.parametrize("ten", MAU)
def test_uoc_la_can_tren_cua_so_that(ten, duong):
    uoc = DUONG[duong](_than(ten))
    that = _that(ten)
    assert uoc >= that, f"{duong} ước {uoc} < thật {that} ở {ten} ({uoc / that:.2f}×)"


# ── Step 2: không quá tay trên văn xuôi ─────────────────────────────────────

@pytest.mark.parametrize("duong", sorted(DUONG))
@pytest.mark.parametrize("ten", VAN_XUOI)
def test_van_xuoi_khong_uoc_qua_1_5_lan(ten, duong):
    uoc = DUONG[duong](_than(ten))
    that = _that(ten)
    assert uoc <= 1.5 * that, f"{duong} ước {uoc} = {uoc / that:.2f}× thật ở {ten}"


# ── Step 4: A và B cùng MỘT hàm ─────────────────────────────────────────────

def test_hai_ban_uoc_token_giong_het_tung_byte():
    """Máy B không có ``platform_core`` (Q102) ⇒ chép; lệch một byte là A ⊆ B gãy im lặng."""
    a = (GOC / "platform_core" / "llm" / "uoc_token.py").read_bytes()
    b = (GOC / "llm_gateway" / "uoc_token.py").read_bytes()
    assert a == b


def test_ca_hai_may_goi_dung_module_uoc_token():
    """Không bản ước thứ ba: hằng ``KY_TU_MOI_TOKEN`` cũ không còn định nghĩa ở đâu."""
    import re
    for tep in ("apps/ltt_llm/ngan_sach.py", "apps/ltt_llm/features.py",
                "llm_gateway/ngan_sach.py"):
        van = (GOC / tep).read_text(encoding="utf-8")
        assert not re.search(r"^KY_TU_MOI_TOKEN\s*=", van, re.M), tep
    assert "uoc_token" in (GOC / "apps/ltt_llm/features.py").read_text(encoding="utf-8")
    assert "uoc_token" in (GOC / "llm_gateway/ngan_sach.py").read_text(encoding="utf-8")


_HINH_DANG = {
    "messages_system_list_cache": {
        "system": [{"type": "text", "text": "Bạn là coding agent.",
                    "cache_control": {"type": "ephemeral"}}],
        "messages": [
            {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_1",
                                               "name": "Read",
                                               "input": {"file_path": "src/app.py", "limit": 4000}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_1",
                                          "content": [{"type": "text", "text": "def f():\n    return 1\n" * 50}]}]}],
        "tools": [{"name": "Read", "description": "Đọc một tệp",
                   "input_schema": {"type": "object",
                                    "properties": {"file_path": {"type": "string"}}}}]},
    "responses_instructions_items": {
        "instructions": "You are Codex. " * 40,
        "input": [{"type": "message", "role": "user",
                   "content": [{"type": "input_text", "text": "Sửa lỗi 😀 ở mã 缓存"}]},
                  {"type": "function_call", "call_id": "c1", "name": "shell",
                   "arguments": "{\"cmd\": [\"rg\", \"deadbeef0123\"]}"},
                  {"type": "function_call_output", "call_id": "c1", "output": "a1b2c3\n" * 30}],
        "tools": [{"type": "function", "name": "shell", "parameters": {"type": "object"}}]},
    "responses_input_str": {"input": "xin chào " * 100},
    "chat_tool_calls": _than("tool_calls_history"),
}


@pytest.mark.parametrize("hinh", sorted(_HINH_DANG))
def test_A_giu_khong_it_hon_B_dem(hinh):
    """A ⊆ B: phần A giữ (cửa stream lẫn job) ≥ số B tự đo, cùng body — và chỉ hơn
    ở khuôn của các phần tử bọc (system/instructions/tools), không phải một phép ước khác."""
    than = _HINH_DANG[hinh]
    b = _uoc_b(than)
    a = _uoc_a_luong(than)
    assert b <= a <= b + 16 * 4, (a, b)
    if "messages" in than:
        assert _uoc_a_job(than) >= _uoc_b({k: than[k] for k in ("messages", "tools") if k in than})


# ── Chứng minh: không hệ số nào vượt cận byte ───────────────────────────────

@pytest.mark.parametrize("s", [
    "a", "ab", "xyz", "the quick brown fox", "getElementById HTTPServer",
    "Nền tảng xử lý hàng đợi", "缓存令牌", "😀🚀🔥✅", "0123456789", "    \n\n\t ",
    "{\"a\":[1,2]}", "ÀÉÎÕÜ", "_" * 10, "١٢٣", "Z" * 1000, "aZkQ+/9=" * 50,
])
def test_uoc_chuoi_khong_vuot_can_byte(s):
    from platform_core.llm.uoc_token import uoc_chuoi
    assert 1 <= uoc_chuoi(s) <= len(s.encode("utf-8"))


def test_chu_so_dung_mot_token_moi_chu_so():
    from platform_core.llm.uoc_token import uoc_chuoi
    assert uoc_chuoi("1234567890") == 10


def test_khuon_la_so_do_nhan_bien():
    from platform_core.llm.uoc_token import khuon
    assert khuon(1, 0) == 256 + 16
    assert khuon(3, 2) == 256 + 16 * 3 + 64 * 2


def test_khach_khong_gia_duoc_khoi_tool_de_A_bo_dem():
    """``so_tool`` là khoá JSON thì khách gửi được; A phải vẫn đếm đủ tin nhắn ấy."""
    tool_calls = [{"id": "c", "type": "function",
                   "function": {"name": "read", "arguments": "{\"p\": \"" + "q" * 4000 + "\"}"}}]
    than = {"messages": [{"role": "assistant", "content": "x", "so_tool": 0,
                          "tool_calls": tool_calls}]}
    assert _uoc_a_luong(than) >= _uoc_b(than) >= 4000
    assert _uoc_a_job(than) >= 4000
