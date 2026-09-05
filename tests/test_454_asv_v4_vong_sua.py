"""Auto Scan Video V4 — vong SUA: nua thu hai cua pha 19, cuoi cung duoc lai.

Bao cao pha 19 goi ten mon no cua chinh no rat ro:

    "The repair loop is planned, not yet driven. `sua_chua` decides *what* to
     redo and *where*; wiring that into a failing run is the remaining half."

Mon no do di qua pha 26 (dem duoc "mot thoi quen, nam lan"), pha 27 (dem them
lan thu sau va thu bay), pha 28 va pha 29 ma khong ai tra. No de lai **bon**
nang luc mo coi cung phuc vu mot tinh nang:

    `sua_chua.py`                     tinh CAI GI phai lam lai va O DAU
    `qc_ai.py`                        mot nguon khiem khuyet nua
    `assets.vo_hieu_theo_day_chuyen`  danh dau artifact ha nguon
    `ITEM_INVALIDATED`                trang thai cho don vi bi bo ket qua

🔴 **Va khiem khuyet no bo sot la khiem khuyet THAT.** `nan_cho_vua` danh dau
   `CAN_SUA` cho mot doan khong vua khe **ke ca sau khi da het bac thang co
   gian**; `giai_doan_giong` ghi dau do vao so cai; va khong dong ma san pham
   nao doc no. Tuc san pham BIET mot doan khong vua, GHI LAI, roi giao hang.

Bo kiem nay chot bon dieu cong thoat pha 19 doi, theo dung thu tu chung co the
hong:

  §1  mot doan `CAN_SUA` phai lam giai doan som nhat sua duoc no chay lai
  §2  va **chi** doan do — pham vi nho nhat an toan
  §3  vong sua co TRAN, va het tran la that bai CO BIEN chu khong phai lap mai
  §4  tran do nam trong CSDL, khong nam trong mot bien
"""
from __future__ import annotations

import json

import pytest

from apps.auto_scan_video import features, jobs, pipeline, su_dung, sua_chua
from apps.auto_scan_video.tables import (ASSET_MISSING, ASSET_OK,
                                         ITEM_INVALIDATED, ITEM_SUCCEEDED,
                                         RUN_DONE, RUN_ERROR, RUN_RUNNING,
                                         STAGE_FAILED_TERMINAL,
                                         STAGE_SUCCEEDED, AsvAsset, AsvRun,
                                         AsvStage)
from apps.auto_scan_video.nan_cho_vua import CAN_SUA, VUA


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """SQLite tam, cung khuon voi `tests/test_430`."""
    url = f"sqlite:///{(tmp_path / 'asv.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    s = next(gen)
    try:
        yield s
    finally:
        s.close()
        dbmod.reset_engine()


def _run_da_chay_het(db, *, owner="u1") -> AsvRun:
    """Mot lan chay MOI giai doan deu `succeeded` — ngay truoc cua giao hang.

    ⚠️ `credit_held=0` co chu dich: `quyet_toan` chi goi `credit.quyet_toan` khi
       con tien giu, va bai nay do vong SUA chu khong do so credit. Giu tien o
       day se keo ca so cai nen tang vao mot bai khong noi gi ve no.

    ⚠️ `fingerprint=""` cung co chu dich: `giai_doan_lech_van_tay` bo qua giai
       doan khong co van tay, nen lan advance khong tu dat lai gi ca. Neu no tu
       dat lai, bai nay se xanh vi mot ly do khac han ly do no tuyen bo.
    """
    run = AsvRun(owner_id=owner, source_key="asv/u1/nguon/x.mp4",
                 settings={}, credit_held=0, status=RUN_RUNNING)
    db.add(run)
    db.flush()
    for g in pipeline.CHUOI:
        db.add(AsvStage(run_id=run.id, owner_id=owner, stage=g.ten,
                        status=STAGE_SUCCEEDED, fingerprint=""))
    db.flush()
    return run


def _doan_tieng(db, run, ma: str, *, trang_thai_nan: str, giay: float = 3.0):
    """Mot doan tieng da tinh tien, kem phan quyet NAN — y het duong that.

    ⭐ Ghi qua `su_dung.ghi` chu khong `db.add(AsvUsage(...))`: do la duong duy
       nhat san pham dung, nen bai kiem di qua chinh cai cua ma san pham di qua.
       Dung tay thi bai se van xanh sau khi cua that doi hinh dang.
    """
    su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key=ma,
                su_dung=su_dung.SuDung(
                    nang_luc="tong_hop_tieng", app_chu="ltt_voice",
                    trang_thai=su_dung.DA_GIAO, don_vi=su_dung.GIAY,
                    so_luong=float(giay), credit=0,
                    ma_dispatch=f"giong:{ma}:vt",
                    ghi_chu={"trang_thai_nan": trang_thai_nan, "so_vong": 2}))
    su_dung.danh_dau_xong(db, run, stage=pipeline.VOICE_SYNTHESIS,
                          item_key=ma, fingerprint="vt")
    db.flush()


