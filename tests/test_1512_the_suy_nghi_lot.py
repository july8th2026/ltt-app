"""T1b — thẻ `</think>` lọt vào câu trả lời khi budget suy nghĩ cắt ngang.

Ca thật production 18/09 (1/8 lượt sau T1, `ltt-3.5`, budget 988):
    content = "Hà Nội\\n</think>\\n\\nHà Nội"
Gốc: llama.cpp#28182 (budget ép `</think>` ⇒ parser lệch, thẻ thứ hai lọt),
#27661 (parser chỉ tách ở `</think>` đầu tiên). Luật lọc: `platform_core/llm/
the_suy_nghi.py`. Test ĐỐI CHỨNG quan trọng ngang test sửa: lọc tham làm mất chữ
của khách (LiteLLM#10702, vLLM#56658).
"""
from __future__ import annotations

import importlib

import pytest

from platform_core.llm.cong_vlm import CongVlm
from platform_core.llm.the_suy_nghi import tach_the_lot


# ── 1. Ca lọt thật: phần trước thẻ là suy nghĩ dở ────────────────────────────

def test_ca_production_18_09_tach_ve_suy_nghi():
    noi, nghi = tach_the_lot("Hà Nội\n</think>\n\nHà Nội", "Người dùng hỏi thủ đô")
    assert noi == "Hà Nội"
    assert "</think>" not in noi
    assert nghi == "Người dùng hỏi thủ đô\nHà Nội"


def test_ca_do_lai_19_09_engine_B_responses_stream():
    """Đo lại engine B 19/09 (`/v1/responses` stream, budget 988 cắt ở 986 token):
    suy nghĩ dở nhiều đoạn, có cả chữ trong nháy, rồi `\\n</think>\\n\\n` + câu đáp."""
    goc = ('is "thu do Viet Nam", which is three words.\n\nWait, maybe "dùng một '
           'từ" is a typo.\n\nSo the answer is: "Thủ đô Việt Nam là Hà Nội."'
           "\n</think>\n\nThủ đô Việt Nam là Hà Nội.")
    noi, nghi = tach_the_lot(goc, "The user asks")
    assert noi == "Thủ đô Việt Nam là Hà Nội."
    assert nghi.startswith("The user asks\nis \"thu do Viet Nam\"")
    assert nghi.endswith('"Thủ đô Việt Nam là Hà Nội."')


def test_budget_cat_giua_khoi_ma_cua_suy_nghi_rao_ho_van_tach():
    """Đo 19/09 (budget 188, `/v1/messages` stream): phần lọt mở bằng "```" không
    bao giờ đóng — rào hở — rồi `\\n</think>\\n\\n` + câu đáp."""
    goc = ("```\n        $17 \\times 3 = 51$\n        $340 + 51 = 391$\n"
           "    *   Result: 391\n\n5.  **Final Output Generation:** 17 x 23 = 391.cw"
           "\n</think>\n\n17 x 23 = 391.")
    noi, nghi = tach_the_lot(goc, "")
    assert noi == "17 x 23 = 391."
    assert nghi.startswith("```") and nghi.endswith("391.cw")


def test_ca_llama_cpp_28182_the_dinh_lien_cau_tra_loi_khong_co_xuong_dong():
    """#28182: `' ... </think>I can help'` — chữ liền sau thẻ, KHÔNG phải hình thẻ
    máy của template Qwen ⇒ luật chọn không đoán (ghi rõ để ai đổi luật biết)."""
    goc = " the user asks what I can do... </think>I can help you with..."
    assert tach_the_lot(goc, "r") == (goc, "r")


def test_suy_nghi_rong_budget_0_van_tach():
    """`max_tokens` ≤ 512 ⇒ budget 0 ⇒ engine ép `</think>` ngay ⇒ reasoning rỗng,
    model nghĩ luôn trong content rồi tự đóng."""
    noi, nghi = tach_the_lot("Để xem, 17 x 23...\n</think>\n\n391", "")
    assert (noi, nghi) == ("391", "Để xem, 17 x 23...")


