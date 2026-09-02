"""Pha 16 — vo hieu theo phu thuoc, thu lai, lan truyen huy, va QC la cong cuoi.

Bon dieu duoi day de bi tuong la da co san vi chuoi chay duoc tu pha 05. Chung
khong co san: mot chuoi chay **mot mach tu dau den cuoi** khong bao gio cham
toi cau hoi "chuyen gi xay ra khi mot giai doan o giua phai lam lai".
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from apps.auto_scan_video import features, pipeline, thi_hanh
from apps.auto_scan_video.tables import (RUN_CANCELLED, RUN_DONE, STAGE_PENDING,
                                         STAGE_SUCCEEDED, AsvStage)
from tests.fixtures import asv_media as fx
from tests.test_402_asv_mach_doc_gia import (  # noqa: F401
    _chay_het_hang_doi, _tao_run, asr_gia, db, dich_gia, giong_gia, kho_tam)

NANG_LUC = {"api", "ffmpeg", "gpu", "voice"}


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Do thi phu thuoc — thuan, khong can CSDL
# ══════════════════════════════════════════════════════════════════════════════

def test_ha_nguon_la_BAO_DONG_bac_cau_chu_khong_phai_phu_thuoc_truc_tiep():
    """`render` an theo `media_prepare` **gian tiep**, qua sau giai doan.

    Mot ban cai dat chi tra ve phu thuoc truc tiep se vo hieu thieu, va thieu
    o day nghia la giao mot ban long tieng tron lan hai lan chay khac nhau.
    """
    assert pipeline.RENDER in pipeline.ha_nguon_cua(pipeline.MEDIA_PREPARE)
    assert pipeline.QC in pipeline.ha_nguon_cua(pipeline.MEDIA_PREPARE)


def test_giai_doan_cuoi_khong_co_ha_nguon():
    assert pipeline.ha_nguon_cua(pipeline.QC) == []


def test_ha_nguon_KHONG_bao_gom_chinh_no():
    for g in pipeline.CHUOI:
        assert g.ten not in pipeline.ha_nguon_cua(g.ten)


def test_ha_nguon_giu_dung_THU_TU_cua_chuoi():
    """Dat lai theo thu tu chuoi de mot nguoi doc log thay duoc dong chay."""
    ds = pipeline.ha_nguon_cua(pipeline.MEDIA_PREPARE)
    chi_so = [pipeline.TEN_GIAI_DOAN.index(t) for t in ds]
    assert chi_so == sorted(chi_so)


def test_hom_nay_ha_nguon_TRUNG_voi_moi_giai_doan_phia_sau():
    """⚠️ Chot chinh SU TRUNG NHAU, khong phai chot rang no phai trung.

    Do thi hom nay gan nhu mot duong thang, nen `ha_nguon_cua(x)` bang
    `CHUOI[i+1:]`. Hai thu do bang nhau **do hoan canh, khong do dinh nghia**.

    ⭐ Phep kiem nay ton tai de luc chung TACH RA thi co mot dong noi ra. Khi no
       do, dung "sua" bang cach doi `ha_nguon_cua` — hay doc lai: rat co the ai
       do vua them mot nhanh doc lap, va do dung la luc `CHUOI[i+1:]` tro thanh
       mot cach vo hieu SAI (bat khach tra tien lai cho viec khong dau vao nao
       doi). Cap nhat phep kiem nay, dung cap nhat ham.
    """
    for i, g in enumerate(pipeline.CHUOI):
        assert pipeline.ha_nguon_cua(g.ten) == list(pipeline.TEN_GIAI_DOAN[i + 1:])


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Thu lai mot giai doan (muc 7)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def run_xong(db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia):
    fx.require_ffmpeg()
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    return run


@pytest.fixture()
def run_dang_chay(db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia):
    """Mot run **chua** ket thuc: chay mot so job roi dung.

    Can rieng vi `thu_lai_giai_doan` co y tu choi mot run da ket thuc.
    """
    fx.require_ffmpeg()
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg"}, toi_da=6)
    return run


def test_thu_lai_dat_lai_giai_doan_do_VA_ha_nguon_cua_no(run_dang_chay, db):
    kq = features.thu_lai_giai_doan(db, run_dang_chay.id, "uA",
                                    pipeline.MEDIA_PREPARE)
    db.commit()
    assert kq["da_dat_lai"][0] == pipeline.MEDIA_PREPARE
    # Moi giai doan an theo deu phai co trong danh sach hoac von da pending.
    for s in features.cac_giai_doan(db, run_dang_chay):
        assert s.status == STAGE_PENDING, f"{s.stage} chua duoc dat lai"


def test_thu_lai_KHONG_dong_toi_giai_doan_THUONG_NGUON(run_dang_chay, db):
    """⛔ Chay lai ca lan chay la bat khach tra tien lai cho chep loi, dich va
    sinh tieng — ba thu dat nhat, va khong thu nao lien quan toi mot loi o cuoi.
    """
    truoc = {s.stage: (s.status, s.fingerprint)
             for s in features.cac_giai_doan(db, run_dang_chay)}
    xong_truoc = [t for t, (st, _) in truoc.items() if st == STAGE_SUCCEEDED]
    assert xong_truoc, "bo do khong chay xong giai doan nao — phep kiem vo nghia"

    # Thu lai giai doan cuoi cung DA XONG: khong giai doan nao truoc no bi dong.
    muc = xong_truoc[-1]
    features.thu_lai_giai_doan(db, run_dang_chay.id, "uA", muc)
    db.commit()

    sau = {s.stage: (s.status, s.fingerprint)
           for s in features.cac_giai_doan(db, run_dang_chay)}
    i = pipeline.TEN_GIAI_DOAN.index(muc)
    for ten in pipeline.TEN_GIAI_DOAN[:i]:
        assert sau[ten] == truoc[ten], f"{ten} (thuong nguon) bi dong toi"


def test_thu_lai_GIU_lai_so_lan_thu(run_dang_chay, db):
    """`attempt` la su that ve lich su cua lan chay, khong phai bo dem tien do.

    Xoa no la xoa dung thu can de tra loi "vi sao lan chay nay ton nhieu tien".
    """
    s = features.giai_doan_theo_ten(db, run_dang_chay.id, pipeline.MEDIA_PREPARE)
    truoc = int(s.attempt)
    assert truoc >= 1
    features.thu_lai_giai_doan(db, run_dang_chay.id, "uA", pipeline.MEDIA_PREPARE)
    db.commit()
    s = features.giai_doan_theo_ten(db, run_dang_chay.id, pipeline.MEDIA_PREPARE)
    assert int(s.attempt) == truoc


def test_thu_lai_mot_run_DA_KET_THUC_bi_tu_choi(run_xong, db):
    """⛔ `quyet_toan` da hoan phan credit chua dung. Mot lan chay tiep sau do se
    tieu tien ma khong con cho giu."""
    assert run_xong.status == RUN_DONE
    with pytest.raises(features.AsvError):
        features.thu_lai_giai_doan(db, run_xong.id, "uA", pipeline.RENDER)


def test_thu_lai_ten_giai_doan_KHONG_CO_bi_tu_choi(run_dang_chay, db):
    with pytest.raises(features.AsvError):
        features.thu_lai_giai_doan(db, run_dang_chay.id, "uA", "khong-co-that")


def test_thu_lai_cua_NGUOI_KHAC_bi_tu_choi(run_dang_chay, db):
    with pytest.raises(features.AsvError):
        features.thu_lai_giai_doan(db, run_dang_chay.id, "uB",
                                   pipeline.MEDIA_PREPARE)


def test_sau_khi_thu_lai_thi_chuoi_CHAY_TIEP_toi_done(run_dang_chay, db):
    """Thu lai khong duoc lam ket lan chay: dieu phoi vien phai duoc danh thuc."""
    features.thu_lai_giai_doan(db, run_dang_chay.id, "uA", pipeline.MEDIA_PREPARE)
    db.commit()
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    run = features.lay_run(db, run_dang_chay.id, "uA")
    assert run.status == RUN_DONE


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Vo hieu TU DONG khi van tay lech (muc 4)
# ══════════════════════════════════════════════════════════════════════════════

def test_khong_lech_thi_khong_dat_lai_gi(run_xong, db):
    """Chieu am, va no quan trong hon ve mat chi phi: mot bo do lech nham se
    lam MOI lan chay lap lai toan bo chuoi."""
    assert thi_hanh.giai_doan_lech_van_tay(db, run_xong) == []


def test_bo_do_lech_bat_giai_doan_bi_sua_VA_giai_doan_ke_no(run_xong, db):
    """Bo do lech la MOT BUOC, va do la thiet ke chu khong phai thieu sot.

    Sua van tay da luu cua `transcribe` roi do:

        lech = ['transcribe', 'content_process']

    ⭐ Hai muc, khong phai bay. `render` **chua** lech, vi van tay cua no doc van
       tay cua `compose`, ma `compose` chua doi. Song lech lan truyen mot buoc
       moi luot.

    ⚠️ Ban dau phep kiem nay doi ca `render` phai co trong danh sach, va no do —
       nhung ma **dung**. Hai suy luan sai trong cung mot dong:

         * cho rang bo do doc bac cau (no khong, va no khong can: khep kin bac
           cau la viec cua `_vo_hieu_giai_doan_da_lech`, xem phep kiem duoi);
         * cho rang `transcribe` khong lech — trong khi chinh gia tri da luu cua
           no vua bi gia mao, nen tinh lai tat nhien khong khop.

    ⇒ Bo do tra loi "dong nao khong con dung voi dau vao cua no", KHONG tra loi
      "nhung gi can lam lai". Cau thu hai la cua tang tren.
    """
    s = features.giai_doan_theo_ten(db, run_xong.id, pipeline.TRANSCRIBE)
    features.cap_nhat_giai_doan(db, s, fingerprint="doi-roi" + "0" * 50)
    db.commit()

    lech = thi_hanh.giai_doan_lech_van_tay(db, run_xong)
    assert pipeline.TRANSCRIBE in lech, "dong bi gia mao phai duoc phat hien"
    assert pipeline.CONTENT_PROCESS in lech, "giai doan ke ngay phai lech theo"
    assert pipeline.RENDER not in lech, (
        "bo do dang doc bac cau — no chi nen doc mot buoc, va tang tren moi lo "
        "khep kin (xem `test_advance_TU_DAT_LAI_giai_doan_lech...`)")


def test_advance_TU_DAT_LAI_giai_doan_lech_thay_vi_ket_thuc(db, kho_tam,
                                                            tmp_path, asr_gia,
                                                            dich_gia, giong_gia):
    """🔑 Cot loi cua muc 4.

    Neu `_advance` khong lam viec nay, mot giai doan da lech van duoc dem la
    `succeeded`, `len(da_xong) == 9`, va lan chay ket thuc bang mot ban long
    tieng tron lan hai lan chay khac nhau — khong loi nao bao.
    """
    from apps.auto_scan_video import jobs as asv_jobs
    from apps.auto_scan_video.tables import RUN_RUNNING

    fx.require_ffmpeg()
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    assert features.lay_run(db, run.id, "uA").status == RUN_DONE

    # Dung run day lai va lam lech mot giai doan giua chuoi.
    run = features.lay_run(db, run.id, "uA")
    run.status = RUN_RUNNING
    s = features.giai_doan_theo_ten(db, run.id, pipeline.VOICE_SYNTHESIS)
    features.cap_nhat_giai_doan(db, s, fingerprint="l" * 58)
    db.commit()

    da_dat_lai = asv_jobs._vo_hieu_giai_doan_da_lech(db, run)
    db.commit()

    assert pipeline.TIMING_ALIGN in da_dat_lai
    assert pipeline.RENDER in da_dat_lai
    assert pipeline.QC in da_dat_lai
    for ten in (pipeline.TIMING_ALIGN, pipeline.COMPOSE, pipeline.RENDER,
                pipeline.QC):
        assert features.giai_doan_theo_ten(db, run.id, ten).status == STAGE_PENDING


# ══════════════════════════════════════════════════════════════════════════════
#  §4  QC la cong cuoi, khong phai RENDER (muc 9)
# ══════════════════════════════════════════════════════════════════════════════

def test_run_KHONG_ve_done_khi_moi_chi_RENDER_xong(db, kho_tam, tmp_path,
                                                   asr_gia, dich_gia, giong_gia):
    """⛔ `render` xong khong phai la lan chay xong. Prompt 16 muc 9.

    Chot bang cach chay het hang doi RỒI ha rieng QC ve pending: neu dieu kien
    ket thuc chi doc `render` thi run se ve `done` o luot advance ke tiep du QC
    chua chay.
    """
    from apps.auto_scan_video.tables import RUN_RUNNING

    fx.require_ffmpeg()
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    run = features.lay_run(db, run.id, "uA")
    run.status = RUN_RUNNING
    s = features.giai_doan_theo_ten(db, run.id, pipeline.QC)
    features._dat_lai_giai_doan(db, s)
    features._nop_dieu_phoi(db, run, ly_do="kiem-qc-la-cong-cuoi")
    db.commit()

    # Worker KHONG co nang luc ffmpeg => QC (lan asv_media) khong chay duoc.
    _chay_het_hang_doi(db, nang_luc={"api"})
    run = features.lay_run(db, run.id, "uA")
    assert run.status != RUN_DONE, (
        "run ve done khi QC chua chay — dieu kien ket thuc dang doc RENDER")

    # Cho du nang luc: QC chay, va gio moi duoc ve done.
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    assert features.lay_run(db, run.id, "uA").status == RUN_DONE


def test_QC_la_giai_doan_CUOI_CUNG_cua_chuoi():
    """Chot vi tri, de mot luot sau them giai doan sau QC khong lam menh de
    "run xong khi QC xong" thanh sai mot cach im lang."""
    assert pipeline.TEN_GIAI_DOAN[-1] == pipeline.QC


# ══════════════════════════════════════════════════════════════════════════════
#  §5  Huy lan truyen (muc 8)
# ══════════════════════════════════════════════════════════════════════════════

def test_huy_dat_moi_giai_doan_CHUA_XONG_ve_cancelled(run_dang_chay, db):
    features.huy_run(db, run_dang_chay.id, "uA")
    db.commit()
    run = features.lay_run(db, run_dang_chay.id, "uA")
    assert run.status == RUN_CANCELLED
    for s in features.cac_giai_doan(db, run):
        assert s.status in (STAGE_SUCCEEDED, "cancelled", "failed_terminal"), (
            f"{s.stage} con o trang thai {s.status} sau khi huy")


def test_sau_khi_huy_thi_chay_tiep_KHONG_lam_run_song_lai(run_dang_chay, db):
    """I13. Mot job con ve dich muon khong duoc lam song lai mot run da huy."""
    features.huy_run(db, run_dang_chay.id, "uA")
    db.commit()
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    assert features.lay_run(db, run_dang_chay.id, "uA").status == RUN_CANCELLED


def test_huy_KHONG_de_lai_job_con_dang_song(run_dang_chay, db):
    from platform_core.models import Job

    features.huy_run(db, run_dang_chay.id, "uA")
    db.commit()
    con = db.execute(select(Job).where(
        Job.plan_id == run_dang_chay.id)).scalars().all()
    song = [j for j in con if j.status in ("queued", "running")]
    assert song == [], f"con {len(song)} job con chua bi huy"


# ══════════════════════════════════════════════════════════════════════════════
#  §6  Khong nhan doi giu cho / job / artifact (verification cua Prompt 16)
# ══════════════════════════════════════════════════════════════════════════════

def test_thu_lai_KHONG_giu_them_mot_khoan_credit_nao(run_dang_chay, db):
    """Mot lan chay giu tien DUNG MOT LAN, tren `run.id` (ADR-001 D3).

    Thu lai la mot thao tac dieu khien, khong phai mot lan chay moi.
    """
    from platform_core import credit

    truoc = credit.so_du(db, "uA")
    giu_truoc = int(run_dang_chay.credit_held)
    features.thu_lai_giai_doan(db, run_dang_chay.id, "uA", pipeline.MEDIA_PREPARE)
    db.commit()
    run = features.lay_run(db, run_dang_chay.id, "uA")
    assert int(run.credit_held) == giu_truoc
    assert credit.so_du(db, "uA") == truoc


def test_moi_giai_doan_chi_co_MOT_dong_du_da_thu_lai(run_dang_chay, db):
    features.thu_lai_giai_doan(db, run_dang_chay.id, "uA", pipeline.MEDIA_PREPARE)
    db.commit()
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    hang = db.execute(select(AsvStage).where(
        AsvStage.run_id == run_dang_chay.id)).scalars().all()
    ten = [s.stage for s in hang]
    assert len(ten) == len(set(ten)) == len(pipeline.CHUOI)
