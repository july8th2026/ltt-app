"""Task 13 — gỡ suy diễn lỗi LLM cũ: chỉ mã có cấu trúc quyết định hành động.

Chốt bằng HÀNH VI (fixture đi qua đúng cửa), không bằng grep:

* máy B không còn phát khoá legacy (`legacy`, `ly_do`, `truong`, `tran`, `thay`)
  trong phong bì lỗi, nhưng giữ nguyên HTTP status dây (spec §3);
* máy A: status (413/429/504/400/422) và câu chữ KHÔNG còn quyết định hành động —
  thân không có mã v1 thì fail-closed `upstream_unknown`, kể cả hình dạng legacy;
* thuộc tính boolean tương thích (`ban`/`qua_dai`/`het_gio`) đã gỡ khỏi lỗi luồng;
* cờ `LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS` đã gỡ: renderer có cấu trúc là
  đường duy nhất (tín hiệu tự nén Claude Code/Codex chốt ở `test_1480`).
"""

from __future__ import annotations

import inspect
import json

import pytest

from llm_gateway.error_contract import make_error
from platform_core.llm.cong_vlm import (BanError, CongVlm, CongVlmError,
                                        VuotNganSachError, YeuCauSaiError)
from platform_core.llm.model_failure import decode_gateway_failure
from tests.test_1704_model_failure_decoder import _stream_http_failure

KHOA_LEGACY = {"legacy", "ly_do", "truong", "tran", "thay", "co_the_dung",
               "ma", "ma_thuong_nguon"}

LEGACY_BODIES = (
    {"detail": {"truong": "context", "tran": 100, "thay": 101}},
    {"detail": {"truong": "images", "tran": 4, "thay": 6}},
    {"detail": {"ly_do": "qua dai", "legacy": {"truong": "input_tokens",
                                                "tran": 1, "thay": 2}}},
    {"detail": "prompt is too long: 9 tokens > 1 maximum"},
    {"error": {"message": "context_length_exceeded"}},
)


# ── Máy B ───────────────────────────────────────────────────────────────────

def test_B_vuot_ngan_sach_chi_phat_phong_bi_v1():
    from llm_gateway.ngan_sach import VuotNganSach

    e = VuotNganSach("image_count_exceeded", "Qua nhieu anh", truong="images",
                     tran=4, thay=6)
    detail = e.as_dict(request_id="rid-b")
    assert detail == make_error("image_count_exceeded", request_id="rid-b",
                                field="images", limit=4, actual=6)
    assert not KHOA_LEGACY & set(detail)


def _goi_b(client, **json):
    return client.post("/v1/chat/completions",
                       headers={"X-LTT-Request-Id": "rid-t13"},
                       json={"model": "qwen38-api", "messages": [], **json})


def _cac_loi_b():
    """(tên, HTTP status dây GIỮ NGUYÊN, hàm gọi) cho mọi lỗi đường model của B."""
    from llm_gateway.gioi_han import GioiHan
    from llm_gateway.upstream import MA_DA_HUY, MA_HET_GIO, MA_KHONG_VOI_TOI
    from tests.test_1701_gateway_error_envelope import _anh
    from tests.test_250_llm_gateway import FakeUpstream, _cfg, _client, _tt_ban

    def _anh_qua_so():
        return _goi_b(_client(_cfg(max_images=0))[0], **_anh())

    def _model_la():
        return _goi_b(_client()[0], model="khong-co")

    def _sai_token():
        c, _ = _client(_cfg(token="bi-mat"))
        return c.post("/v1/chat/completions",
                      headers={"Authorization": "Bearer sai"},
                      json={"model": "qwen38-api", "messages": []})

    def _cong_day():
        full = GioiHan(max_dong_thoi=1)
        _px, held = full.cap_suat()
        try:
            return _goi_b(_client(gh=full)[0])
        finally:
            held.tra()

    def _gpu_ban():
        return _goi_b(_client(tt=_tt_ban())[0])

    def _thuong_nguon(ma):
        return lambda: _goi_b(_client(up=FakeUpstream(ma=ma, than=b"x"))[0])

    return (
        ("anh", 413, _anh_qua_so),
        ("model", 404, _model_la),
        ("auth", 401, _sai_token),
        ("cong_day", 429, _cong_day),
        ("gpu_ban", 429, _gpu_ban),
        ("huy", 499, _thuong_nguon(MA_DA_HUY)),
        ("het_gio", 504, _thuong_nguon(MA_HET_GIO)),
        ("khong_voi_toi", 502, _thuong_nguon(MA_KHONG_VOI_TOI)),
        ("thuong_nguon_500", 502, _thuong_nguon(500)),
    )