def _advance(db, run):
    return jobs._advance(db, run_id=run.id, owner_id=run.owner_id)


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Mot doan CAN_SUA phai lam giai doan sua duoc no chay lai
# ══════════════════════════════════════════════════════════════════════════════

def test_khong_khiem_khuyet_thi_van_QUYET_TOAN_nhu_cu(db):
    """⭐ Chot mac dinh truoc: vong sua khong duoc lam cham duong hanh phuc.

    Mot co che sua chua chi duoc phep xen vao khi CO gi de sua. Neu bai nay do,
    moi lan chay binh thuong deu dang di qua mot nhanh khong ai muon.
    """
    run = _run_da_chay_het(db)
    _doan_tieng(db, run, "seg_0001", trang_thai_nan=VUA)
    _doan_tieng(db, run, "seg_0002", trang_thai_nan=VUA)

    kq = _advance(db, run)
    assert kq["status"] == RUN_DONE
    assert "sua_chua" not in kq


def test_doan_CAN_SUA_lam_GIONG_va_HA_NGUON_chay_lai(db):
    """🔴 Truoc ban va nay, lan chay nay ket thuc `done` — kem mot doan khong vua.

    `nan_cho_vua` da ket luan doan khong vua khe **sau khi het bac thang**, va
    `giai_doan_giong` da ghi ket luan do vao so cai. Khong ai doc.
    """
    run = _run_da_chay_het(db)
    _doan_tieng(db, run, "seg_0001", trang_thai_nan=VUA)
    _doan_tieng(db, run, "seg_0002", trang_thai_nan=CAN_SUA)

    kq = _advance(db, run)

    assert kq["status"] != RUN_DONE, "lan chay co doan khong vua ma van giao hang"
    dat_lai = set(kq.get("sua_chua") or ())
    assert pipeline.VOICE_SYNTHESIS in dat_lai, (
        "`khong_vua` phai sua o `voice_synthesis` — doc lai dung doan do")
    # ⛔ Ha nguon phai di theo: mot ban tieng moi ma van dung ban dung cu la
    #    giao mot ban tron lan hai lan chay.
    for ten in (pipeline.TIMING_ALIGN, pipeline.COMPOSE, pipeline.RENDER,
                pipeline.QC):
        assert ten in dat_lai, f"{ten} phai bi vo hieu theo `voice_synthesis`"

    theo_ten = {s.stage: s for s in features.cac_giai_doan(db, run)}
    assert theo_ten[pipeline.VOICE_SYNTHESIS].status != STAGE_SUCCEEDED


def test_khong_day_nguoc_len_giai_doan_SOM_HON_can_thiet(db):
    """⛔ Doan khong vua **khong duoc** day ve `content_process`.

    `sua_chua` noi thang vi sao o docstring cua no, va day la cho dieu do duoc
    cuong che tren duong chay that chu khong chi trong mot phep tinh: viet lai
    cau van la tra tien de doi mot cau dung lay mot cau khac cung dung.
    """
    run = _run_da_chay_het(db)
    _doan_tieng(db, run, "seg_0001", trang_thai_nan=CAN_SUA)

    kq = _advance(db, run)
    dat_lai = set(kq.get("sua_chua") or ())

    # 🔴 **Chot rang CO sua truoc da.** Bai nay chi kiem nhung giai doan KHONG
    #    duoc dung toi, nen no xanh y het nhau o hai tinh huong trai nguoc: "da
    #    sua, va sua dung cho" va "khong sua gi ca". Mot dot bien tat ca vong sua
    #    di da lam no xanh — no khong do duoc dieu no tuyen bo.
    assert pipeline.VOICE_SYNTHESIS in dat_lai, (
        "chua co viec sua nao xay ra — phan con lai cua bai nay se xanh rong")

    for ten in (pipeline.CONTENT_PROCESS, pipeline.EDIT_PLAN,
                pipeline.TRANSCRIBE, pipeline.MEDIA_PREPARE):
        assert ten not in dat_lai, (
            f"{ten} bi lam lai cho mot khiem khuyet no khong gay ra")


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Va CHI doan do — pham vi nho nhat an toan
# ══════════════════════════════════════════════════════════════════════════════

