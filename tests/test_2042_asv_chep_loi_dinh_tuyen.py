"""ASV final — lan ocr: TRANSCRIBE that (hang doi, kho, CSDL, lineage) di qua
dinh tuyen nguon loi; cache chung mang dau vao dinh tuyen.

Chi runner OCR la gia (cung hinh dang `ocr_khung.py`); moi thu khac that.
"""
from __future__ import annotations

import json

import pytest

from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401
from tests import test_478_asv_v6_cache_chung as _t478
from apps.auto_scan_video import nguon_loi as nl

db, kho, asr_gia, dem_engine = _t478.db, _t478.kho, _t478.asr_gia, _t478.dem_engine
_nguon, _run, _chay, _gd = _t478._nguon, _t478._run, _t478._chay, _t478._gd

#: Ban THAT, lay truoc khi fixture autouse cua `rao_chan_nang` thay no.
_DOC_HARDSUB_THAT = nl.doc_hardsub


def _runner_gia(*a, **kw):
    dv = a[1]
    if not dv.get("cat"):
        khung = [{"t": float(i), "dong": [
            {"hop": [100, 120, 220, 150], "chu": f"第{i}句", "diem": 0.99}]} for i in range(10)]
    else:
        chu = ["即使遇到暴风雨"] * 4 + ["圆拱形状内部的空间"] * 4
        khung = [{"t": i / 5, "dong": [{"hop": [100, 120, 220, 150], "chu": c, "diem": 0.96}]}
                 for i, c in enumerate(chu)]
    return {"rong": 320, "cao": 180, "khung": khung, "engine": "rapidocr/gia",
            "ms_moi_khung": 1.0}


@pytest.fixture()
def co_hardsub(monkeypatch):
    monkeypatch.setattr(nl, "doc_hardsub",
                        lambda v, **kw: _DOC_HARDSUB_THAT(v, **{**kw, "chay": _runner_gia}))


def _ban_ghi(kho, db, run):
    khoa = _gd(db, run, "transcribe").outputs["khoa_asset"][0]
    with kho.open(khoa) as f:
        return json.loads(f.read().decode("utf-8"))


def _ba(db, run):
    for t in _t478.BA:
        _chay(db, run, t)


def test_auto_co_hardsub_thi_ban_ghi_tu_OCR_va_KHONG_goi_ASR(
        db, kho, tmp_path, asr_gia, co_hardsub, monkeypatch):
    from apps.auto_scan_video import giai_doan_chep_loi

    goi_asr = []
    monkeypatch.setattr(giai_doan_chep_loi, "chep_loi",
                        lambda *a, **kw: goi_asr.append(1) or asr_gia())
    r = _run(db, _nguon(kho, tmp_path))
    _ba(db, r)
    gd = _gd(db, r, "transcribe")
    assert gd.status == "succeeded", gd.outputs
    assert goi_asr == []
    ban = _ban_ghi(kho, db, r)
    assert ban["nguon_loi"] == "ocr" and ban["ngon_ngu"] == "zh"
    assert [d["chu"] for d in ban["doan"]] == ["即使遇到暴风雨", "圆拱形状内部的空间"]
    assert all(d["do_tin"] == pytest.approx(0.96) for d in ban["doan"])
    assert gd.outputs["dinh_tuyen"] == {"che_do": "auto", "nguon_loi": "ocr", "ly_do": [
        "khong_co_phu_de_nhung"]}


def test_auto_khong_hardsub_thi_ASR_va_ban_ghi_ghi_nguon_asr(db, kho, tmp_path, asr_gia):
    r = _run(db, _nguon(kho, tmp_path))
    _ba(db, r)
    ban = _ban_ghi(kho, db, r)
    assert ban["nguon_loi"] == "asr"
    assert "khong_co_hardsub" in ban["dinh_tuyen"]["ly_do"]
    assert all("do_tin" not in d for d in ban["doan"]), "ASR khong co do tin — khong bia"


def test_EP_ocr_ma_khong_co_hardsub_thi_giai_doan_HONG_voi_loi_cho_khach(
        db, kho, tmp_path, asr_gia):
    r = _run(db, _nguon(kho, tmp_path), nguon_loi="ocr")
    for t in _t478.BA[:2]:
        _chay(db, r, t)
    with pytest.raises(Exception) as loi:
        _chay(db, r, "transcribe")
    assert "phụ đề cứng" in str(loi.value), repr(loi.value)
    db.expire_all()
    assert _gd(db, r, "transcribe").status != "succeeded"


def test_khoa_chung_mang_che_do_nguon_loi_va_video(db, kho, tmp_path, asr_gia):
    from apps.auto_scan_video import cache_chung, pipeline

    k = _nguon(kho, tmp_path)
    r_auto, r_asr = _run(db, k), _run(db, k, nguon_loi="asr")
    for r in (r_auto, r_asr):
        for t in _t478.BA[:2]:
            _chay(db, r, t)
    dv_auto = cache_chung.dau_vao_noi_dung(db, r_auto, pipeline.TRANSCRIBE)
    dv_asr = cache_chung.dau_vao_noi_dung(db, r_asr, pipeline.TRANSCRIBE)
    assert dv_auto["nguon_loi"] == "auto" and dv_auto["video"]
    assert dv_asr["nguon_loi"] == "asr" and "video" not in dv_asr
    assert (cache_chung.khoa(db, r_auto, pipeline.TRANSCRIBE, engine="e")
            != cache_chung.khoa(db, r_asr, pipeline.TRANSCRIBE, engine="e"))


def test_doi_nguon_loi_thi_chep_loi_TINH_LAI(db, kho, tmp_path, asr_gia, dem_engine):
    r1, r2 = _t478._hai_lan_chay(db, kho, tmp_path, nguon_loi="asr")
    for t in _t478.BA:
        _chay(db, r2, t)
    assert dem_engine == {"audio_prepare": 1, "transcribe": 2}