@pytest.mark.parametrize("ten", [t for t, _s, _f in _cac_loi_b()])
def test_B_moi_loi_duong_model_chi_con_v1_va_giu_status(ten):
    _ten, status, goi = next(x for x in _cac_loi_b() if x[0] == ten)
    r = goi()
    assert r.status_code == status, r.text
    body = r.json()
    assert set(body) == {"detail"}, body
    detail = body["detail"]
    assert detail["schema_version"] == 1
    assert not KHOA_LEGACY & set(detail), detail


# ── Máy A: decoder ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("status", (400, 413, 422, 429, 504))
@pytest.mark.parametrize("payload", LEGACY_BODIES)
def test_A_khong_ma_v1_thi_unknown_bat_ke_status_va_hinh_dang(status, payload):
    failure = decode_gateway_failure(status, {}, json.dumps(payload).encode())
    assert failure.canonical_code == "upstream_unknown"
    assert not failure.is_context_limit
    assert not failure.is_busy
    assert not failure.is_timeout


def test_A_as_detail_khong_con_ten_truong_legacy():
    failure = decode_gateway_failure(
        413, {}, json.dumps({"detail": make_error(
            "image_count_exceeded", request_id="r", field="images", limit=4,
            actual=6)}).encode())
    assert not KHOA_LEGACY & set(failure.as_detail())


# ── Máy A: cửa stream (`luong_vlm.mo`) ──────────────────────────────────────

@pytest.mark.parametrize("status", (413, 429, 504))
def test_A_stream_status_tran_khong_sinh_ngu_nghia(monkeypatch, status):
    error = _stream_http_failure(
        monkeypatch, status=status,
        payload={"detail": {"truong": "context", "tran": 1, "thay": 2}})
    assert error.failure.canonical_code == "upstream_unknown"
    assert not error.failure.is_context_limit
    assert not error.failure.is_busy
    assert not error.failure.is_timeout


def test_A_stream_cau_parser_khong_quyet_dinh_gi(monkeypatch):
    calls: list = []
    error = _stream_http_failure(
        monkeypatch, status=502,
        payload={"error": {"message": "Failed to parse tool call peg-native"}},
        calls=calls)
    assert error.failure.canonical_code == "upstream_unknown"
    assert len(calls) == 1


def test_A_loi_luong_khong_con_boolean_tuong_thich():
    from platform_core.llm import luong_vlm
    from platform_core.runtime_noi_bo import luong as cua_luong

    for cls in (luong_vlm.KhongMoDuocLuong, cua_luong.KhongMoDuoc):
        params = inspect.signature(cls.__init__).parameters
        assert not {"ban", "qua_dai", "het_gio"} & set(params), cls
        for ten in ("ban", "qua_dai", "het_gio", "_ban_legacy",
                    "_qua_dai_legacy", "_het_gio_legacy"):
            assert not hasattr(cls, ten), (cls, ten)
    assert not hasattr(luong_vlm, "_loi_parser_tool_call")


# ── Máy A: cửa đồng bộ (`CongVlm.chat`) ─────────────────────────────────────

@pytest.mark.parametrize("status", (400, 413, 422, 429, 504))
def test_A_dong_bo_status_tran_la_loi_cong_chung(status):
    payload = {"detail": {"truong": "context", "tran": 1, "thay": 2}}
    client = CongVlm(goi=lambda *a, **k: (status, payload, {}))
    with pytest.raises(CongVlmError) as caught:
        client.chat(model="m", messages=[])
    assert type(caught.value) is CongVlmError
    assert not isinstance(caught.value, (YeuCauSaiError, BanError,
                                         VuotNganSachError))
    assert caught.value.failure.canonical_code == "upstream_unknown"


# ── Máy A: bề mặt công khai ─────────────────────────────────────────────────

def test_A_khong_con_co_renderer_legacy():
    from platform_core.public_api.config import (PublicApiConfig,
                                                 load_public_api_config)
    from server.api import su_kien_loi

    assert not hasattr(PublicApiConfig(), "structured_model_errors")
    assert not hasattr(
        load_public_api_config({"LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS": "0"}),
        "structured_model_errors")
    for fn in (su_kien_loi.loi_sse, su_kien_loi.loi_qua_dai,
               su_kien_loi.loi_qua_dai_json):
        assert "structured" not in inspect.signature(fn).parameters, fn