def test_CHI_doan_hong_bi_mo_lai_doan_lanh_van_con_xong(db):
    """🔑 Day la "smallest safe scope" cua cong thoat pha 19, do duoc.

    ⭐ Do o cap DON VI, khong o cap giai doan. Giai doan `voice_synthesis` co
       chay lai — no phai chay lai — nhung `su_dung.da_xong` loc theo
       `ITEM_SUCCEEDED`, nen doan lanh nam ngoai tap viec va khong bi doc lai.
       Mot bai chi kiem "giai doan da dat lai" se xanh ca khi ca hai doan deu bi
       lam lai, tuc no khong do duoc dieu no noi.
    """
    run = _run_da_chay_het(db)
    _doan_tieng(db, run, "seg_lanh", trang_thai_nan=VUA)
    _doan_tieng(db, run, "seg_hong", trang_thai_nan=CAN_SUA)

    _advance(db, run)

    lanh = features.don_vi_theo_khoa(db, run.id, pipeline.VOICE_SYNTHESIS,
                                     "seg_lanh")
    hong = features.don_vi_theo_khoa(db, run.id, pipeline.VOICE_SYNTHESIS,
                                     "seg_hong")
    assert lanh.status == ITEM_SUCCEEDED, "doan lanh bi lam lai — tra tien vo ich"
    assert hong.status == ITEM_INVALIDATED, "doan hong khong duoc mo lai"

    con_lai = su_dung.da_xong(db, run, stage=pipeline.VOICE_SYNTHESIS,
                              fingerprint="vt")
    assert con_lai == {"seg_lanh"}, (
        "tap viec cua lan chay lai phai chi con doan hong")


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Vong sua co TRAN
# ══════════════════════════════════════════════════════════════════════════════

def test_HET_VONG_thi_KHONG_lap_mai_va_KHONG_giet_lan_chay(db):
    """⛔ Vong "sua roi kiem lai" tren dich vu tra tien la hoa don khong day —
    nen phai dung. Nhung dung KHONG duoc bien thanh giet.

    🔴 **Ban dau bai nay chot dieu nguoc lai, va so lieu that da bac no.**

       Toi viet nhanh "het vong -> `RUN_ERROR`" vi cong thoat pha 19 co chu
       "bounded terminal failure". Roi doc bang chung cua luot nghiem thu THAT
       gan nhat — luot vua duoc goi la xanh hoan toan:

           giu hinh        so_vua 3 | so_co_gian 0 | **so_can_sua 3**
           cat thong minh  so_vua 5 | so_co_gian 0 | **so_can_sua 1**

       Ca hai luot deu se ve `error` duoi ban dau tien cua toi. Mot ban va lam
       hong luot chay xanh nhat tung co la mot ban va sai, khong phai mot cong
       nghiem ngat.

    ⭐ Vi `CAN_SUA` khong dong nghia "video hong": `thoi_gian` hap thu phan vuot
       bang no troi (tran `TRAN_TROI_SO_DOAN`), va QC do dung hau qua do —
       **T7** (troi cua mot doan) va **T11** (troi tich luy). Ca hai DAT tren
       chinh ban giao ay. Hau qua da co cong gac; them mot cong o tang nan la
       gac hai lan cung mot thu, bang mot nguong ma chinh ma nguon ghi la CHUA
       DO (`DUNG_SAI_DAI`).

    ⚠️ Va "bounded terminal failure" trong cong thoat pha 19 noi ve **QC
       failures**. `CAN_SUA` la phan quyet cua tang NAN. Toi da gop hai thu do.
    """
    run = _run_da_chay_het(db)
    _doan_tieng(db, run, "seg_0009", trang_thai_nan=CAN_SUA)

    kq1 = _advance(db, run)
    assert kq1.get("sua_chua"), "vong dau phai sua"

    # Dua lan chay tro lai "da chay het" — y nhu worker da lam lai xong ma doan
    # van khong vua.
    for s in features.cac_giai_doan(db, run):
        s.status = STAGE_SUCCEEDED
    db.flush()

    kq2 = _advance(db, run)
    assert kq2["status"] == RUN_DONE, (
        "het vong ma van giet lan chay: QC da la cong gac cho hau qua cua "
        "`CAN_SUA` (T7/T11), day la gac hai lan")
    assert not kq2.get("sua_chua"), "khong duoc sua them vong nao nua"

    # ⭐ Nhung khiem khuyet con lai phai de lai DAU VET — im lang la thu dua ta
    #    vao day ngay tu dau.
    con_lai = [d for d in su_dung.cac_dong(db, run, stage=pipeline.QC,
                                           item_key=jobs.DON_VI_SUA)
               if d.nang_luc == "sua_chua_con_lai"]
    assert len(con_lai) == 1, (
        "khiem khuyet con lai sau khi het vong phai duoc ghi vao so cai")
    assert "seg_0009" in json.dumps(con_lai[0].ghi_chu, ensure_ascii=False), (
        "dau vet phai goi TEN doan — mot ghi chu khong ten khong tra loi duoc "
        "cau hoi se duoc hoi sau do")


