# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.
"""ASV final (lan ky-thuat) — CHO NOI: giai doan QC that su do T13/T17/T18.

🔑 Cac bai o `test_2010`/`test_2012` goi thang `qc.kiem` voi tham so tuong minh;
   chung khong chung minh `giai_doan_qc` TRUYEN do vao. Bai nay chay het chuoi
   (preset cat + preset giu hinh) roi doc bao cao da luu: T18 phai la mot con so
   VMAF that o preset cat — `khong_kha_dung` o day la mot phep do chet lang le.
"""
from __future__ import annotations

import json

from apps.auto_scan_video import (che_do_render as cdr, features,
                                  giai_doan_qc, pipeline, qc)
from platform_core.storage import get_storage
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401
from tests.test_402_asv_mach_doc_gia import (_chay_het_hang_doi, _tao_run,  # noqa: F401
                                             asr_gia, db, dich_gia, giong_gia,
                                             kho_tam)
from tests.test_440_asv_v4_long_tieng import _nhieu_canh, _run_cat


def _bao_cao(phien, run) -> dict:
    gd = features.giai_doan_theo_ten(phien, run.id, pipeline.QC)
    assert gd is not None and gd.status == "succeeded", (
        "QC: %s %s" % (getattr(gd, "status", None), getattr(gd, "error", "")))
    khoa = next(k for k in (gd.outputs or {}).get("khoa_asset") or []
                if k.endswith(".json"))
    with get_storage().open(khoa) as f:
        return json.loads(f.read().decode("utf-8"))


def _muc(bc, ma):
    return next(m for m in bc["muc"] if m["ma"] == ma)


def test_preset_CAT_do_that_VMAF_den_dong_va_giai_ma(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia):
    # 🔴 27/09: chu du an chot TAT T18 MAC DINH (`giai_doan_qc.BIEN_T18` —
    #    5d568ffe) vi phep so sanh cu lech truc, cho VMAF mot con so khong
    #    dang tin. Bai nay TON TAI DE CHUNG MINH T18 do duoc mot con so VMAF
    #    THAT o preset cat (xem docstring dau tep) — nen no phai TU BAT, chu
    #    ⛔ khong duoc thua ke mac dinh san xuat (mac dinh do la mot quyet dinh
    #    ve CHI PHI/do tin cay production, khong phai ve kha nang do duoc).
    monkeypatch.setenv(giai_doan_qc.BIEN_T18, "1")
    _nhieu_canh(monkeypatch)
    run = _run_cat(db, kho_tam, tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()
    bc = _bao_cao(db, run)
    assert bc["che_do_render"] == cdr.CAT_MA_HOA_LAI
    assert bc["phien_ban"] == qc.PHIEN_BAN_QC
    t18 = _muc(bc, "T18")
    assert t18["trang_thai"] == qc.DAT, t18
    assert t18["mo_hinh"] == qc.MO_HINH_VMAF and t18["so_khung"] > 0
    assert _muc(bc, "T17")["trang_thai"] == qc.DAT
    assert _muc(bc, "T13")["trang_thai"] == qc.DAT


def test_preset_GIU_HINH_T18_khong_ap_dung_T13_T17_van_do(
        tmp_path, db, kho_tam, asr_gia, dich_gia, giong_gia):
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()
    bc = _bao_cao(db, run)
    assert _muc(bc, "T18")["trang_thai"] == qc.KHONG_AP_DUNG
    assert _muc(bc, "T17")["trang_thai"] == qc.DAT
    assert _muc(bc, "T13")["trang_thai"] == qc.DAT
