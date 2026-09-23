"""test_1257 — mot loi phai noi duoc khach PHAI LAM GI, va phai dung LOAI.

## 🔴 Hai loi that, do duoc tren production 14/09/2026

**(a) Thong diep khong hanh dong duoc.** Gui 5 anh (tran cua cong la 4):

    400 invalid_request  detail = "yeu cau vuot tran cua cong"

Tieng Viet khong dau, tren mot API cong khai tieng Anh, va **khong noi tran nao,
tran bao nhieu, hay truong nao**. Khach khong the sua yeu cau cua ho tu do.

⭐ Va thong tin AY DA CO SAN suot: `llm_gateway/ngan_sach.py` nem kem
   `{truong: "images", tran: 4, thay: 5}` va cong tra chung trong than 413.
   Tang HTTP cua ta **vut het** roi thay bang mot chuoi cung.

**(b) Phan loai sai LOAI loi — nang hon (a).** Cua stream gop:

    except (VuotNganSachError, CongVlmError):
        raise service_unavailable("The model could not serve this request.")

`VuotNganSachError` la "yeu cau QUA LON" — loi cua khach, sua duoc. Tra no
thanh **503** la bao khach *"may dang ban, thu lai sau"* cho mot viec **thu lai
bao nhieu lan cung hong**. Khach dot thoi gian cua ho va GPU cua ta vao mot
vong lap khong bao gio thanh cong.

## Vi sao phep kiem nay khong goi may B

No goi thang ham dich va soi nhanh `except`. Mot phep kiem E2E that doi 5 anh
that va mot GPU ranh; phep kiem nay chot **bat bien**, nen no chay moi lan gate.
"""

from __future__ import annotations

import inspect
import json

import pytest

from llm_gateway.error_contract import make_error
from platform_core.llm.model_failure import decode_gateway_failure
from server.api import su_kien_loi


# ── (a) Thong tin cong da gui phai di TIEP ra toi khach ──────────────────────
#
# Task 13 (22/09): `tran_bi_vuot` (dich `{truong, tran, thay}`) da go cung
# decoder legacy. Cong may B gui `field`/`limit`/`actual` trong phong bi v1;
# renderer duy nhat dua chung ra `ltt_error` cua moi giao thuc.


def _loi_anh():
    return decode_gateway_failure(413, {}, json.dumps({"detail": make_error(
        "image_count_exceeded", request_id="rid", field="images", limit=4,
        actual=5)}).encode())


@pytest.mark.parametrize("duong", ["/v1/chat/completions", "/v1/messages",
                                   "/v1/responses", "/api/v1/jobs"])
def test_ba_truong_cong_gui_len_di_toi_khach(duong):
    body = json.loads(su_kien_loi.render_model_failure(
        duong, _loi_anh(), phase="before_headers", stream=False).body)
    error = body.get("error") if isinstance(body.get("error"), dict) else body
    ext = error["ltt_error"]
    assert ext["field"] == "images", "khach khong biet TRUONG nao sai"
    assert ext["limit"] == 4, "khach khong biet tran la BAO NHIEU"
    assert ext["actual"] == 5, "khach khong biet ho da gui BAO NHIEU"


def test_hinh_dang_legacy_khong_con_duoc_dich():
    """Than cu `{truong, tran, thay}` khong mang ma v1 ⇒ `upstream_unknown`."""
    failure = decode_gateway_failure(413, {}, b'{"detail": {"truong": "images", '
                                               b'"tran": 4, "thay": 5}}')
    assert failure.canonical_code == "upstream_unknown"
    assert failure.field is None


# ── (b) Dung LOAI loi: qua lon la 4xx, KHONG phai 503 ────────────────────────


def test_cua_STREAM_khong_con_gop_qua_lon_vao_503():
    """🔴 Bat bien chinh. Gop hai loai loi la noi doi voi khach hai lan cung luc."""
    from server.api import streaming

    nguon = inspect.getsource(streaming)
    assert "except (VuotNganSachError, CongVlmError)" not in nguon, (
        "cua stream dang gop `VuotNganSachError` vao cung nhanh voi "
        "`CongVlmError` -> tra 503 'thu lai sau' cho mot yeu cau QUA LON, ma "
        "thu lai bao nhieu lan cung hong"
    )
    assert "except VuotNganSachError" in nguon, (
        "cua stream phai bat rieng `VuotNganSachError` de tra 400 kem field/limit/actual"
    )


@pytest.mark.parametrize("mo_dun", ["server.api.chat", "server.api.streaming"])
def test_CA_HAI_cua_deu_dua_loi_vuot_tran_qua_renderer_duy_nhat(mo_dun):
    """Mot cua dich, mot cua khong = hai khach thay hai thong diep khac nhau."""
    import importlib

    nguon = inspect.getsource(importlib.import_module(mo_dun))
    assert "tran_bi_vuot(" not in nguon
    assert "render_model_failure(" in nguon, (
        f"`{mo_dun}` khong dua loi vuot tran qua renderer co cau truc"
    )


def test_cong_vlm_GIU_chi_tiet_thay_vi_thay_bang_chuoi_cung():
    """Neu `cong_vlm` vut `chi_tiet` thi hai cua o tren khong co gi de dich."""
    from llm_gateway.error_contract import make_error
    from platform_core.llm import cong_vlm

    payload = {
        "error": make_error(
            "image_count_exceeded",
            request_id="rid",
            field="images",
            limit=4,
            actual=5,
        )
    }
    client = cong_vlm.CongVlm(goi=lambda *args, **kwargs: (400, payload, {}))
    with pytest.raises(cong_vlm.VuotNganSachError) as caught:
        client.chat(model="qwen35-api", messages=[])
    assert caught.value.chi_tiet["field"] == "images"
    assert caught.value.chi_tiet["limit"] == 4
    assert caught.value.chi_tiet["actual"] == 5
