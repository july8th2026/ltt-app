"""test_1410 — usage của ba giao thức quy về MỘT nghĩa: token_vao = tổng prompt (mới + cache).

Hình dạng lấy từ phép đo 16/09 trên engine b10883 (docs/ltt_llm_dual/serving_v2/02_BASELINE_2026-09-16.md §8b):
  /v1/messages   message_start: input 4, cache_read 8826   (input LOẠI TRỪ cache)
  /v1/responses  completed:     input 8825, cached 8821     (input GỒM cache)
"""
from __future__ import annotations

import json

import pytest

from platform_core.llm import gia_token
from platform_core.llm.dem_token_luong import DemToken

NL = bytes([10])


def _sse(ten, goi):
    return b"event: " + ten.encode() + NL + b"data: " + json.dumps(goi).encode() + NL + NL


def _messages(input_, cache, out):
    return [_sse("message_start", {"type": "message_start", "message": {"usage": {
                "cache_read_input_tokens": cache, "input_tokens": input_, "output_tokens": 0}}}),
            _sse("message_delta", {"type": "message_delta", "usage": {"output_tokens": out}})]


def _responses(input_, cache, out):
    return [_sse("response.completed", {"type": "response.completed", "response": {"usage": {
                "input_tokens": input_, "output_tokens": out, "total_tokens": input_ + out,
                "input_tokens_details": {"cached_tokens": cache}}}})]


@pytest.mark.parametrize("khoi, vao, cache, ra", [
    (_messages(8830, 0, 46), 8830, 0, 46),          # lạnh
    (_messages(4, 8826, 54), 8830, 8826, 54),       # cache toàn phần (đo thật)
    (_messages(5000, 8826, 10), 13826, 8826, 10),   # cache một phần
    (_responses(8825, 0, 64), 8825, 0, 64),
    (_responses(8825, 8821, 64), 8825, 8821, 64),
])
def test_token_vao_la_tong_prompt(khoi, vao, cache, ra):
    d = DemToken()
    for k in khoi:
        d.nhin(k)
    u = d.su_dung()
    assert (u.token_vao, u.token_vao_cache, u.token_ra) == (vao, cache, ra)
    assert u.token_vao_moi == vao - cache


def test_messages_cache_mot_phan_KHONG_tinh_token_moi_bang_0():
    d = DemToken()
    for k in _messages(5000, 8826, 10):
        d.nhin(k)
    cp = gia_token.tinh(d.su_dung(), "ltt-3.8")
    assert cp.vao_moi_mcredit > 0


def test_cache_khong_bao_gio_vuot_tong():
    d = DemToken()
    d.nhin(_sse("x", {"timings": {"cache_n": 999}, "usage": {"prompt_tokens": 10, "completion_tokens": 1}}))
    u = d.su_dung()
    assert u.token_vao_cache <= u.token_vao


def test_messages_cache_hit_van_tinh_token_moi():
    """R-04 tái hiện 18/09: 38 mới + 9.844 cache từng ra 0 credit phần mới."""
    d = DemToken()
    d.nhin(b'data: {"type":"message_start","message":{"usage":{"input_tokens":38,"cache_read_input_tokens":9844,"output_tokens":1}}}\n\n')
    d.nhin(b'data: {"type":"message_delta","usage":{"output_tokens":120}}\n\n')
    su = d.su_dung()
    assert su.token_vao == 38 + 9844
    assert su.token_vao_cache == 9844
    assert su.token_vao - su.token_vao_cache == 38


def test_quyet_toan_khong_tinh_cache_hai_lan():
    """Bên tiêu thụ duy nhất của số tiền (`gia_token.tinh`, gọi từ `thanh_toan`) định giá
    phần mới và phần cache TÁCH RỜI: sau khi `token_vao` gồm cache, 9.844 cache chỉ được
    tính một lần ở giá cache, 38 mới ở giá mới — không ai tính `token_vao` ở giá mới."""
    d = DemToken()
    for k in _messages(38, 9844, 120):
        d.nhin(k)
    su = d.su_dung()
    g = gia_token.bang_cua("ltt-3.8")
    cp = gia_token.tinh(su, "ltt-3.8")
    assert cp.vao_moi_mcredit == gia_token._mcredit(38, g.vao_moi_1m)
    assert cp.vao_cache_mcredit == gia_token._mcredit(9844, g.vao_cache_1m)
    assert cp.vao_moi_mcredit > 0
