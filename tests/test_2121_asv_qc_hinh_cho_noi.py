# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.
"""M-02 CHO NOI — `giai_doan_qc_ai` THUC SU hoi VLM ve tung cho noi cua BAN RA.

🔑 `test_2120` goi thang `qc_ai.cac_cho_noi` / `qc_ai.doc_hinh` voi tham so
   tuong minh; no khong chung minh rang GIAI DOAN truyen chung vao. Va do dung
   la hinh dang cua M-02: ba manh (`loi_nhac_hinh`, `doc_hinh`, `tu_qc_hinh`)
   deu co test xanh tu pha 19, deu **khong co nguoi goi**, va bao cao pha 19 goi
   dung ten no — *"The repair loop is planned, not yet driven."*

⇒ Bai nay chay HET CHUOI voi `LTT_ASV_QC_AI=1` roi doc bao cao da luu. Mot
  `so_cho_noi: 0` hay mot `khong_kha_dung` o preset CAT la mot phep do chet
  lang le, va no phai lam bai nay DO.
"""
from __future__ import annotations

import json

import pytest

from apps.auto_scan_video import features, giai_doan_qc_ai as gdqa, pipeline
from platform_core.storage import get_storage
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401
from tests.test_402_asv_mach_doc_gia import (_chay_het_hang_doi, _tao_run,  # noqa: F401
                                             asr_gia, db, dich_gia, giong_gia,
                                             kho_tam)
from tests.test_440_asv_v4_long_tieng import _cat_canh_le, _nhieu_canh, _run_cat


@pytest.fixture()
def bat_qc_ai(monkeypatch):
    monkeypatch.setenv(gdqa.BIEN_BAT, "1")


def _bao_cao(phien, run) -> dict:
    gd = features.giai_doan_theo_ten(phien, run.id, pipeline.QC_AI)
    assert gd is not None and gd.status == "succeeded", (
        "qc_ai: %s %s" % (getattr(gd, "status", None), getattr(gd, "error", "")))
    khoa = next(k for k in (gd.outputs or {}).get("khoa_asset") or []
                if k.endswith(".json"))
    with get_storage().open(khoa) as f:
        return json.loads(f.read().decode("utf-8"))


def test_preset_CAT_hoi_VLM_ve_TUNG_cho_noi_cua_ban_ra(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia,
        bat_qc_ai):
    """🔴 **Bai nay la cai M-02 thieu.** Mot `so_cho_noi: 0` o preset CAT nghia
    la lop QC hinh dang chay ma khong nhin gi — dung trang thai truoc 23/09,
    chi khac la nay no co ten."""
    _nhieu_canh(monkeypatch)
    _cat_canh_le(monkeypatch)
    run = _run_cat(db, kho_tam, tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()

    bc = _bao_cao(db, run)
    tt = bc["hinh_tom_tat"]
    assert "khong_kha_dung" not in tt, tt
    assert tt["so_cho_noi"] > 0, "preset CAT ma khong co cho noi nao de soat"
    # ⭐ Bat bien: moi cho noi hoac co phan quyet, hoac co mot dong ly do.
    assert tt["du_phu"] is True, tt
    assert tt["so_co_phan_quyet"] == tt["so_cho_noi"], tt

    # Moi phan quyet phai mang DU thu de doi chieu lai: moc tren ban ra, canh bi
    # bo (don vi sua), va so khung DA THUC SU gui di.
    assert len(bc["hinh"]) == tt["so_cho_noi"]
    for pq in bc["hinh"]:
        assert pq["so_khung"] >= 1, pq
        assert pq["moc_giay"] >= 0.0
        assert pq["ma_cat"], "cho noi khong doi nguoc ra canh nao — khong sua duoc"
        assert pq["ma_canh"] in pq["ma_cat"]
        assert 0.0 <= pq["do_tin"] <= 1.0


def test_preset_GIU_HINH_KHONG_hoi_cau_nao_va_NOI_RO_vi_sao(
        tmp_path, db, kho_tam, asr_gia, dich_gia, giong_gia, bat_qc_ai):
    """⭐ Khong canh nao bi cat ⇒ khong cho noi nao ⇒ khong mot dong token.

    ⛔ Nhung bao cao phai NOI RA dieu do. Mot `so_cho_noi: 0` khong kem ly do
       doc giong het mot lan chay da soat va khong thay gi.
    """
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()

    tt = _bao_cao(db, run)["hinh_tom_tat"]
    assert tt["so_cho_noi"] == 0
    assert tt["ly_do"], "so_cho_noi = 0 ma khong noi vi sao"


def test_phan_quyet_hinh_di_toi_stage_outputs_cho_vong_sua(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia,
        bat_qc_ai):
    """🔑 `jobs._qc_hinh` doc `stage.outputs`, KHONG mo kho — `_advance` chay o
    moi luot cua moi lan chay. Khoa phai co mat ke ca khi rong."""
    _nhieu_canh(monkeypatch)
    _cat_canh_le(monkeypatch)
    run = _run_cat(db, kho_tam, tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.QC_AI)
    o = gd.outputs or {}
    assert "qc_hinh_khong_dat" in o
    assert o["qc_hinh_la_tu_van"] is True
    assert o["qc_hinh_so_cho_noi"] > 0

    from apps.auto_scan_video.jobs import _qc_hinh
    theo_ten = {s.stage: s for s in features.cac_giai_doan(db, run)}
    assert _qc_hinh(theo_ten) == o["qc_hinh_khong_dat"]


def test_cho_noi_HONG_van_ve_run_DONE_chu_khong_giet_lan_chay(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia,
        bat_qc_ai):
    """⛔ Mot lop QC CHU QUAN khong duoc giet mot lan chay. `qc` (tat dinh) moi
    la cong phat hanh; neu `_soat_hinh` nem thi mot model dong bong lam hong
    mot ban ra da qua het muoi tam dung sai."""
    from apps.auto_scan_video import ai

    _nhieu_canh(monkeypatch)
    _cat_canh_le(monkeypatch)

    goc = ai.goi_tinh_tien

    def hong(db_, run_, thao_tac, messages, **kw):
        if thao_tac.ma == ai.QC_HINH.ma:
            raise ai.AiError("gia lap: may B tu choi")
        return goc(db_, run_, thao_tac, messages, **kw)

    monkeypatch.setattr(ai, "goi_tinh_tien", hong)
    monkeypatch.setattr(gdqa.ai, "goi_tinh_tien", hong, raising=False)

    run = _run_cat(db, kho_tam, tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()

    tt = _bao_cao(db, run)["hinh_tom_tat"]
    assert tt["so_co_phan_quyet"] == 0
    assert tt["so_hong"] == tt["so_cho_noi"] > 0
    # ⭐ Va bat bien do phu VAN dung: khong cho noi nao bien mat khong dau vet.
    assert tt["du_phu"] is True
    assert features.giai_doan_theo_ten(db, run.id, pipeline.QC_AI).status \
        == "succeeded"
