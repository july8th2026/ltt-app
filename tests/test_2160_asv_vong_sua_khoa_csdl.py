# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.
"""M-09 — VONG SUA phai chay tron, khong chet `database is locked`.

🔴 **Nang luc "sua dung cho" (§8 de bai) chua tung chay tron mot lan nao.**
   `LOI_TONG.md` M-09: moi vong sua chay lai `voice_synthesis` deu chet
   `sqlite3.OperationalError: database is locked`. Lan `qc-hinh` phat hien qua
   `test_2121` va ghi lai; khong lan nao sua vi no thuoc tep cua lan khac.

Bai nay dung mot vong sua THAT tu mot phep DO that (WER vuot nguong tieng
Viet), qua chuoi that, hang doi that, worker that — chi may do va may sinh
tieng la gia:

    qc_do_luong (WER cao) -> _sua_chua_neu_can -> doc_sai -> dat lai
    voice_synthesis -> sinh lai doan -> qc/qc_do_luong lai -> run DONE

⭐ Menh de: **`run.status == done`**, so cai dung (khong tinh tien hai lan,
   `VONG_SUA_TOI_DA` duoc ton trong), va khong mot khoa nao bi bo lai.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import features, jobs, pipeline, su_dung, sua_chua
from apps.auto_scan_video.tables import RUN_DONE
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401
from tests.test_402_asv_mach_doc_gia import (_chay_het_hang_doi, _tao_run,  # noqa: F401
                                             asr_gia, db, dich_gia, giong_gia,
                                             kho_tam)


def _do_giong_gia(monkeypatch, *, hong: set[str] | None = None,
                  ghi_lai: list | None = None):
    """Thay BO DO that (ASR + WER/CER, can qc-venv + model) bang mot phep do
    xac dinh. Moi thu khac tren duong — giai doan, so cai, vong sua — la that.

    `hong` = tap ma doan bi cham VUOT nguong `vi` (wer 0,30 / cer 0,23).
    """
    from apps.asv_gpu.do_luong import bo_do

    def chay_tat_ca(dv, **kw):
        ket_qua = {}
        for d in dv.doan_tieng:
            ma = str(d["ma"])
            xau = ma in (hong or set())
            ket_qua[ma] = {"wer": 0.95 if xau else 0.01,
                           "cer": 0.90 if xau else 0.01,
                           "doc_ra": str(d.get("chu") or ""),
                           "tham_chieu_chuan": str(d.get("chu") or "")}
        if ghi_lai is not None:
            ghi_lai.append(sorted(ket_qua))
        return {"giong": {"trang_thai": "xong", "ket_qua": ket_qua}}

    monkeypatch.setattr(bo_do, "chay_tat_ca", chay_tat_ca)


def _ma_doan_dau(db, run) -> str:
    """Ma doan tieng dau tien cua lan chay — doc tu SO CAI cua giai doan giong."""
    ds = [d.item_key for d in su_dung.cac_dong(db, run,
                                               stage=pipeline.VOICE_SYNTHESIS)
          if d.item_key and not str(d.item_key).startswith("__")]
    assert ds, "khong doan tieng nao trong so cai"
    return sorted(ds)[0]


# ══════════════════════════════════════════════════════════════════════════════
#  Doi chung: khong co khiem khuyet thi chuoi ve `done` — bai duoi do MOT thu
# ══════════════════════════════════════════════════════════════════════════════

def test_DOI_CHUNG_khong_khiem_khuyet_thi_khong_vong_sua_va_run_DONE(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """⛔ Khong co doi chung thi mot bai do khong chung minh duoc gi: no phai
    tra loi duoc *"lan chay nay hong VI vong sua, hay von da hong"*."""
    _do_giong_gia(monkeypatch, hong=set())
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()

    run = features.lay_run(db, run.id, "uA")
    assert run.status == RUN_DONE, run.error
    vong = [d for d in su_dung.cac_dong(db, run, stage=pipeline.QC,
                                        item_key=jobs.DON_VI_SUA)
            if d.nang_luc == jobs.NANG_LUC_VONG_SUA]
    assert vong == [], "khong khiem khuyet ma van vao vong sua"


# ══════════════════════════════════════════════════════════════════════════════
#  M-09 — vong sua that
# ══════════════════════════════════════════════════════════════════════════════

def test_vong_sua_chay_lai_voice_synthesis_KHONG_chet_database_is_locked(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """🔴 **Bai chinh cua M-09.**

    Mot doan bi cham WER vuot nguong ⇒ `doc_sai` ⇒ dat lai `voice_synthesis`
    ⇒ giai doan chay lai. Truoc ban va, luot chay lai do chet
    `sqlite3.OperationalError: database is locked` ngay o `ctx.progress`, va
    ca lan chay ve `error`.
    """
    lan = {"n": 0}
    hong: set[str] = set()

    from apps.asv_gpu.do_luong import bo_do

    def chay_tat_ca(dv, **kw):
        lan["n"] += 1
        ket_qua = {}
        for d in dv.doan_tieng:
            ma = str(d["ma"])
            # Chi luot DO DAU TIEN cham hong — luot sau (sau khi doc lai) dat.
            xau = (lan["n"] == 1 and ma == sorted(
                str(x["ma"]) for x in dv.doan_tieng)[0])
            if xau:
                hong.add(ma)
            ket_qua[ma] = {"wer": 0.95 if xau else 0.01,
                           "cer": 0.90 if xau else 0.01,
                           "doc_ra": str(d.get("chu") or ""),
                           "tham_chieu_chuan": str(d.get("chu") or "")}
        return {"giong": {"trang_thai": "xong", "ket_qua": ket_qua}}

    monkeypatch.setattr(bo_do, "chay_tat_ca", chay_tat_ca)

    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    so_job = _chay_het_hang_doi(db)
    db.expire_all()

    run = features.lay_run(db, run.id, "uA")
    assert "locked" not in str(run.error or "").lower(), run.error
    assert run.status == RUN_DONE, f"{run.status}: {run.error}"
    assert so_job < 200, "vong sua quay: cham tran job cua khuon thu"

    # Vong sua DA THUC SU xay ra (neu khong, bai nay khong do gi).
    vong = [d for d in su_dung.cac_dong(db, run, stage=pipeline.QC,
                                        item_key=jobs.DON_VI_SUA)
            if d.nang_luc == jobs.NANG_LUC_VONG_SUA]
    assert len(vong) == 1 == sua_chua.VONG_SUA_TOI_DA
    ke = dict(vong[0].ghi_chu or {})
    assert list(ke["giai_doan_sua"]) == ["voice_synthesis"], ke["giai_doan_sua"]
    assert hong, "phep do gia khong cham hong doan nao"
    assert set(ke["giai_doan_sua"]["voice_synthesis"]) == hong


def test_vong_sua_KHONG_tinh_tien_hai_lan_cho_cung_mot_doan(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """⭐ Doan duoc doc lai sinh MOT dong so cai moi (`UNIQUE(run_id,
    ma_dispatch)` chan mot but toan trung), va cac doan LANH khong bi doc lai."""
    lan = {"n": 0}

    from apps.asv_gpu.do_luong import bo_do

    def chay_tat_ca(dv, **kw):
        lan["n"] += 1
        dau = sorted(str(x["ma"]) for x in dv.doan_tieng)[0]
        return {"giong": {"trang_thai": "xong", "ket_qua": {
            str(d["ma"]): ({"wer": 0.95, "cer": 0.90}
                           if (lan["n"] == 1 and str(d["ma"]) == dau)
                           else {"wer": 0.01, "cer": 0.01})
            | {"doc_ra": "", "tham_chieu_chuan": ""}
            for d in dv.doan_tieng}}}

    monkeypatch.setattr(bo_do, "chay_tat_ca", chay_tat_ca)

    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()
    run = features.lay_run(db, run.id, "uA")
    assert run.status == RUN_DONE, f"{run.status}: {run.error}"

    dong = [d for d in su_dung.cac_dong(db, run, stage=pipeline.VOICE_SYNTHESIS)
            if d.item_key and not str(d.item_key).startswith("__")]
    ma_dich = [str(d.ma_dispatch) for d in dong]
    # ⛔ `UNIQUE(run_id, ma_dispatch)`: mot but toan trung se bi CSDL chan,
    #    nen phep kiem nay do cai con lai — SO dong.
    assert len(ma_dich) == len(set(ma_dich)), ma_dich

    # ⭐ M-07: doan bi doc lai mang van tay CO MUOI ⇒ no co HAI dong so cai
    #    (hai luot doc that), moi doan lanh chi co MOT. Do la bang chung co hoc
    #    rang vong sua da lam viec that, va chi cho doan hong.
    from collections import Counter
    dem = Counter(str(d.item_key) for d in dong)
    assert sorted(dem.values()) == [1] * (len(dem) - 1) + [2], dict(dem)


def test_vong_sua_DICH_SAI_dat_lai_content_process_va_chay_lai_giong(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """⭐ **Doi chung cua `LOI_TONG` M-09**: duong `dich_sai` (co tu M-01,
    khong dung gi toi lan `qc-hinh`) dat lai `content_process`, tuc
    `voice_synthesis` chay lai voi TOAN BO artifact ha nguon da bi VO HIEU —
    khac hin duong `doc_sai` (chi mot don vi duoc mo lai).

    Do la hinh dang M-08 (`kiem_toan_ven` GHI roi goi `ctx.progress`) o mot
    giai doan khac, va no chinh la cai M-09 bao."""
    import json

    from apps.auto_scan_video import ai, giai_doan_qc_ai as gdqa
    monkeypatch.setenv(gdqa.BIEN_BAT, "1")
    _do_giong_gia(monkeypatch, hong=set())

    lan = {"n": 0}
    goc = ai.goi_tinh_tien

    def gia(db_, run_, thao_tac, messages, **kw):
        if thao_tac.ma == ai.QC_NGU_NGHIA.ma:
            lan["n"] += 1
            goi = json.loads(messages[-1]["content"])
            cac_doan = goi.get("doan") or []
            mas = sorted(str(d["ma"]) for d in cac_doan)
            # ⭐ GEMBA-MQM (91d921f4, da tren main): `qc_ai.doc_ngu_nghia` tinh
            #    `dat` TU `loi` (danh sach loi kem `muc`+`doan` trich nguyen
            #    van), ⛔ khong con doc truong `dat` model tu goi thang. Ban gia
            #    phai theo dung dang do, va `doan` phai la MOT DOAN TRICH THAT
            #    tu cau goc da gui (`qc_ai._loc_loi` loai loi khong trich duoc).
            doan = {m: {"loi": []} for m in mas}
            if lan["n"] == 1 and cac_doan:
                dau = cac_doan[0]
                trich = str(dau.get("goc") or "")[:50] or str(dau["ma"])
                doan[str(dau["ma"])] = {"loi": [
                    {"loai": "lat_nghia", "muc": "nghiem_trong",
                     "doan": trich, "ly_do": "nghia lech so voi nguon"}]}
            return {"noi_dung": json.dumps({"doan": doan}, ensure_ascii=False),
                    "provider": "gia", "model": "gia", "su_dung": None,
                    "finish_reason": "stop", "suy_nghi": ""}
        return goc(db_, run_, thao_tac, messages, **kw)

    monkeypatch.setattr(ai, "goi_tinh_tien", gia)
    monkeypatch.setattr(gdqa.ai, "goi_tinh_tien", gia, raising=False)

    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    so_job = _chay_het_hang_doi(db)
    db.expire_all()

    run = features.lay_run(db, run.id, "uA")
    assert "locked" not in str(run.error or "").lower(), run.error
    assert run.status == RUN_DONE, f"{run.status}: {run.error}"
    assert so_job < 200

    vong = [d for d in su_dung.cac_dong(db, run, stage=pipeline.QC,
                                        item_key=jobs.DON_VI_SUA)
            if d.nang_luc == jobs.NANG_LUC_VONG_SUA]
    assert len(vong) == 1, [dict(d.ghi_chu or {}) for d in vong]
    ke = dict(vong[0].ghi_chu or {})
    assert list(ke["giai_doan_sua"]) == ["content_process"], ke["giai_doan_sua"]


# ══════════════════════════════════════════════════════════════════════════════
#  Bat bien CO HOC — hinh dang chung cua M-08 va M-09
# ══════════════════════════════════════════════════════════════════════════════

def test_HAI_PHIEN_gap_nhau_that_su_thanh_database_is_locked(db, tmp_path,
                                                             kho_tam):
    """⭐ **Doi chung cua ca muc nay.** Truoc khi doi mot ban va, phai chung
    minh cai bay co that: mot phien giu transaction GHI chua dong, mot phien
    THU HAI ghi — SQLite tra ve `database is locked`.

    ⛔ Khong co bai nay thi hai bai duoi chi chung minh rang mot doan ma khong
       nem, khong chung minh duoc rang no *co the* nem.
    """
    from sqlalchemy.exc import OperationalError

    from platform_core.db import get_session

    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    run.error = "phien mot dang ghi"
    db.flush()                       # GHI, chua `commit` — giu khoa

    gen = get_session()
    hai = next(gen)
    try:
        hai_run = hai.get(type(run), run.id)
        hai_run.error = "phien hai"
        with pytest.raises(OperationalError, match="(?i)locked"):
            hai.commit()
    finally:
        hai.rollback()
        hai.close()
    db.rollback()


def test_kiem_toan_ven_KHONG_de_lai_transaction_GHI_chua_dong(
        db, tmp_path, kho_tam):
    """🔴 Ve thu nhat cua ban va M-09: `kiem_toan_ven` la mot phep DO co ghi
    lai ket qua — ket qua do la mot quan sat ve THE GIOI, khong phai mot manh
    cua don vi viec nguoi goi. Nen no `commit`, va duong LANH thi khong ghi gi.
    """
    import io

    from platform_core.storage import get_storage
    from apps.auto_scan_video import assets, pipeline
    from apps.auto_scan_video.tables import ASSET_MISSING, ASSET_OK

    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    kho = get_storage()
    khoa_tam = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                   stage=pipeline.VOICE_SYNTHESIS,
                                   van_tay="a" * 32, duoi="json")
    kho.put(khoa_tam, io.BytesIO(b"{}"), content_type="application/json")
    a = assets.promote_va_ghi(db, kho, owner_id=run.owner_id, run_id=run.id,
                              stage=pipeline.VOICE_SYNTHESIS,
                              van_tay="a" * 32, kind="json", duoi="json",
                              staging_key=khoa_tam)
    db.commit()

    # (1) Duong LANH: gia tri khong doi ⇒ khong mot lenh ghi nao.
    assert assets.kiem_toan_ven(db, kho, a) == ASSET_OK
    assert not db.dirty and not db.new, (db.dirty, db.new)

    # (2) Duong DOI (chinh la vong sua: artifact vua bi danh dau `missing`
    #     roi hoa ra van con nguyen) ⇒ ghi, va ghi xong thi phien SACH.
    assets.vo_hieu_theo_day_chuyen(db, run.id, [pipeline.VOICE_SYNTHESIS])
    db.commit()
    assert a.integrity == ASSET_MISSING
    assert assets.kiem_toan_ven(db, kho, a) == ASSET_OK
    assert not db.dirty and not db.new, (db.dirty, db.new)
    assert not db.in_transaction(), "con giu transaction sau khi da ghi xong"


def test_CtxChotSo_chot_so_TRUOC_moi_loi_goi_mo_phien_thu_hai(
        db, tmp_path, kho_tam):
    """🔴 Ve thu hai: hang rao chung. Mot giai doan BAT KY ghi roi bao tien do
    khong duoc chet — ke ca giai doan chua ai viet.

    ⛔ Bai nay co y KHONG dung `assets.kiem_toan_ven`: neu no dung, no chi do
       lai ve thu nhat mot lan nua.
    """
    from sqlalchemy.exc import OperationalError

    from platform_core.db import get_session
    from apps.auto_scan_video.thi_hanh import _CtxChotSo

    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)

    class CtxGia:
        """Bat chuoc `JobContext`: MOI loi goi mo mot phien RIENG."""

        def __init__(self):
            self.so_lan = 0

        def progress(self, phan_tram, thong_bao=""):
            self.so_lan += 1
            gen = get_session()
            hai = next(gen)
            try:
                r = hai.get(type(run), run.id)
                r.error = f"tien do {phan_tram}"
                hai.commit()
            finally:
                hai.close()

    # (a) KHONG co hang rao: dung cai bay cua M-08/M-09.
    run.error = "giai doan dang ghi"
    db.flush()
    with pytest.raises(OperationalError, match="(?i)locked"):
        CtxGia().progress(10)
    db.rollback()

    # (b) CO hang rao: chot so truoc, nen phien thu hai di duoc.
    run.error = "giai doan dang ghi"
    db.flush()
    ctx = _CtxChotSo(CtxGia(), db)
    ctx.progress(20)
    assert ctx.so_lan == 1                 # uy quyen thuoc tinh van chay
    assert not db.in_transaction(), "hang rao khong chot so"


def test_vong_sua_CAT_SAI_dat_lai_edit_plan_va_chay_lai_CA_CHUOI(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """⭐ Duong sua thu BA, va la duong dat nhat: `cat_sai` dat lai `edit_plan`
    — giai doan SOM NHAT — nen ca `content_process`, `voice_synthesis`,
    `timing_align`, `compose`, `render` va ba lop QC deu chay lai.

    `test_2121` (lan `qc-hinh`) co chu dinh KHONG chot `run.status` o day, vi
    luc no viet thi M-09 chan duong. Bai nay chot dieu con thieu do.
    """
    import json

    from apps.auto_scan_video import ai, giai_doan_qc_ai as gdqa, sua_chua as sc
    from tests.test_440_asv_v4_long_tieng import (_cat_canh_le, _nhieu_canh,
                                                  _run_cat)

    monkeypatch.setenv(gdqa.BIEN_BAT, "1")
    # ⛔ Chi trong bai nay: san pham van de lop QC hinh o che do TU VAN
    #    (`L_QC_HINH.md` §5). Bai nay hoi ve VONG SUA, khong ve chinh sach.
    monkeypatch.setattr(sc, "QC_HINH_LA_TU_VAN", False)
    _do_giong_gia(monkeypatch, hong=set())
    _nhieu_canh(monkeypatch)
    _cat_canh_le(monkeypatch)

    goc = ai.goi_tinh_tien

    def moi_cho_noi_deu_hong(db_, run_, thao_tac, messages, **kw):
        if thao_tac.ma == ai.QC_HINH.ma:
            return {"noi_dung": json.dumps(
                {"dat": False, "do_tin": 0.95, "ly_do": "cat giua dong tac"},
                ensure_ascii=False),
                "provider": "gia", "model": "gia", "su_dung": None,
                "finish_reason": "stop", "suy_nghi": ""}
        return goc(db_, run_, thao_tac, messages, **kw)

    monkeypatch.setattr(ai, "goi_tinh_tien", moi_cho_noi_deu_hong)
    monkeypatch.setattr(gdqa.ai, "goi_tinh_tien", moi_cho_noi_deu_hong,
                        raising=False)

    # 🔴 Nguon 24 giay: mot cho noi chi ton tai duoc khi ngan sach cat 5 % lon
    #    hon `ke_cat.TOI_THIEU_GIAY` — xem `test_2121.NGUON_CO_CHO_NOI_S`.
    from tests.test_2121_asv_qc_hinh_cho_noi import NGUON_CO_CHO_NOI_S

    run = _run_cat(db, kho_tam, tmp_path, duration_s=NGUON_CO_CHO_NOI_S)
    so_job = _chay_het_hang_doi(db)
    db.expire_all()

    run = features.lay_run(db, run.id, "uA")
    assert "locked" not in str(run.error or "").lower(), run.error
    assert run.status == RUN_DONE, f"{run.status}: {run.error}"
    assert so_job < 200

    vong = [d for d in su_dung.cac_dong(db, run, stage=pipeline.QC,
                                        item_key=jobs.DON_VI_SUA)
            if d.nang_luc == jobs.NANG_LUC_VONG_SUA]
    assert len(vong) == 1 == sua_chua.VONG_SUA_TOI_DA
    assert list(dict(vong[0].ghi_chu or {})["giai_doan_sua"]) == ["edit_plan"]
