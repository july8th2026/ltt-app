"""
test_603 — Phase 03 (Text): chuẩn hoá luồng OpenAI chunk → sự kiện canonical, và
những thứ cửa nội bộ phải **giữ nguyên** khi đi qua (vision, tools, reasoning).

  1. `_DocSSE` đệm tới trọn dòng: một `data:` tới làm ba khối vẫn ra đúng một sự kiện.
  2. `finish_reason` (kể cả `length` = bị cắt) lên `response.completed` — không cắt cụt im lặng.
  3. `DemToken` đọc `timings.cache_n` ⇒ stream giảm giá token cache như đường không stream.
  4. Thân gửi lên giữ nguyên: `messages` có `image_url`, `tools`, `reasoning_effort`,
     `temperature`; `stream_options` do bên gọi đặt thì không bị đè.
  5. `tran_token_ra`: khách khai thì kẹp theo ngữ cảnh; không khai thì mặc định CỬA STREAM.
"""
from __future__ import annotations

import json

import pytest

from platform_core.runtime_noi_bo import luong as L

#: Model mà bảng giá của tệp này neo vào. D07 (dual-model 2.5) tách giá
#: theo model; những con số dưới đây là của model mặc định. Giá của
#: CẢ HAI model neo ở `test_1213_gia_theo_model.py`.
from platform_core.llm.gia_token import MODEL_GIA_MAC_DINH as _M

NL = bytes([10])


def _sse(goi):
    return b"data: " + json.dumps(goi).encode() + NL + NL


# ── 1. Đệm SSE ───────────────────────────────────────────────────────────────

def test_doc_sse_dem_toi_tron_dong():
    doc = L._DocSSE()
    tron = _sse({"choices": [{"delta": {"content": "xin chao"}}]})
    a, b, c = tron[:7], tron[7:20], tron[20:]
    assert list(doc.nhin(a)) == []
    assert list(doc.nhin(b)) == []
    ra = list(doc.nhin(c))
    assert ra == [{"choices": [{"delta": {"content": "xin chao"}}]}]


def test_doc_sse_bo_qua_DONE_va_dong_khong_json():
    doc = L._DocSSE()
    khoi = (b"event: ping" + NL + b": comment" + NL + b"data: [DONE]" + NL
            + b"data: khong-phai-json" + NL + _sse({"choices": []}))
    assert list(doc.nhin(khoi)) == [{"choices": []}]


# ── 2. finish_reason ─────────────────────────────────────────────────────────

def test_finish_reason_length_len_su_kien():
    tt: dict = {}
    sk = list(L._su_kien_tu_goi(
        {"choices": [{"delta": {"content": "a"}, "finish_reason": "length"}]}, tt))
    assert sk == [{"type": "response.delta", "text": "a"}]
    assert tt["finish_reason"] == "length"


def test_reasoning_va_tool_call_thanh_su_kien_rieng():
    tt: dict = {}
    sk = list(L._su_kien_tu_goi({"choices": [{"delta": {
        "reasoning_content": "nghi", "content": "noi",
        "tool_calls": [{"index": 0, "function": {"name": "f", "arguments": "{"}}]}}]}, tt))
    assert [s["type"] for s in sk] == ["reasoning.delta", "response.delta", "tool_call.delta"]


# ── 3. Cache token trong stream ──────────────────────────────────────────────

def test_dem_token_doc_timings_cache_n():
    from platform_core.llm.dem_token_luong import DemToken
    dem = DemToken()
    dem.nhin(_sse({"choices": [], "usage": {"prompt_tokens": 1000, "completion_tokens": 10},
                   "timings": {"cache_n": 800, "prompt_n": 200}}))
    su = dem.su_dung()
    assert (su.token_vao, su.token_ra, su.token_vao_cache) == (1000, 10, 800)
    assert su.dang_tin is True


def test_cache_lam_re_luot_stream():
    """Cùng 1.000 token vào: 800 cache phải rẻ hơn 0 cache — đúng bảng giá 50/10 per 1M."""
    from platform_core.llm import gia_token
    from platform_core.llm.cong_vlm import SuDung
    khong = gia_token.tinh(SuDung(token_vao=1000, token_ra=10, token_vao_cache=0, dang_tin=True), _M)
    co = gia_token.tinh(SuDung(token_vao=1000, token_ra=10, token_vao_cache=800, dang_tin=True), _M)
    assert co.tong_mcredit < khong.tong_mcredit


