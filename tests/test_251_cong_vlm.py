"""
test_251_cong_vlm — client máy A gọi cổng VLM máy B. (H38)

Chạy được **trên máy A, không cần GPU và không cần máy B**: hàm HTTP được tiêm.

Bốn hành vi neo ở đây vì mất chúng là mất tiền hoặc mất dịch vụ:

  1. **429 ⇒ `BanError`, KHÔNG phải `CongVlmError`.** Nếu lẫn, `api_pool` sẽ
     cooldown rồi `disable` key sau 5 lần, và một tối máy B chạy video sẽ tự tắt
     vĩnh viễn model nhà (D-005).
  2. **`usage` thiếu ⇒ `dang_tin=False`.** Không đoán số để tính tiền (luật 3).
  3. **Token cache đếm riêng.** Tính đủ giá cho phần cache là tính tiền khách hai
     lần cho cùng một ngữ cảnh (luật 4).
  4. **Không có đường tự đổi model.** D-010: đổi model sau lưng khách là đánh
     tráo sản phẩm — với API bán ra ngoài thì đó là bán sai hàng.
"""
from __future__ import annotations

import pytest

from platform_core.llm.cong_vlm import (AmbiguousProviderError, BanError,
                                        CongVlm, CongVlmError, ProviderOomError,
                                        SuDung, VuotNganSachError, doc_su_dung)


def _goi_gia(ma=200, than=None, ghi=None):
    """Hàm HTTP giả. `ghi` là list để test soi lời gọi."""
    def goi(method, path, *, json=None, timeout=None):
        if ghi is not None:
            ghi.append((method, path, json))
        return ma, than if than is not None else {}
    return goi


