"""
test_271_dem_token_luong — đếm token từ luồng SSE đang chảy. (H38, Q107, C5)

🔴 VÌ SAO BỘ TEST NÀY LÀ BỘ QUAN TRỌNG NHẤT CỦA ĐỢT 3. Nó gác một **lỗi tiền**.
   Với streaming, luồng có thể **không bao giờ tới cuối** — khách Ctrl-C, mạng
   đứt — mà GPU thì đã đốt rồi. Đếm sai ở đây nghĩa là thu sai, và thu sai theo
   kiểu không ai phát hiện được cho tới khi khách kêu.

Năm tính chất neo ở đây:

  1. Khối SSE **cắt giữa dòng** vẫn phải đếm đúng — đây là chuyện thường của
     `iter_raw()`, không phải ca hiếm.
  2. Luồng **cắt giữa chừng** vẫn ra đúng số đã sinh tới lúc đó.
  3. **Lấy lớn nhất, không lấy cái cuối** — `message_start` có `output_tokens: 0`.
  4. Cả hai giao thức, một bộ đếm.
  5. **Không sửa một byte nào** của luồng.
"""
from __future__ import annotations

import json

import pytest

from platform_core.llm.dem_token_luong import DemToken, dem_qua

NL = bytes([10])


def _sse(ten: str, goi: dict) -> bytes:
    return (b"event: " + ten.encode() + NL
            + b"data: " + json.dumps(goi).encode() + NL + NL)


# Dung hinh dang THAT, chep tu mot lan bat luong tren may B ngay 23/08.
BAT_DAU = _sse("message_start", {
    "type": "message_start",
    "message": {"id": "chatcmpl-x", "type": "message", "role": "assistant",
                "content": [], "model": "qwen38-api",
                "usage": {"cache_read_input_tokens": 0, "input_tokens": 18,
                          "output_tokens": 0}}})
DELTA = _sse("content_block_delta", {
    "type": "content_block_delta", "index": 0,
    "delta": {"type": "text_delta", "text": "Ha"}})
KET = _sse("message_delta", {
    "type": "message_delta", "delta": {"stop_reason": "end_turn"},
    "usage": {"output_tokens": 105}})


# ── 1. Ca thường ────────────────────────────────────────────────────────────

def test_dem_dung_mot_luot_tron_ven():
    d = DemToken()
    for k in (BAT_DAU, DELTA, KET):
        d.nhin(k)
    u = d.su_dung()
    assert (u.token_vao, u.token_ra, u.dang_tin) == (18, 105, True)


def test_KHONG_SUA_MOT_BYTE_NAO():
    """⛔ Ống nhòm, không phải bộ lọc. Cộng đồng đã mất thời gian vì lỗi ngược
    lại — một harness dùng regex cắt delta ở dấu nháy đã thoát."""
    goc = [BAT_DAU, DELTA, KET]
    d = DemToken()
    assert list(dem_qua(iter(goc), d)) == goc


# ── 2. Khối cắt giữa dòng — chuyện THƯỜNG, không phải ca hiếm ───────────────

def test_khoi_cat_giua_dong_van_dem_dung():
    """🔴 `iter_raw()` trả byte theo nhịp MẠNG, không theo nhịp dòng.

    Phân tích từng khối rời rạc là hỏng ngẫu nhiên theo tải — loại lỗi chỉ hiện
    ra ở production, và hiện ra dưới dạng hoá đơn sai."""
    tat_ca = BAT_DAU + DELTA + KET
    for buoc in (1, 3, 7, 17, 64):
        d = DemToken()
        for i in range(0, len(tat_ca), buoc):
            d.nhin(tat_ca[i:i + buoc])
        u = d.su_dung()
        assert (u.token_vao, u.token_ra) == (18, 105), f"buoc={buoc}"


def test_cat_dung_giua_mot_so():
    """Ca ác nhất: khối vỡ ngay giữa `105`."""
    tat_ca = BAT_DAU + DELTA + KET
    vi_tri = tat_ca.rindex(b"105") + 1
    d = DemToken()
    d.nhin(tat_ca[:vi_tri])
    d.nhin(tat_ca[vi_tri:])
    assert d.su_dung().token_ra == 105


# ── 3. Luồng cắt giữa chừng — chỗ tiền thật sự nằm ─────────────────────────

def test_cat_giua_chung_van_ra_so_da_sinh():
    """GPU đã đốt rồi. Không đếm dọc đường thì chỉ còn hai lựa chọn tồi: thu
    trọn phần đã giữ (lỗi tiền), hoặc cho không (mất tiền)."""
    d = DemToken()
    d.nhin(BAT_DAU)
    d.nhin(_sse("message_delta", {"usage": {"output_tokens": 40}}))
    d.nhin(DELTA)                      # roi khach ngat, khong co message_stop
    u = d.su_dung()
    assert u.dang_tin is True
    assert (u.token_vao, u.token_ra) == (18, 40)


