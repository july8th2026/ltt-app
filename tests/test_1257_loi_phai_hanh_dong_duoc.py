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

import pytest

from platform_core.public_api.errors import tran_bi_vuot


# ── (a) Thong tin cong da gui phai di TIEP ra toi khach ──────────────────────

def test_dich_du_ba_truong_cong_gui_len():
    """`{truong, tran, thay}` cua cong -> `field`/`limit`/`actual` cong khai."""
    ra = tran_bi_vuot({"ly_do": "Qua nhieu anh.", "truong": "images",
                       "tran": 4, "thay": 5})
    assert ra["field"] == "images", "khach khong biet TRUONG nao sai"
    assert ra["limit"] == 4, "khach khong biet tran la BAO NHIEU"
    assert ra["actual"] == 5, "khach khong biet ho da gui BAO NHIEU"
    # `fields` la ten sổ tay cua nen tang cho danh sach truong (cua job dung no).
    assert ra["fields"] == ["images"]


@pytest.mark.parametrize("vao", [None, "", 0, [], {"khong": "lien quan"}])
def test_khong_co_chi_tiet_thi_tra_RONG_chu_khong_no(vao):
    """Mot loi khong kem chi tiet van phai la mot loi hop le.

    Ben goi dung `**tran_bi_vuot(...)`, nen ham nay ma nem thi mot loi 400
    binh thuong se thanh 500 — bien mot loi cua khach thanh mot loi cua may.
    """
    assert tran_bi_vuot(vao) == {}


def test_gia_tri_vo_nghia_bi_BO_chu_khong_duoc_cong_bo():
    """`tran=0` nghia la 'khong co tran', dung day 0 ra cho khach doc."""
    ra = tran_bi_vuot({"truong": "", "tran": 0, "thay": 0})
    assert ra == {}, f"dang cong bo gia tri vo nghia: {ra!r}"

    ra = tran_bi_vuot({"truong": "images", "tran": "khong phai so", "thay": None})
    assert ra == {"field": "images", "fields": ["images"]}


# ── (b) Dung LOAI loi: qua lon la 4xx, KHONG phai 503 ────────────────────────

def test_cua_STREAM_khong_con_gop_qua_lon_vao_503():
    """🔴 Bat bien chinh. Gop hai loai loi la noi doi voi khach hai lan cung luc."""
    from server.api import streaming

    nguon = inspect.getsource(streaming)
    assert "except (VuotNganSachError, CongVlmError)" not in nguon, (
        "cua stream dang gop `VuotNganSachError` vao cung nhanh voi "
        "`CongVlmError` -> tra 503 'thu lai sau' cho mot yeu cau QUA LON, ma "
        "thu lai bao nhieu lan cung hong")
    assert "except VuotNganSachError" in nguon, (
        "cua stream phai bat rieng `VuotNganSachError` de tra 400 kem "
        "field/limit/actual")


@pytest.mark.parametrize("mo_dun", ["server.api.chat", "server.api.streaming"])
def test_CA_HAI_cua_deu_dich_chi_tiet_tran(mo_dun):
    """Mot cua dich, mot cua khong = hai khach thay hai thong diep khac nhau."""
    import importlib

    nguon = inspect.getsource(importlib.import_module(mo_dun))
    assert "tran_bi_vuot(" in nguon, (
        f"`{mo_dun}` khong dich `{{truong, tran, thay}}` sang ten cong khai — "
        "thong tin cong may B gui len bi vut di")


def test_cong_vlm_GIU_chi_tiet_thay_vi_thay_bang_chuoi_cung():
    """Neu `cong_vlm` vut `chi_tiet` thi hai cua o tren khong co gi de dich."""
    from platform_core.llm import cong_vlm

    nguon = inspect.getsource(cong_vlm)
    i = nguon.find("if ma == 413:")
    assert i > 0, "khong tim thay nhanh 413 trong cong_vlm"
    khoi = nguon[i:i + 1400]
    assert "chi_tiet=" in khoi, (
        "nhanh 413 khong mang `chi_tiet` theo — `{truong, tran, thay}` cua cong "
        "bi bo lai va khach nhan mot cau vo nghia")