def _than_ok(noi_dung="xin chao", **them):
    d = {
        "model": "qwen38-api",
        "choices": [{"message": {"content": noi_dung}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 40},
    }
    d.update(them)
    return d


# ── 1. Bận là bận, không phải hỏng ───────────────────────────────────────────

def test_429_nem_BanError_chu_khong_phai_CongVlmError():
    c = CongVlm(goi=_goi_gia(429, {"detail": {"chi_tiet": "co 1 tien trinh python"}}))
    with pytest.raises(BanError) as e:
        c.chat(model="qwen38-api", messages=[])
    assert "python" in e.value.ly_do
    # Đây là mấu chốt: `BanError` KHÔNG được là con của `CongVlmError`.
    assert not isinstance(e.value, CongVlmError), \
        "lan hai loai nay se lam api_pool disable key model nha sau 5 lan (D-005)"


def test_dang_ban_khi_khong_lien_lac_duoc_thi_coi_la_ban():
    """Không lạc quan: không biết ⇒ coi là bận."""
    c = CongVlm(goi=_goi_gia(503))
    ban, ly_do = c.dang_ban()
    assert ban is True and ly_do


def test_dang_ban_doc_dung_truong_trong_tai():
    c = CongVlm(goi=_goi_gia(200, {"trong_tai": {"ban": True, "ly_do": "video"}}))
    assert c.dang_ban() == (True, "video")


# ── 2. Vượt ngân sách là loại lỗi RIÊNG ──────────────────────────────────────

def test_413_nem_VuotNganSachError_khong_phai_loi_provider():
    c = CongVlm(goi=_goi_gia(413, {"detail": {"truong": "input_tokens", "tran": 65536}}))
    with pytest.raises(VuotNganSachError) as e:
        c.chat(model="qwen38-api", messages=[])
    assert e.value.chi_tiet["detail"]["truong"] == "input_tokens"
    assert not isinstance(e.value, CongVlmError), \
        "may B khong hong — khong duoc danh dau loi cho key vi mot yeu cau qua to"


def test_404_model_chua_mo_thi_la_CongVlmError():
    c = CongVlm(goi=_goi_gia(404))
    with pytest.raises(CongVlmError):
        c.chat(model="khong-co", messages=[])


def test_mat_ket_noi_trong_post_la_ambiguous_khong_duoc_retry_mu():
    def mat_mang(_method, _path, *, json=None, timeout=None):
        raise TimeoutError("khong biet provider da nhan body hay chua")

    c = CongVlm(goi=mat_mang)
    with pytest.raises(AmbiguousProviderError):
        c.chat(model="qwen38-api", messages=[])


def test_502_bao_oom_la_loi_terminal_co_cau_truc():
    c = CongVlm(goi=_goi_gia(
        502, {"error": {"message": "CUDA out of memory while allocating"}}))
    with pytest.raises(ProviderOomError):
        c.chat(model="qwen38-api", messages=[])


def test_thieu_ten_model_bi_chan_truoc_khi_ra_mang():
    ghi = []
    c = CongVlm(goi=_goi_gia(200, _than_ok(), ghi))
    with pytest.raises(CongVlmError):
        c.chat(model="", messages=[])
    assert ghi == []


# ── 3. Đọc usage — đây là hàm tính tiền ──────────────────────────────────────

def test_thieu_usage_thi_dang_tin_False():
    """⛔ Luật 3: không đoán. 0 token KHÔNG có nghĩa là miễn phí."""
    su = doc_su_dung({"choices": []})
    assert su.dang_tin is False
    assert su.token_vao == 0 and su.token_ra == 0


def test_doc_usage_co_ban():
    su = doc_su_dung(_than_ok())
    assert su.dang_tin is True
    assert (su.token_vao, su.token_ra) == (100, 40)
    assert su.token_vao_cache == 0
    assert su.token_vao_moi == 100


def test_cache_n_cua_llama_cpp_duoc_dem_rieng():
    """⛔ Luật 4: phần cache không prefill lại, không được tính giá đầy đủ."""
    su = doc_su_dung(_than_ok(timings={"cache_n": 80}))
    assert su.token_vao == 100
    assert su.token_vao_cache == 80
    assert su.token_vao_moi == 20, "chi 20 token that su phai prefill"


def test_nhan_ca_kieu_prompt_tokens_details_cua_openai():
    than = _than_ok()
    than["usage"]["prompt_tokens_details"] = {"cached_tokens": 60}
    su = doc_su_dung(than)
    assert su.token_vao_cache == 60


def test_cache_bao_nhieu_hon_prompt_thi_bi_kep_lai():
    """Thượng nguồn báo sai không được biến thành một khoản giảm giá không có thật."""
    su = doc_su_dung(_than_ok(timings={"cache_n": 9999}))
    assert su.token_vao_cache == 100
    assert su.token_vao_moi == 0


def test_usage_khong_phai_dict_thi_khong_dang_tin():
    assert doc_su_dung({"usage": "?"}).dang_tin is False


def test_so_am_tu_thuong_nguon_bi_kep_ve_0():
    su = doc_su_dung({"usage": {"prompt_tokens": -5, "completion_tokens": -1}})
    assert (su.token_vao, su.token_ra) == (0, 0)


# ── 4. Bóc phản hồi ──────────────────────────────────────────────────────────

def test_boc_noi_dung_va_usage():
    c = CongVlm(goi=_goi_gia(200, _than_ok("chao ban", timings={"cache_n": 30})))
    kq = c.chat(model="qwen38-api", messages=[{"role": "user", "content": "hi"}])
    assert kq.noi_dung == "chao ban"
    assert kq.finish_reason == "stop"
    assert kq.su_dung.token_vao_moi == 70


def test_suy_nghi_tach_khoi_noi_dung():
    """`--reasoning-format deepseek` đưa khối <think> ra trường riêng, để token
    suy nghĩ không chen vào giữa một tool call."""
    than = _than_ok("ket qua")
    than["choices"][0]["message"]["reasoning_content"] = "de xem nao..."
    c = CongVlm(goi=_goi_gia(200, than))
    kq = c.chat(model="qwen38-api", messages=[])
    assert kq.noi_dung == "ket qua"
    assert kq.suy_nghi == "de xem nao..."


def test_tool_calls_duoc_boc():
    than = _than_ok("")
    than["choices"][0]["message"]["tool_calls"] = [
        {"id": "c1", "function": {"name": "doc_file", "arguments": '{"p":"a.txt"}'}}]
    than["choices"][0]["finish_reason"] = "tool_calls"
    c = CongVlm(goi=_goi_gia(200, than))
    kq = c.chat(model="qwen38-api", messages=[], tools=[{"type": "function"}])
    assert kq.co_tool_call
    assert kq.tool_calls[0]["function"]["name"] == "doc_file"


def test_khong_co_choices_thi_khong_no():
    c = CongVlm(goi=_goi_gia(200, {"model": "x"}))
    kq = c.chat(model="qwen38-api", messages=[])
    assert kq.noi_dung == "" and kq.su_dung.dang_tin is False


# ── 5. Thân gửi đi ───────────────────────────────────────────────────────────

def test_than_gui_dung_hinh_dang_openai():
    ghi = []
    c = CongVlm(goi=_goi_gia(200, _than_ok(), ghi))
    c.chat(model="qwen38-api", messages=[{"role": "user", "content": "a"}],
           tools=[{"type": "function"}], max_tokens=256, temperature=0.7,
           reasoning_effort="medium")
    method, path, than = ghi[-1]
    assert (method, path) == ("POST", "/v1/chat/completions")
    assert than["model"] == "qwen38-api"
    assert than["max_tokens"] == 256 and than["temperature"] == 0.7
    assert than["reasoning_effort"] == "medium"
    assert than["stream"] is False, "duong stream tinh tien khac — khong tron vao day"


def test_khong_gui_truong_rong():
    ghi = []
    c = CongVlm(goi=_goi_gia(200, _than_ok(), ghi))
    c.chat(model="qwen38-api", messages=[])
    than = ghi[-1][2]
    for khoa in ("tools", "max_tokens", "temperature", "reasoning_effort"):
        assert khoa not in than


def test_khong_co_duong_tu_doi_model():
    """⛔ D-010. `chat()` KHÔNG được nhận tham số fallback: chọn model lui là
    quyết định của tầng trên, và nó phải kèm việc tính tiền theo model lui."""
    import inspect
    tham_so = set(inspect.signature(CongVlm.chat).parameters)
    for cam in ("fallback", "fallback_model", "thu_tu_provider", "provider"):
        assert cam not in tham_so, f"'{cam}' o day la duong danh trao san pham"