def test_mo_lai_khoi_suy_nghi_o_dau_cau_tra_loi():
    noi, nghi = tach_the_lot("<think>\nnghĩ tiếp\n</think>\n\nĐáp án: 42", "a")
    assert (noi, nghi) == ("Đáp án: 42", "a\nnghĩ tiếp")


def test_the_o_duoi_chi_bo_the_khong_bao_gio_lam_rong_cau_tra_loi():
    assert tach_the_lot("Hà Nội\n</think>\n", "r") == ("Hà Nội", "r")
    assert tach_the_lot("Hà Nội</think>", "r") == ("Hà Nội", "r")


def test_the_o_dau_chi_bo_the():
    assert tach_the_lot("\n</think>\n\nHà Nội", "r") == ("Hà Nội", "r")


def test_chi_the_dau_tien_bi_xu_the_sau_giu_nguyen():
    noi, _ = tach_the_lot("x\n</think>\nA\n</think>\nB", "")
    assert noi == "A\n</think>\nB"


# ── 2. ĐỐI CHỨNG: văn bản hợp lệ nhắc tới thẻ KHÔNG bị đụng ────────────────────

@pytest.mark.parametrize("van_ban", [
    # khối mã rào
    "Template Qwen đóng suy nghĩ thế này:\n```jinja\n{{ '</think>\n\n' }}\n</think>\n```\nXong.",
    "Ví dụ:\n~~~\nreasoning here\n</think>\n~~~\nHết.",
    # span mã một dòng
    "Thẻ đóng là `</think>`\nvà thẻ mở là `<think>`.",
    # nháy kép / đơn
    'Chuỗi "</think>"\nlà thẻ đóng.',
    "Chuỗi '</think>'\nlà thẻ đóng.",
    # văn xuôi, chữ liền sau thẻ
    "Model Qwen dùng thẻ </think> để đóng khối suy nghĩ.",
    "Nó viết <think> rồi </think> quanh phần nghĩ.",
    # HTML/XML thoát
    "&lt;/think&gt;\nkhông phải thẻ.",
    # `<think>` ở giữa câu
    "Bạn có thể gõ <think>\nở đầu dòng không?",
    # không có thẻ
    "Hà Nội",
    "",
])
def test_doi_chung_van_ban_hop_le_khong_bi_sua(van_ban):
    assert tach_the_lot(van_ban, "r") == (van_ban, "r")


def test_doi_chung_khoi_ma_chua_dong_den_het_van_ban():
    """Model bị cắt `max_tokens` giữa khối mã: rào không đóng ⇒ vẫn là mã tới hết."""
    van_ban = "Đây:\n```python\ns = '''\n</think>\n'''"
    assert tach_the_lot(van_ban, "") == (van_ban, "")


def test_ma_truoc_the_that_van_tach_the_that():
    """Thẻ trong mã được giữ, thẻ MÁY ngoài mã phía sau vẫn được xử."""
    goc = "nghĩ `</think>` dở\n</think>\n\nĐáp án"
    assert tach_the_lot(goc, "") == ("Đáp án", "nghĩ `</think>` dở")


# ── 3. Lắp vào MỘT chỗ bóc: mọi cửa đồng bộ cùng sạch ─────────────────────────