def test_lan_chay_QC_HONG_van_hong_nhu_cu(db):
    """⛔ Bo duong giet cua vong sua khong duoc lam mem cong QC that.

    Bai nay ton tai vi ban sua tren de lai mot rui ro ro rang: neu ai do doc no
    thanh "vong sua khong bao gio lam hong lan chay", buoc tiep theo de nghi la
    lam mem ca QC. Mot giai doan hong han van phai giet lan chay.
    """
    run = _run_da_chay_het(db)
    _doan_tieng(db, run, "seg_0001", trang_thai_nan=CAN_SUA)
    qc = [s for s in features.cac_giai_doan(db, run)
          if s.stage == pipeline.QC][0]
    qc.status = STAGE_FAILED_TERMINAL
    qc.error = "T5: dinh that vuot tran"
    db.flush()

    kq = _advance(db, run)
    assert kq["status"] == RUN_ERROR
    db.refresh(run)
    assert "T5" in run.error


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Tran nam trong CSDL, khong nam trong mot bien
# ══════════════════════════════════════════════════════════════════════════════

def test_VONG_SUA_duoc_GHI_VAO_SO_CAI_va_khong_dem_hai_lan(db):
    """🔑 Bo dem la SO DONG SO CAI, va do khong phai mot chi tiet trien khai.

    Mot bien trong bo nho chet theo worker; mot cot dem co the bi hai luot
    advance cung tang. `UNIQUE(run_id, ma_dispatch)` thi khong — no la mot tran
    do CSDL cuong che.

    ⭐ Va no lam vong sua **nhin thay duoc trong hoa don**: nguoi ho tro doc so
       ke se thay lan chay nay da quyet dinh lam lai viec gi, chu khong phai chi
       thay tong tien to hon.
    """
    run = _run_da_chay_het(db)
    _doan_tieng(db, run, "seg_0003", trang_thai_nan=CAN_SUA)

    _advance(db, run)

    dong = [d for d in su_dung.cac_dong(db, run, stage=pipeline.QC,
                                        item_key=jobs.DON_VI_SUA)
            if d.nang_luc == jobs.NANG_LUC_VONG_SUA]
    assert len(dong) == 1, "mot vong sua phai de lai dung mot dong so cai"
    assert dong[0].credit == 0, "vong sua tu no khong duoc tinh tien"
    assert dong[0].ghi_chu.get("giai_doan_sua"), (
        "dong so cai phai mang ke hoach — no la bang chung, khong phai mot dau tich")

    # Goi lai chinh nhanh do: tran phai giu, khong sinh dong thu hai.
    theo_ten = {s.stage: s for s in features.cac_giai_doan(db, run)}
    jobs._sua_chua_neu_can(db, run, theo_ten)
    # ⚠️ Dem theo `nang_luc`: luot goi thu hai het vong nen no ghi mot dong
    #    `sua_chua_con_lai` dung chung `item_key`. Neu bai nay dem ca hai, no se
    #    xanh ngay ca khi bo dem cua san pham cung dem ca hai — tuc no khong con
    #    do duoc dieu no noi.
    assert len([d for d in su_dung.cac_dong(db, run, stage=pipeline.QC,
                                            item_key=jobs.DON_VI_SUA)
                if d.nang_luc == jobs.NANG_LUC_VONG_SUA]) == 1