def test_LAY_LON_NHAT_khong_lay_cai_cuoi():
    """🔴 `message_start` mang `output_tokens: 0`.

    Lấy cái cuối chỉ đúng khi luồng chạy tới cuối. Một luồng bị cắt có thể để
    lại cái cuối là số 0 đó, và ta sẽ thu 0 cho một lượt đã sinh vài trăm token."""
    d = DemToken()
    d.nhin(_sse("message_delta", {"usage": {"output_tokens": 105}}))
    d.nhin(BAT_DAU)                    # den SAU, mang output_tokens: 0
    assert d.su_dung().token_ra == 105


def test_vo_TRUOC_message_start_thi_KHONG_DO_DUOC():
    """⛔ Không đo được thì không thu. Cùng luật `quyet_toan_hoac_hoan`."""
    d = DemToken()
    d.nhin(b"event: ping" + NL + NL)
    d.nhin(b": keep-alive" + NL + NL)
    assert d.do_duoc is False
    assert d.su_dung().dang_tin is False


def test_sinh_0_token_KHAC_khong_do_duoc():
    """Hai chuyện khác nhau, và trộn chúng là thu sai một trong hai."""
    d = DemToken()
    d.nhin(BAT_DAU)                    # output_tokens: 0, nhung DA thay usage
    u = d.su_dung()
    assert u.dang_tin is True and u.token_ra == 0


# ── 4. Hai giao thức, một bộ đếm ───────────────────────────────────────────

def test_giao_thuc_responses_cua_codex():
    """OpenAI Responses để `usage` trong `response`, không ở gốc."""
    d = DemToken()
    d.nhin(_sse("response.completed", {
        "type": "response.completed",
        "response": {"id": "resp_x", "status": "completed",
                     "usage": {"input_tokens": 21936, "output_tokens": 312,
                               "input_tokens_details": {"cached_tokens": 20000}}}}))
    u = d.su_dung()
    assert (u.token_vao, u.token_ra, u.token_vao_cache) == (21936, 312, 20000)


def test_dang_openai_chat_prompt_completion_tokens():
    d = DemToken()
    d.nhin(_sse("x", {"usage": {"prompt_tokens": 50, "completion_tokens": 7}}))
    u = d.su_dung()
    assert (u.token_vao, u.token_ra) == (50, 7)


def test_cache_anthropic():
    """Hình dạng THẬT (đo 16/09, b10883): `input_tokens` LOẠI TRỪ cache."""
    d = DemToken()
    d.nhin(_sse("message_start", {"message": {"usage": {
        "input_tokens": 4, "cache_read_input_tokens": 413,
        "output_tokens": 0}}}))
    u = d.su_dung()
    assert (u.token_vao_cache, u.token_vao) == (413, 417)


# ── 5. Rác không được làm đổ bộ đếm ────────────────────────────────────────

@pytest.mark.parametrize("rac", [
    b"data: khong-phai-json" + NL + NL,
    b"data: " + NL + NL,
    b"data: [DONE]" + NL + NL,
    b": keep-alive" + NL + NL,
    b"event: ping" + NL + b"data: {}" + NL + NL,
    b"data: null" + NL + NL,
    b"data: [1,2,3]" + NL + NL,
])
def test_rac_khong_lam_do(rac):
    d = DemToken()
    d.nhin(BAT_DAU)
    d.nhin(rac)
    d.nhin(KET)
    u = d.su_dung()
    assert (u.token_vao, u.token_ra) == (18, 105)


def test_cay_json_sau_khong_lam_treo():
    """Đầu vào đến từ mạng — đệ quy phải có đáy."""
    sau = {"usage": {"output_tokens": 3}}
    for _ in range(200):
        sau = {"x": sau}
    d = DemToken()
    d.nhin(_sse("x", sau))
    d.su_dung()                        # khong treo, khong no la du


def test_luong_no_thi_loi_NOI_LEN_va_so_dem_van_con():
    """Lỗi phải nổi lên, nhưng số đã đếm được tới lúc đó là số dùng để thu tiền."""
    def vo():
        yield BAT_DAU
        yield _sse("message_delta", {"usage": {"output_tokens": 12}})
        raise ConnectionError("thuong nguon dut")

    d = DemToken()
    g = dem_qua(vo(), d)
    next(g); next(g)
    with pytest.raises(ConnectionError):
        next(g)
    assert d.su_dung().token_ra == 12