def _cong(content, reasoning=""):
    msg = {"content": content}
    if reasoning:
        msg["reasoning_content"] = reasoning

    def goi(method, path, *, json=None, timeout=None):
        return 200, {"model": "qwen35-api",
                     "choices": [{"message": msg, "finish_reason": "stop"}],
                     "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
    return CongVlm(goi=goi)


def test_cong_vlm_boc_da_tach_the_lot():
    kq = _cong("Hà Nội\n</think>\n\nHà Nội", "nghĩ").chat(
        model="qwen35-api", messages=[{"role": "user", "content": "?"}])
    assert kq.noi_dung == "Hà Nội"
    assert kq.suy_nghi == "nghĩ\nHà Nội"


def test_cong_vlm_boc_khong_dung_noi_dung_sach():
    kq = _cong("Dùng `</think>`\nđể đóng.", "nghĩ").chat(
        model="qwen35-api", messages=[{"role": "user", "content": "?"}])
    assert kq.noi_dung == "Dùng `</think>`\nđể đóng."
    assert kq.suy_nghi == "nghĩ"


# ── 4. `/messages` không stream: khối `thinking` không còn bị vứt ─────────────

class _Kq:
    """Hình `apps.ltt_llm.features.KetQua` (token phẳng) — như test_285."""

    def __init__(self, noi="Hà Nội", suy_nghi="", finish="stop", tool_calls=()):
        self.noi_dung = noi
        self.suy_nghi = suy_nghi
        self.finish_reason = finish
        self.tool_calls = tool_calls
        self.token_vao, self.token_ra = 11, 7
        self.token_vao_cache = 0
        self.do_duoc = True


@pytest.fixture()
def st():
    return importlib.import_module("server.api.streaming")


def test_mot_cuc_co_khoi_thinking_dung_dau_dung_hinh_anthropic(st):
    d = st._dang_anthropic(_Kq(suy_nghi="thủ đô VN"), "ltt-3.5", "ms-x")
    assert d["content"][0] == {"type": "thinking", "thinking": "thủ đô VN",
                               "signature": ""}
    assert d["content"][1] == {"type": "text", "text": "Hà Nội"}


def test_mot_cuc_khong_suy_nghi_thi_khong_them_khoi(st):
    d = st._dang_anthropic(_Kq(suy_nghi=""), "ltt-3.5", "ms-x")
    assert [k["type"] for k in d["content"]] == ["text"]


def test_mot_cuc_kq_khong_co_truong_suy_nghi_van_chay(st):
    kq = _Kq()
    del kq.suy_nghi
    d = st._dang_anthropic(kq, "ltt-3.5", "ms-x")
    assert [k["type"] for k in d["content"]] == ["text"]


def test_chi_co_suy_nghi_het_tran_khong_them_text_rong(st):
    d = st._dang_anthropic(_Kq(noi="", suy_nghi="nghĩ mãi", finish="length"),
                           "ltt-3.5", "ms-x")
    assert [k["type"] for k in d["content"]] == ["thinking"]
    assert d["stop_reason"] == "max_tokens"


def test_thinking_dung_truoc_tool_use_va_stop_reason_giu_tool_use(st):
    goi = ({"id": "c1", "function": {"name": "doc", "arguments": "{}"}},)
    d = st._dang_anthropic(_Kq(noi="", suy_nghi="cần đọc tệp", finish="tool_calls",
                               tool_calls=goi), "ltt-3.5", "ms-x")
    assert [k["type"] for k in d["content"]] == ["thinking", "tool_use"]
    assert d["stop_reason"] == "tool_use"


def test_khoi_thinking_gui_lai_o_luot_sau_khong_lot_vao_prompt():
    """Claude Code gửi lại khối `thinking` (kèm `signature` rỗng) trong lịch sử —
    đường không stream chỉ lấy `text`, nên không có gì phải kiểm chữ ký."""
    from server.api.tool_dich import sang_openai_messages
    ra = sang_openai_messages([
        {"role": "user", "content": "?"},
        {"role": "assistant", "content": [
            {"type": "thinking", "thinking": "bí mật", "signature": ""},
            {"type": "text", "text": "Hà Nội"}]},
        {"role": "user", "content": "cảm ơn"}])
    assert ra[1] == {"role": "assistant", "content": "Hà Nội"}


# ── 5. Mã lượt xuống máy B ở cửa MỘT CỤC (`X-LTT-Request-Id`) ─────────────────
#
# T4 P1 (`10c01059`, test_1511) phát hiện: `_mot_cuc` gọi `executor.run` KHÔNG có
# `ma_luot` ⇒ `/messages` và `/responses` không stream không gửi `X-LTT-Request-Id`
# ⇒ sổ lượt B không nối được sổ A, và huỷ-khi-khách-đi chỉ đóng socket (L-06).
# Ba mắt xích, mỗi mắt một phép: cửa → `features.chay` (dưới đây), `executor.run`
# → `features.chay` (test_1241), `dieu_phoi._goi_openai` → header (dưới đây).

from tests import test_272_cua_streaming as _t272  # noqa: E402

MODEL, MSG, RSP, _account, _h = (_t272.MODEL, _t272.MSG, _t272.RSP,
                                 _t272._account, _t272._h)
#: Giàn CSDL + app của test_272 (cùng khuôn), dùng lại thay vì chép.
api = _t272.api


def _bat_ma_luot(monkeypatch) -> list:
    from apps.ltt_llm import features
    thay: list = []

    def gia(db, params, *, timeout_s=300.0, ma_luot="", **_):
        thay.append(ma_luot)
        return features.KetQua(
            noi_dung="Hà Nội", suy_nghi="", tool_calls=(), finish_reason="stop",
            model=params["model"], token_vao=10, token_ra=5, token_vao_cache=0,
            do_duoc=True)

    monkeypatch.setattr(features, "chay", gia)
    return thay


def _job_id_credit(user_id: str) -> set:
    from platform_core.db import get_session
    from platform_core.models import CreditEntry
    gen = get_session()
    db = next(gen)
    try:
        return {e.job_id for e in db.query(CreditEntry).filter_by(user_id=user_id)}
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@pytest.mark.parametrize("duong,than", [
    (MSG, {"messages": [{"role": "user", "content": "thủ đô?"}]}),
    (RSP, {"input": "thủ đô?"}),
])
def test_mot_cuc_truyen_ma_luot_xuong_may_B(api, monkeypatch, duong, than):
    thay = _bat_ma_luot(monkeypatch)
    user_id, token = _account()
    r = api.post(duong, json={"model": MODEL, "max_tokens": 1500, **than},
                 headers=_h(token))
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/json"), (
        "khong phai nhanh mot-cuc -> phep kiem dang do nham duong")
    assert len(thay) == 1 and thay[0], (
        "cua mot cuc khong truyen ma luot => may B khong nhan X-LTT-Request-Id")
    # Cùng MỘT khoá với sổ tiền: mã gửi B = `credit_entries.job_id` của lượt.
    assert thay[0] in _job_id_credit(user_id)


def _goi_openai_ghi_header(monkeypatch, ma_luot: str) -> dict:
    import httpx

    from platform_core.llm import dieu_phoi
    thay: dict = {}

    class _Tra:
        status_code = 200

        @staticmethod
        def json():
            return {"model": "qwen35-api",
                    "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1}}

    def gia(self, method, url, *, json=None, headers=None, timeout=None):
        thay.update(headers or {})
        return _Tra()

    monkeypatch.setattr(httpx.Client, "request", gia)
    dieu_phoi._goi_openai("http://b.invalid", "k", {
        "model": "qwen35-api", "messages": [{"role": "user", "content": "?"}]},
        5.0, ma_luot=ma_luot)
    return thay


def test_goi_openai_co_ma_luot_thi_gui_header(monkeypatch):
    assert _goi_openai_ghi_header(monkeypatch, "ms-abc")["X-LTT-Request-Id"] == "ms-abc"


def test_doi_chung_goi_openai_khong_ma_luot_thi_KHONG_co_header(monkeypatch):
    """Đối chứng: phép trên đỏ được — thiếu mã thì header vắng, đúng ca trước T1b."""
    assert "X-LTT-Request-Id" not in _goi_openai_ghi_header(monkeypatch, "")