# ── 4 + 5. Thân gửi lên và trần token ra ─────────────────────────────────────

class _Exec:
    #: ⚠️ Bí danh phải là một model CÓ TRONG BẢNG GIÁ (D07, dual-model 2.5).
    #:    Trước 2.5 chỗ này dùng `"a"` — một tên bịa — và nó chạy được **chỉ vì**
    #:    tầng giá bỏ qua model. Nay `chuan_bi` giữ tiền theo bảng giá của model,
    #:    nên một tool đi qua đường tiền LLM phải khai một model đường ấy biết giá.
    def aliases(self):
        return {_M: "id-a"}

    def model_id(self, alias):
        return "id-a"

    def estimate_input(self, tin, tools=None):
        return 100

    def context_output_cap(self, token_input):
        return 5000

    @staticmethod
    def mac_dinh_cho(cua):
        return {"stream": 4096, "sync": 1024, "job": 4096}[cua]


def test_tran_token_ra_kep_theo_ngu_canh_va_mac_dinh_cua_stream():
    ex = _Exec()
    assert L.tran_token_ra({"max_tokens": 9000}, 100, ex) == 5000     # kẹp
    assert L.tran_token_ra({"max_output_tokens": 7}, 100, ex) == 7
    assert L.tran_token_ra({}, 100, ex) == 4096                        # cửa stream, KHÔNG phải 1024
    assert L.tran_token_ra({"max_tokens": True}, 100, ex) == 4096      # bool không phải số


def test_uoc_tin_nhan_gom_system_input_va_tools():
    tin = L.uoc_tin_nhan({"system": "he thong", "messages": [{"role": "user", "content": "a"}],
                          "input": "b", "tools": [{"type": "function"}]})
    assert len(tin) == 4 and tin[0] == {"content": "he thong"}
    assert L.uoc_tin_nhan({}) == []


def test_chuan_bi_giu_nguyen_vision_tools_reasoning(monkeypatch, tmp_path):
    """Thân gửi lên máy B phải là thân khách gửi + alias đã dịch + trần đã kẹp — không hơn."""
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "c.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session
    Base.metadata.create_all(get_engine())
    from platform_core import credit, registry as reg
    from platform_core.users import tao_nguoi_dung

    tool = reg.ToolSpec(name="text.thu603", job_type="t603.j", description="d",
                        params_schema={"messages": {"type": "json[]"}},
                        returns={"content": "text"},
                        sync_executor="tests.test_603_text_luong_chuan_hoa:EXEC")
    manifest = reg.AppManifest(slug="t603", display_name="x", route_prefix="/t603",
                               job_types=("t603.j",), credit_cost=lambda p: 1,
                               tools=(tool,))
    gen = get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="c603@example.com", password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, u.id, 500, by="test")
        db.commit()
        than = {"model": _M, "temperature": 0.3, "reasoning_effort": "xhigh",
                "tools": [{"type": "function", "function": {"name": "f"}}],
                "stream_options": {"include_usage": True, "khac": 1},
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": "anh nay la gi"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}}]}]}
        cb = L.chuan_bi(db, user_id=u.id, tool_name="text.thu603", than=than,
                        duong="/v1/chat/completions", tim=lambda _n: (manifest, tool))
        gui = cb.than_gui
        assert gui["model"] == "id-a"
        assert gui["messages"] == than["messages"]              # vision parts nguyên xi
        assert gui["tools"] == than["tools"]
        assert gui["reasoning_effort"] == "xhigh" and gui["temperature"] == 0.3
        assert gui["stream_options"] == {"include_usage": True, "khac": 1}
        assert gui["max_tokens"] == 4096                          # mặc định cửa stream
        assert cb.lease_id == ""                                  # tool không khai admission
        assert cb.da_giu >= 1 and int(credit.so_du(db, u.id)) == 500 - cb.da_giu
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()


EXEC = _Exec()
