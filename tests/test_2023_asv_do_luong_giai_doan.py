"""ASV final — giai doan `qc_do_luong` noi vao chuoi + vong sua DOC SAI.

Chot:
  * vi tri + dinh tuyen: sau `qc`, truoc `qc_ai`, app `asv_gpu` (nang luc gpu),
    job type/VRAM/tran thoi gian khai o manifest;
  * van tay engine mang phien ban MOI bo do + model ASR san pham;
  * DOC SAI (WER vuot nguong) -> dat lai DUNG doan do o `voice_synthesis`, va
    doan do duoc DOC LAI THAT (luot doc moi, khong tra tep cu tu cache) — cac
    doan khac dung lai nguyen;
  * cong thuc Dice tu che da XOA.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import pipeline, sua_chua
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401
from tests.test_402_asv_mach_doc_gia import (  # noqa: F401 - fixture
    _chay_het_hang_doi, _tao_run, asr_gia, db, dich_gia, giong_gia, kho_tam)


def test_vi_tri_va_dinh_tuyen():
    ten = [g.ten for g in pipeline.CHUOI]
    i = ten.index(pipeline.QC_DO_LUONG)
    assert ten[i - 1] == pipeline.QC and ten[i + 1] == pipeline.QC_AI
    g = pipeline.THEO_TEN[pipeline.QC_DO_LUONG]
    assert g.app_slug == "asv_gpu" and g.sau == (pipeline.QC,)
    assert pipeline.THEO_TEN[pipeline.QC_AI].sau == (pipeline.QC_DO_LUONG,)
    from apps.asv_gpu.manifest import MANIFEST
    assert g.job_type in MANIFEST.job_types and "gpu" in MANIFEST.requires
    assert MANIFEST.gpu_vram_mb[g.job_type] > 0
    assert MANIFEST.max_runtime_s[g.job_type] > 0


def test_van_tay_engine_mang_phien_ban_bo_do_va_model_asr(monkeypatch):
    from apps.asv_gpu.do_luong import bo_do
    from apps.auto_scan_video import giai_doan_chep_loi, thi_hanh
    v = thi_hanh.phien_ban_engine(pipeline.QC_DO_LUONG)
    assert bo_do.phien_ban() in v and giai_doan_chep_loi.MODEL_ASR in v
    monkeypatch.setattr(giai_doan_chep_loi, "MODEL_ASR", "khac")
    assert thi_hanh.phien_ban_engine(pipeline.QC_DO_LUONG) != v


def test_DICE_da_xoa():
    from apps.auto_scan_video import qc_ai
    for ten in ("khop_van_ban", "NGUONG_KHOP_DOC"):
        assert not hasattr(sua_chua, ten), ten
    assert not hasattr(qc_ai, "so_khop_doc")


def test_muoi_van_tay_doc_lai_chi_khi_da_bi_sua():
    from apps.auto_scan_video import giai_doan_giong as gg
    goc = gg._van_tay("s1", "xin chao", "g", "p", tu_dien={})
    assert gg._van_tay("s1", "xin chao", "g", "p", tu_dien={}, lan=0) == goc
    l1 = gg._van_tay("s1", "xin chao", "g", "p", tu_dien={}, lan=1)
    assert l1 != goc and len(l1) == len(goc)
    assert gg._van_tay("s1", "xin chao", "g", "p", tu_dien={}, lan=2) not in (goc, l1)
    ke = [{"giai_doan_sua": {"voice_synthesis": ["s1", "s2"]}},
          {"giai_doan_sua": {"content_process": ["s3"], "voice_synthesis": ["s1"]}}]
    assert sua_chua.lan_doc_lai(ke) == {"s1": 2, "s2": 1}


def test_jobs_doc_doan_doc_sai_tu_outputs():
    from types import SimpleNamespace

    from apps.auto_scan_video import jobs
    kd = [{"ma": "s1", "wer": 0.9}]
    theo = {pipeline.QC_DO_LUONG: SimpleNamespace(outputs={"qc_giong_khong_dat": kd})}
    assert jobs._qc_giong(theo) == kd
    assert jobs._qc_giong({}) == []


@pytest.mark.skipif("vi" not in sua_chua.NGUONG_DOC_SAI,
                    reason="nguong tieng Viet chua hieu chinh")
def test_DOC_SAI_doc_lai_DUNG_doan_do_roi_giao(db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia, monkeypatch):  # noqa: F811, E501
    """E2E tren hang doi that: luot do dau bao `ma[0]` doc sai (WER=CER=1) ->
    vong sua dat lai `voice_synthesis` cho RIENG doan do -> may doc goi lai
    DUNG MOT lan cho doan do -> luot do thu hai dat -> run `done`."""
    from apps.asv_gpu.do_luong import bo_do
    from apps.auto_scan_video import features, giong_noi, su_dung
    from apps.auto_scan_video.tables import RUN_DONE

    goi_doc: list[str] = []
    cu = giong_noi.doc_mot_doan
    monkeypatch.setattr(giong_noi, "doc_mot_doan",
                        lambda chu, **kw: (goi_doc.append(chu), cu(chu, **kw))[1])
    luot: list[list[str]] = []

    def do_gia(dv, **kw):
        ma = [d["ma"] for d in dv.doan_tieng]
        luot.append(ma)
        hong = len(luot) == 1
        g = {m: {"doc_ra": "", "wer": 1.0 if (hong and i == 0) else 0.0,
                 "cer": 1.0 if (hong and i == 0) else 0.0, "so_tu": 3}
             for i, m in enumerate(ma)}
        return {"giong": {"trang_thai": bo_do.XONG, "ket_qua": g}}

    monkeypatch.setattr(bo_do, "chay_tat_ca", do_gia)
    run = _tao_run(db)
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg", "gpu", "voice"}, toi_da=400)
    run = features.lay_run(db, run.id, "uA")
    assert run.status == RUN_DONE, run.error
    assert len(luot) == 2, "phai do lai sau vong sua"
    so_doan = len(luot[0])
    # Luot dau doc moi doan mot lan; vong sua doc lai DUNG MOT doan.
    assert len(goi_doc) == so_doan + 1, goi_doc
    dong = [d for d in su_dung.cac_dong(db, run, stage=pipeline.VOICE_SYNTHESIS)
            if d.nang_luc == "tong_hop_tieng"]
    theo_ma: dict = {}
    for d in dong:
        theo_ma.setdefault(d.item_key, set()).add(d.ma_dispatch)
    assert len(theo_ma[luot[0][0]]) == 2, "doan doc sai phai co luot doc MOI"
    assert all(len(v) == 1 for k, v in theo_ma.items() if k != luot[0][0])