def test_ma_dispatch_cua_vong_sua_KHAC_NHAU_giua_cac_vong(db, monkeypatch):
    """⚠️ Neu ma dispatch khong doi theo vong, tran se la MOT vong vinh vien.

    `UNIQUE(run_id, ma_dispatch)` giu HAI vai cung luc: no dem vong, va no chan
    ghi trung. Hai vai do chi song chung duoc khi ma mang so vong.

    🔴 **Ban dau bai nay doc AST va no YEU — day la ban thay the.**

       Ban cu chi doi *"co it nhat mot `ma_dispatch` la f-string"*. No khong doi
       f-string ay mang so vong, va no xanh ca khi ai do viet `f"sua:{0}"` — tuc
       xanh trong khi lam hong dung cai no duoc viet ra de canh.

    ⭐ Do la mot phep do tra loi cau *"co dung dinh dang khong"* trong khi cau
       can hoi la *"hai vong co ra hai ma khac nhau khong"*. Nen ban nay chay
       THAT hai vong va doi hai ma — mot cau hoi ma dinh dang khong tra loi ho
       duoc.
    """
    # Noi tran len 2 de co vong thu hai that su xay ra.
    monkeypatch.setattr(sua_chua, "VONG_SUA_TOI_DA", 2)

    run = _run_da_chay_het(db)
    _doan_tieng(db, run, "seg_0007", trang_thai_nan=CAN_SUA)

    def _mot_vong():
        for s in features.cac_giai_doan(db, run):
            s.status = STAGE_SUCCEEDED
        db.flush()
        return _advance(db, run)

    assert _mot_vong().get("sua_chua"), "vong 1 phai sua"
    assert _mot_vong().get("sua_chua"), (
        "vong 2 KHONG chay — dau hieu ma dispatch khong doi theo vong, nen "
        "`UNIQUE(run_id, ma_dispatch)` coi vong 2 la mot ban ghi trung")

    ma = [d.ma_dispatch for d in su_dung.cac_dong(db, run, stage=pipeline.QC,
                                                  item_key=jobs.DON_VI_SUA)
          if d.nang_luc == jobs.NANG_LUC_VONG_SUA]
    assert len(ma) == 2, f"phai co dung hai dong vong sua, dang co {len(ma)}"
    assert len(set(ma)) == 2, f"hai vong dung CHUNG mot ma dispatch: {ma}"

def _asset(db, run, stage: str, khoa: str) -> AsvAsset:
    a = AsvAsset(owner_id=run.owner_id, run_id=run.id, created_by_stage=stage,
                 kind="audio", storage_key=khoa, integrity=ASSET_OK)
    db.add(a)
    db.flush()
    return a


def test_ARTIFACT_cua_chinh_giai_doan_duoc_sua_KHONG_bi_danh_dau_mat(db):
    """🔴 **Bo tam bai kiem cua tep nay tung XANH trong khi E2E hong vi dieu nay.**

    Ban dau `_sua_chua_neu_can` truyen ca danh sach `dat_lai` — tuc CA
    `voice_synthesis` — vao `assets.vo_hieu_theo_day_chuyen`. Artifact cua chinh
    giai doan dang duoc sua bi danh dau `missing`, ke ca tieng cua nhung doan con
    LANH. Luot chay lai khong tai dung duoc chung nua, va hau qua lo ra o mot cho
    khong ai ngo:

        timing_align failed_terminal
        "He so co gian 3.304 ngoai khoang mot lan `atempo`"

    ⛔ Tuc chinh buoc don dep pha "pham vi nho nhat an toan" ma ca co che nay ton
       tai de bao ve. Va khong mot bai don vi nao thay: chung do TRANG THAI cua
       giai doan va don vi, khong do ARTIFACT.

    ⭐ Nen bai nay do dung thu con thieu — mot ban do 3 phut moi thay duoc, gio
       thay trong mot giay.
    """
    run = _run_da_chay_het(db)
    _doan_tieng(db, run, "seg_lanh", trang_thai_nan=VUA)
    _doan_tieng(db, run, "seg_hong", trang_thai_nan=CAN_SUA)

    tieng = _asset(db, run, pipeline.VOICE_SYNTHESIS, "asv/u1/tieng/seg_lanh.wav")
    ban_dung = _asset(db, run, pipeline.COMPOSE, "asv/u1/dung/ban.json")

    _advance(db, run)
    db.refresh(tieng)
    db.refresh(ban_dung)

    assert tieng.integrity == ASSET_OK, (
        "artifact cua CHINH giai doan duoc sua bi danh dau mat — luot chay lai "
        "se phai lam lai ca nhung doan con lanh")
    assert ban_dung.integrity == ASSET_MISSING, (
        "artifact HA NGUON phai bi vo hieu: no duoc dung tu mot ban tieng sap "
        "bi thay")
