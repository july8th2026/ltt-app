"""ASV — TRANSCHIBE that (hang doi, kho, CSDL, lineage) di DUY NHAT duong ASR.

⛔ **Khong con dinh tuyen** (Task 21, 26/09): `ocr`/`embedded`/`auto` da bo, xem
`apps/auto_scan_video/nguon_loi.py` dau tep va `B1_PLAN_DUONG_ONG_GD1.md` §11.

## Tep nay tung do gi, va cai gi con lai

Ban cu (lan `ocr`, 22/09) chay mot runner OCR GIA qua `nguon_loi.doc_hardsub` de
chung minh ba dieu: (a) `auto` co hardsub thi ban ghi tu OCR va ⛔ khong goi ASR;
(b) EP `ocr` ma khong co hardsub thi giai doan HONG voi cau cho khach; (c) doi
`nguon_loi` thi chep loi tinh lai. Ca ba **mat doi tuong**.

⭐ Hai bai con lai doi HUONG khang dinh chu khong bien: truoc kia chung noi
   *"duong nay chon dung"*, nay chung noi *"⛔ khong con duong nao de chon"*.
"""
from __future__ import annotations

import json

from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401
from tests import test_478_asv_v6_cache_chung as _t478

db, kho, asr_gia, dem_engine = _t478.db, _t478.kho, _t478.asr_gia, _t478.dem_engine
_nguon, _run, _chay, _gd = _t478._nguon, _t478._run, _t478._chay, _t478._gd


def _ban_ghi(kho, db, run):
    khoa = _gd(db, run, "transcribe").outputs["khoa_asset"][0]
    with kho.open(khoa) as f:
        return json.loads(f.read().decode("utf-8"))


def _ba(db, run):
    for t in _t478.BA:
        _chay(db, run, t)


def test_TRANSCRIBE_luon_di_duong_ASR_va_ban_ghi_ghi_nguon_asr(db, kho, tmp_path,
                                                               asr_gia):
    """⭐ Ban cu ten `test_auto_khong_hardsub_thi_ASR_...` — no mo ta mot **ca**
       trong ba ca. Nay do la ca DUY NHAT, nen ten phai noi the."""
    r = _run(db, _nguon(kho, tmp_path))
    _ba(db, r)
    ban = _ban_ghi(kho, db, r)
    assert ban["nguon_loi"] == "asr"
    assert all("do_tin" not in d for d in ban["doan"]), "ASR khong co do tin — khong bia"


def test_ban_ghi_dinh_tuyen_KHONG_con_ly_do_nao_vi_khong_con_gi_de_chon(db, kho,
                                                                        tmp_path,
                                                                        asr_gia):
    """🔑 `dinh_tuyen.ly_do` tung ghi VI SAO `auto` lui sang buoc sau
    (`khong_co_phu_de_nhung`, `khong_co_hardsub`, `ocr_chi_do_cho_zh`, ...).

    ⛔ Voi mot duong duy nhat thi khong con buoc nao de lui, nen danh sach ly do
       phai RONG. ⭐ Truong `ly_do` thi GIU: no la ban ghi provenance ma cac lan
       chay 22-26/09 da luu, va `quan_sat`/`test_2101` doc no.
    """
    r = _run(db, _nguon(kho, tmp_path))
    _ba(db, r)
    dt = _gd(db, r, "transcribe").outputs["dinh_tuyen"]
    assert dt["che_do"] == "asr" and dt["nguon_loi"] == "asr"
    assert dt.get("ly_do") in (None, []), dt
    # `cat_lai` van co: buoc cat lai theo cau nay KHONG con bi rao cho rieng
    # duong ASR (no la duong duy nhat) — xem `giai_doan_chep_loi.chay`.
    assert "cat_lai" in dt, dt


def test_khoa_chung_KHONG_con_mang_nguon_loi_hay_checksum_VIDEO(db, kho, tmp_path,
                                                                asr_gia):
    """⭐ Ban cu ten `test_khoa_chung_mang_che_do_nguon_loi_va_video` va chung
    minh dieu NGUOC lai. No doi huong vi mot su that ve co che da doi:

    🔴 `transcribe` nay ⛔ **khong mo video mot lan nao** — no chi doc ban tieng
       16 kHz. Nen checksum HINH khong con la mot dau vao cua no, va giu lai se
       lam hai lan chay cung am thanh / khac hinh ⛔ KHONG chia se duoc mot ket
       qua giong het nhau (cai gia la mot luot whisper large-v3 tren GPU).
    """
    from apps.auto_scan_video import cache_chung, pipeline

    r = _run(db, _nguon(kho, tmp_path))
    for t in _t478.BA[:2]:
        _chay(db, r, t)
    dv = cache_chung.dau_vao_noi_dung(db, r, pipeline.TRANSCRIBE)
    assert "nguon_loi" not in dv and "dinh_tuyen" not in dv and "video" not in dv, dv
    assert set(dv) == {"tieng_asr", "model", "ngon_ngu_nguon", "ngon_ngu_dich"}, dv


def test_ho_so_cu_mang_nguon_loi_ocr_VAN_chay_het_ba_giai_doan(db, kho, tmp_path,
                                                               asr_gia):
    """🔑 Bat bien 2 cua Task 21, do **tren duong THAT** chu khong tren mot ham.

    ⚠️ `test_2041` goi `chuan_che_do` truc tiep — no khong tra loi duoc cau
       *"mot lan chay cua khach voi ho so cu co chay duoc khong"*. Day la cho tra
       loi cau do: `features.tao_run` nhan settings THO (⛔ khong qua cua
       `dich_vu_tao`), dung nhu mot hang CSDL cu.
    """
    r = _run(db, _nguon(kho, tmp_path), nguon_loi="ocr")
    _ba(db, r)
    gd = _gd(db, r, "transcribe")
    assert gd.status == "succeeded", gd.outputs
    assert _ban_ghi(kho, db, r)["nguon_loi"] == "asr"
