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
import sqlalchemy as sa

from apps.auto_scan_video import features, jobs, pipeline, su_dung, sua_chua
from apps.auto_scan_video.tables import (ASSET_MISSING, ASSET_OK,
                                         ITEM_INVALIDATED, ITEM_SUCCEEDED,
                                         RUN_DONE, RUN_ERROR, RUN_RUNNING,
                                         STAGE_FAILED_TERMINAL,
                                         STAGE_SUCCEEDED, AsvAsset, AsvRun,
                                         AsvStage, AsvWorkItem)
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

    ⚠️ **`render` mang san mot `.mp4` trong `outputs.khoa_asset` (N-57, 25/09).**
       Bai nay do vong SUA — RUN_DONE o day phai noi "vong sua da xu ly xong",
       khong phai "co hien vat de giao". Thieu dong nay, moi bai `RUN_DONE`
       trong tep se roi vao cong `co_hien_vat_giao_duoc` moi them o `jobs.py`
       va bao `error` vi mot ly do KHAC han ly do bai dang kiem. Cong do co
       phep kiem rieng o `test_483_asv_v7_may_trang_thai_giao_hang_rong.py`.
    """
    run = AsvRun(owner_id=owner, source_key="asv/u1/nguon/x.mp4",
                 settings={}, credit_held=0, status=RUN_RUNNING)
    db.add(run)
    db.flush()
    for g in pipeline.CHUOI:
        outputs = None
        if g.ten == pipeline.RENDER:
            outputs = {"khoa_asset": [f"asv/{owner}/{run.id}/long-tieng.mp4"]}
        db.add(AsvStage(run_id=run.id, owner_id=owner, stage=g.ten,
                        status=STAGE_SUCCEEDED, fingerprint="", outputs=outputs))
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
    # van khong vua. Worker THAT se render lai va sinh mp4 moi (N-57: thieu
    # dong nay se giat vao cong `co_hien_vat_giao_duoc` vi mot ly do KHAC han
    # ly do bai nay dang kiem — xem ghi chu o `_run_da_chay_het`).
    for s in features.cac_giai_doan(db, run):
        s.status = STAGE_SUCCEEDED
        if s.stage == pipeline.RENDER:
            s.outputs = {"khoa_asset": [f"asv/{run.owner_id}/{run.id}/long-tieng.mp4"]}
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


# ══════════════════════════════════════════════════════════════════════════════
#  Moi noi: hai duong ghi cua CUNG mot bang phai co CUNG mot rao
# ══════════════════════════════════════════════════════════════════════════════

def test_mo_lai_don_vi_KHONG_ghi_de_mot_ban_ghi_vua_doi(db):
    """🔴 **Duong ghi cua toi di vong qua chinh lop bao ve cua ham anh em.**

    `su_dung.danh_dau_xong` dung `UPDATE ... WHERE revision = :r` roi nem
    `XungDotDonVi` khi `rowcount != 1`, va `tables.py` noi ro cot `revision` sinh
    ra de lam gi: *"bien mot cuoc dua thanh mot xung dot NHIN THAY DUOC thay vi
    mot ban ghi de"*.

    Ban dau `mo_lai_don_vi` — viet ngay canh no — lai la mot phep gan ORM tran.

    ⛔ Cuoc dua that: mot tien trinh khac vua doc lai doan nay va `danh_dau_xong`
       no voi van tay moi; ta cam mot ban doc CU roi ghi `invalidated` de len.
       **Mot lan doc lai da tra tien bien mat, va khong ai thay.**

    ⭐ Khong phep kiem nao truoc do bat duoc, vi ca hai duong ghi deu xanh RIENG
       LE. Cho hong la **moi noi** — thu duy nhat biet ca hai ben.
    """
    import platform_core.db as dbmod

    run = _run_da_chay_het(db)
    _doan_tieng(db, run, "seg_dua", trang_thai_nan=CAN_SUA)
    db.commit()

    # ⛔ **Phai dung HAI phien, va ban dau toi da lam sai cho nay.**
    #
    #    Ban dau toi tang `revision` ngay tren `db` roi goi ham. Bai xanh — vi
    #    ham DOC LAI truoc khi ghi, nen no thay dung con so vua doi va `UPDATE`
    #    khop. Do khong phai mot cuoc dua; do la mot lan doc va mot lan ghi
    #    trong cung mot dong thoi gian.
    #
    # ⭐ Cuoc dua that can mot ban doc CU con song trong identity map cua phien
    #    nay, trong khi phien KHAC da ghi de duoi CSDL. Luc do `select` tra ve
    #    doi tuong da nap (SQLAlchemy khong ghi de thuoc tinh da nap), nen `rev`
    #    la so CU va `UPDATE ... WHERE revision = rev` khop **khong dong nao**.
    it = features.don_vi_theo_khoa(db, run.id, pipeline.VOICE_SYNTHESIS,
                                   "seg_dua")
    assert it is not None and int(it.revision) >= 1

    khac = next(dbmod.get_session())
    try:
        khac.execute(sa.update(AsvWorkItem)
                     .where(AsvWorkItem.id == it.id)
                     .values(revision=int(it.revision) + 5))
        khac.commit()
    finally:
        khac.close()

    with pytest.raises(su_dung.XungDotDonVi):
        su_dung.mo_lai_don_vi(db, run, stage=pipeline.VOICE_SYNTHESIS,
                              item_key="seg_dua")


def test_don_vi_bi_TRANH_CHAP_khong_giet_ca_vong_sua(db, monkeypatch):
    """⚠️ Va mot xung dot o MOT don vi khong duoc lam hong ca lan chay.

    Nhung don vi khac van sua duoc; don vi nay se hien lai o ban ghi "con lai"
    neu no van hong. Bai nay chot rang ban va tren khong doi mot cuoc dua tam
    thoi thanh mot lan chay hong.
    """
    run = _run_da_chay_het(db)
    _doan_tieng(db, run, "seg_a", trang_thai_nan=CAN_SUA)
    _doan_tieng(db, run, "seg_b", trang_thai_nan=CAN_SUA)

    that = su_dung.mo_lai_don_vi

    # ⚠️ Chu ky phai BAM theo `su_dung.mo_lai_don_vi`. `y_canh` them 25/09
    #    (noi LY DO bi che vao luot dich lai) da lam ban gia nay do bang
    #    `TypeError` o `jobs.py:344` — mot thong diep KHONG tro vao cho that.
    def gia(db_, run_, *, stage, item_key, y_canh=None):
        if item_key == "seg_a":
            raise su_dung.XungDotDonVi("tien trinh khac dang cham")
        return that(db_, run_, stage=stage, item_key=item_key, y_canh=y_canh)

    monkeypatch.setattr(su_dung, "mo_lai_don_vi", gia)

    kq = _advance(db, run)
    assert kq.get("sua_chua"), "mot don vi tranh chap da giet ca vong sua"
    assert features.don_vi_theo_khoa(
        db, run.id, pipeline.VOICE_SYNTHESIS, "seg_b").status == ITEM_INVALIDATED


# =============================================================================
#  S5  QC bang AI la NGUON KHIEM KHUYET THU HAI — va no phai nhap chung MOT ke
#      hoach voi bac thang nan, khong phai chay mot vong rieng
# =============================================================================

def _doan_dich(db, run, ma: str, *, chu: str = "cau tieng Viet"):
    """Mot doan DA DICH — don vi viec o `content_process`.

    Khong goi `su_dung.ghi`: `giai_doan_noi_dung` tinh tien theo LO nhung chot
    theo DOAN, nen o truc doan chi co `danh_dau_xong`. Bai kiem di dung duong
    do; dung tay se dung mot hinh dang san pham khong bao gio tao ra.
    """
    su_dung.danh_dau_xong(db, run, stage=pipeline.CONTENT_PROCESS,
                          item_key=ma, fingerprint="vt",
                          outputs={"chu": chu})
    db.flush()


def _phan_quyet_qc_ai(db, run, phan: list[dict]):
    """Dat phan quyet QC ngu nghia vao dung cho san pham dat no: `stage.outputs`.

    Day la giao dien THAT giua hai nua: `giai_doan_qc_ai.chay` tra ve
    `tom_tat`, `thi_hanh` do `tom_tat` vao `stage.outputs`, roi
    `jobs._qc_ngu_nghia` doc lai tu do. Bai kiem dat vao dung o do — khong goi
    `lap_ke_hoach` truc tiep — nen no do CA duong day, ke ca cho noi.
    """
    st = db.execute(sa.select(AsvStage).where(
        AsvStage.run_id == run.id,
        AsvStage.stage == pipeline.QC_AI)).scalar_one()
    khong_dat = [p for p in phan if not p.get("dat", True)]
    st.outputs = {"qc_ai_bat": True, "so_muc": len(phan),
                  "so_co_phan_quyet": len(phan),
                  "so_khong_dat": len(khong_dat),
                  "qc_ai_khong_dat": khong_dat}
    db.flush()


def test_QC_AI_TAT_thi_lan_chay_van_giao_hang(db):
    """Chot mac dinh: `LTT_ASV_QC_AI` chua bat thi khong co gi doi.

    Giai doan van chay va van `succeeded`, chi la `outputs` khong mang phan
    quyet nao. Neu bai nay do, viec them mot giai doan MAC DINH TAT da lam moi
    lan chay binh thuong di qua mot nhanh khong ai yeu cau.
    """
    run = _run_da_chay_het(db)
    _doan_tieng(db, run, "seg_0001", trang_thai_nan=VUA)
    st = db.execute(sa.select(AsvStage).where(
        AsvStage.run_id == run.id,
        AsvStage.stage == pipeline.QC_AI)).scalar_one()
    st.outputs = {"qc_ai_bat": False, "ly_do": "LTT_ASV_QC_AI chua dat '1'"}
    db.flush()

    kq = _advance(db, run)
    assert kq["status"] == RUN_DONE
    assert "sua_chua" not in kq


def test_moi_phan_quyet_DAT_thi_khong_sinh_viec_sua(db):
    """QC da chay va noi "khong sao" phai khac han QC chua chay bao gio o CHI PHI,
    nhung giong nhau o KET QUA: khong sua gi.

    Bai nay chan mot ban doc sai hien nhien — coi "co phan quyet" la "co loi".
    Mot ban nhu the se tra tien dich lai toan bo moi lan bat QC len.
    """
    run = _run_da_chay_het(db)
    _doan_tieng(db, run, "seg_0001", trang_thai_nan=VUA)
    _phan_quyet_qc_ai(db, run, [
        {"ma": "seg_0001", "dat": True, "muc": "", "ly_do": "", "loi": []},
        {"ma": "seg_0002", "dat": True, "muc": "", "ly_do": "", "loi": []},
    ])

    kq = _advance(db, run)
    assert kq["status"] == RUN_DONE, (
        "moi doan deu DAT ma van sinh viec sua — QC bang AI dang tu tao viec "
        "cho chinh no")
    assert "sua_chua" not in kq


def test_doan_DICH_SAI_lam_CONTENT_PROCESS_va_ha_nguon_chay_lai(db):
    """Duong chinh cua S5: mot ban dich lech y phai duoc DICH LAI.

    Doc lai bao nhieu lan cung ra cung mot y sai, nen diem sua la
    `content_process` — som hon `voice_synthesis` han mot buoc.
    """
    run = _run_da_chay_het(db)
    _doan_tieng(db, run, "seg_0001", trang_thai_nan=VUA)
    _doan_tieng(db, run, "seg_0007", trang_thai_nan=VUA)
    _doan_dich(db, run, "seg_0001")
    _doan_dich(db, run, "seg_0007")
    _phan_quyet_qc_ai(db, run, [
        {"ma": "seg_0001", "dat": True, "muc": "", "ly_do": "", "loi": []},
        {"ma": "seg_0007", "dat": False, "muc": "nang",
         "ly_do": "bo mat menh de dieu kien",
         "nguon": "If it rains, the match is off.",
         "dich": "Tran dau bi huy."},
    ])

    kq = _advance(db, run)

    assert kq["status"] != RUN_DONE, (
        "lan chay co mot doan bi bao dich sai ma van giao hang")
    dat_lai = set(kq.get("sua_chua") or ())
    assert pipeline.CONTENT_PROCESS in dat_lai, (
        "`dich_sai` phai sua o `content_process`")
    for ten in (pipeline.VOICE_SYNTHESIS, pipeline.TIMING_ALIGN,
                pipeline.COMPOSE, pipeline.RENDER, pipeline.QC):
        assert ten in dat_lai, f"{ten} phai bi vo hieu theo `content_process`"

    # 🔑 Va CHI doan bi bao sai moi bi mo lai — day moi la "pham vi nho nhat
    #    an toan". Dat lai mot GIAI DOAN ma mo lai MOI don vi cua no la dich
    #    lai ca phim de sua mot cau.
    assert features.don_vi_theo_khoa(
        db, run.id, pipeline.CONTENT_PROCESS,
        "seg_0007").status == ITEM_INVALIDATED
    assert features.don_vi_theo_khoa(
        db, run.id, pipeline.CONTENT_PROCESS,
        "seg_0001").status == ITEM_SUCCEEDED, (
        "doan DAT bi mo lai — vong sua dang tra tien dich lai mot cau dung")


def test_DICH_SAI_va_KHONG_VUA_cung_mot_doan_thi_sua_o_cho_SOM_HON(db):
    """Hai NGUON khiem khuyet, MOT doan, MOT ke hoach.

    Day la ly do `lap_ke_hoach` nhan ca bon nguon vao cung mot ham thay vi moi
    nguon chay mot vong. Neu `seg_0007` vua bi bao doc khong vua khe (sua o
    `voice_synthesis`) vua bi bao dich sai (sua o `content_process`), sua o
    `voice_synthesis` la vo ich: doc lai mot cau dich sai van ra cau dich sai.

    Neu hai nguon chay hai vong rieng, lan chay se sua o `voice_synthesis`
    truoc, tieu mot vong, roi moi phat hien phai lui ve `content_process`. Bai
    nay chot rang khong co cai vong phi pham do.
    """
    run = _run_da_chay_het(db)
    _doan_tieng(db, run, "seg_0007", trang_thai_nan=CAN_SUA)
    _doan_dich(db, run, "seg_0007")
    _phan_quyet_qc_ai(db, run, [
        {"ma": "seg_0007", "dat": False, "muc": "nang", "ly_do": "lech y",
         "nguon": "src", "dich": "dich"},
    ])

    kq = _advance(db, run)
    dat_lai = set(kq.get("sua_chua") or ())

    assert pipeline.CONTENT_PROCESS in dat_lai, (
        "phai lui ve cho som nhat sua duoc doan nay")
    # `voice_synthesis` VAN bi dat lai — nhung vi no la HA NGUON cua
    # `content_process`, khong phai vi no la diem sua. Phan biet hai dieu do
    # bang don vi viec: don vi bi mo lai phai nam o `content_process`.
    assert features.don_vi_theo_khoa(
        db, run.id, pipeline.CONTENT_PROCESS,
        "seg_0007").status == ITEM_INVALIDATED
    assert features.don_vi_theo_khoa(
        db, run.id, pipeline.VOICE_SYNTHESIS,
        "seg_0007").status == ITEM_SUCCEEDED, (
        "doan bi mo lai o CA HAI cho — tuc hai nguon da chay hai vong rieng "
        "thay vi nhap thanh mot ke hoach, va lan doc lai se bi vut di ngay "
        "sau khi `content_process` sinh cau moi")


# =============================================================================
#  S6  CHO NOI giua hai nua — va no la cho mot dot bien di qua duoc
# =============================================================================
#
# Cac bai o S5 dat phan quyet vao `stage.outputs` BANG TAY. Chung do dung nua
# thu hai (vong sua doc gi), nhung khong do duoc nua thu nhat: giai doan co
# THAT SU ghi phan quyet vao do khong.
#
# Do duoc bang dot bien: go `qc_ai_khong_dat` khoi `tom_tat` cua giai doan thi
# ca 15 bai tren VAN XANH — trong khi san pham da lang le thoi sua moi khiem
# khuyet dich thuat. Bai duoi day dong dung cho do, va no khong duoc gia dinh
# TEN cua khoa: no chay `chay()` that roi hoi `jobs._qc_ngu_nghia` that.

class _KhoGia:
    """Kho toi thieu — chi can `open` va `put` cho duong nay."""

    def __init__(self, noi_dung: bytes):
        self._noi_dung = noi_dung
        self.da_ghi: dict[str, bytes] = {}

    def open(self, khoa):
        import io as _io
        return _io.BytesIO(self._noi_dung)

    def put(self, khoa, f, content_type=None):
        self.da_ghi[khoa] = f.read()


def test_GIAI_DOAN_ghi_phan_quyet_vao_dung_cho_VONG_SUA_doc(db, monkeypatch):
    """🔑 Noi hai nua bang mot bai duy nhat, khong bang mot ten khoa go hai lan.

    ⭐ Bai nay KHONG viet ra ten `qc_ai_khong_dat`. No lay `tom_tat` that ma
       `giai_doan_qc_ai.chay` tra ve, do vao `stage.outputs` dung cach
       `thi_hanh` do, roi hoi `jobs._qc_ngu_nghia` — ham THAT ma vong sua dung.
       Doi ten khoa o ca hai ben van xanh (dung), go no o mot ben la do (dung).
    """
    from apps.auto_scan_video import ai, giai_doan_qc_ai

    run = _run_da_chay_het(db)
    ban_dich = {"muc": [
        {"ma": "seg_0001", "goc": "The match is on.", "chu": "Tran dau dien ra."},
        {"ma": "seg_0007", "goc": "If it rains, the match is off.",
         "chu": "Tran dau bi huy."},
    ]}
    kho = _KhoGia(json.dumps(ban_dich).encode("utf-8"))

    st_cp = db.execute(sa.select(AsvStage).where(
        AsvStage.run_id == run.id,
        AsvStage.stage == pipeline.CONTENT_PROCESS)).scalar_one()
    st_cp.outputs = {"khoa_asset": ["asv/u1/staging/long_tieng.json"]}
    db.flush()

    monkeypatch.setenv(giai_doan_qc_ai.BIEN_BAT, "1")

    def goi_gia(db_, run_, thao_tac, loi_nhac, **kw):
        # Phan hoi dung khuon loi nhac doi: mot bang `doan` theo ma.
        # ⚠️ Khuon V2: model LIET KE LOI kem muc + doan trich, khong phan
        #    true/false. `doan` phai co that trong cau nguon hoac cau dich —
        #    `qc_ai._loc_loi` loai loi khong trich duoc doan.
        return {"noi_dung": json.dumps({"doan": {
            "seg_0001": {"loi": []},
            "seg_0007": {"loi": [{"loai": "bo_sot", "muc": "nang",
                                  "doan": "If it rains",
                                  "ly_do": "bo mat menh de dieu kien"}]},
        }})}

    monkeypatch.setattr(ai, "goi_tinh_tien", goi_gia)

    ra = giai_doan_qc_ai.chay(db, kho, run=run)

    # Do vao `stage.outputs` DUNG CACH `thi_hanh` do (`thi_hanh.py`): chi
    # `tom_tat` di qua, cac khoa mo dau bang `_` bi giu lai trong `thi_hanh`.
    st = db.execute(sa.select(AsvStage).where(
        AsvStage.run_id == run.id,
        AsvStage.stage == pipeline.QC_AI)).scalar_one()
    st.outputs = {"stage": pipeline.QC_AI, "khoa_asset": [],
                  **(ra.get("tom_tat") or {})}
    db.flush()

    theo_ten = {g.stage: g for g in features.cac_giai_doan(db, run)}
    thay = jobs._qc_ngu_nghia(theo_ten)

    assert [d["ma"] for d in thay] == ["seg_0007"], (
        "vong sua khong nhan duoc phan quyet ma giai doan vua sinh ra — "
        f"nhan: {thay}")
    assert thay[0]["nguon"] and thay[0]["dich"], (
        "phan quyet khong mang cau nguon/cau dich, nen bao cao noi 'seg_0007 "
        "sai' ma khong noi SAI CAI GI — khong ai kiem lai duoc ben chu quan")

    # Va di het duong: phan quyet do phai thanh mot viec sua o `content_process`.
    ke = sua_chua.lap_ke_hoach(qc_ngu_nghia=thay, vong=0)
    assert sua_chua.gon_theo_don_vi(ke) == {"seg_0007": "content_process"}

# =============================================================================
#  S7  Giai doan QC AI: cong TAT, va mot lo hong khong duoc lam hong ca lan chay
# =============================================================================

def _don_qc_ai(db, run, *, so_muc: int) -> list[dict]:
    """Dung san canh de `giai_doan_qc_ai.chay` co ban dich de doc."""
    st_cp = db.execute(sa.select(AsvStage).where(
        AsvStage.run_id == run.id,
        AsvStage.stage == pipeline.CONTENT_PROCESS)).scalar_one()
    st_cp.outputs = {"khoa_asset": ["asv/u1/staging/long_tieng.json"]}
    db.flush()
    return [{"ma": f"seg_{i:04d}", "goc": f"src {i}", "chu": f"dich {i}"}
            for i in range(so_muc)]


def test_QC_AI_TAT_thi_KHONG_goi_model_va_van_thanh_cong(db, monkeypatch):
    """⛔ Cong tat phai chan o cho TRUOC khi tieu tien, khong phai loc ket qua sau.

    Va giai doan van tra ve binh thuong: bo qua han mot giai doan se lam
    `len(da_xong) != len(CHUOI)` va lan chay khong bao gio ve `done`.
    """
    from apps.auto_scan_video import ai, giai_doan_qc_ai

    run = _run_da_chay_het(db)
    monkeypatch.delenv(giai_doan_qc_ai.BIEN_BAT, raising=False)

    def khong_duoc_goi(*a, **kw):
        raise AssertionError("QC AI dang TAT ma van goi model — dang tieu tien "
                             "cua nguoi van hanh cho mot thu chua ai bat")

    monkeypatch.setattr(ai, "goi_tinh_tien", khong_duoc_goi)

    kho = _KhoGia(b"")
    ra = giai_doan_qc_ai.chay(db, kho, run=run)

    assert ra["tom_tat"]["qc_ai_bat"] is False
    assert ra["tom_tat"].get("ly_do"), (
        "giai doan xanh ma khong noi VI SAO no trong — khong phan biet duoc "
        "'da soat, khong co loi' voi 'chua soat lan nao'")

    # 🔑 VAN ghi bao cao du khong soat gi. `test_403` doi moi giai doan
    #    ket thuc bang mot asset ref that; va quan trong hon, ly do "chua soat"
    #    phai nam trong chuoi BANG CHUNG duoc giao, khong chi trong mot cot CSDL.
    #    Sau khi lan chay ket thuc, `stage.outputs` tra loi duoc cau "da soat
    #    chua" — nhung artifact la thu di theo san pham toi tay nguoi doi soat.
    assert len(ra["phan"]) == 1, (
        "QC dang TAT ma giai doan khong de lai gi — sau lan chay khong ai "
        "doi chieu duoc no da chay hay chua")
    (khoa,) = list(kho.da_ghi)
    bc = json.loads(kho.da_ghi[khoa].decode("utf-8"))
    assert bc["qc_ai_bat"] is False and bc["ly_do"]
    assert bc["ngu_nghia"] == []

    # Va vong sua khong duoc doc ra khiem khuyet nao tu mot lan khong soat.
    st = db.execute(sa.select(AsvStage).where(
        AsvStage.run_id == run.id,
        AsvStage.stage == pipeline.QC_AI)).scalar_one()
    st.outputs = {"stage": pipeline.QC_AI, **ra["tom_tat"]}
    db.flush()
    theo_ten = {g.stage: g for g in features.cac_giai_doan(db, run)}
    assert jobs._qc_ngu_nghia(theo_ten) == []


def test_mot_LO_hong_khong_lam_hong_ca_lan_chay(db, monkeypatch):
    """🔴 Mot lo thu hai hong khong duoc vut bo phan quyet cua lo thu nhat.

    Ba muoi doan la ba lo. Neu mot loi mang o lo giua giet ca giai doan, moi
    lan chay dai deu la mot vong quay xo so — va lan chay lai se tra tien cho
    CA ba lo.

    ⚠️ Va chieu nguoc lai cung duoc chot: lo hong KHONG duoc doc thanh "moi doan
       trong lo deu DAT". Im lang la khong co phan quyet, khong phai phan quyet
       tot. Do bang `so_co_phan_quyet` < `so_muc`.
    """
    from apps.auto_scan_video import ai, giai_doan_qc_ai

    run = _run_da_chay_het(db)
    muc = _don_qc_ai(db, run, so_muc=30)
    kho = _KhoGia(json.dumps({"muc": muc}).encode("utf-8"))
    monkeypatch.setenv(giai_doan_qc_ai.BIEN_BAT, "1")

    da_goi = {"n": 0}

    def goi_gia(db_, run_, thao_tac, loi_nhac, **kw):
        da_goi["n"] += 1
        if da_goi["n"] == 2:
            raise RuntimeError("mang dut giua chung")
        ma = kw.get("item_key")
        i = int(str(ma).split("_")[-1])
        dau = i * 10
        return {"noi_dung": json.dumps({"doan": {
            f"seg_{j:04d}": {"loi": [] if j != 5 else [
                {"loai": "lat_nghia", "muc": "nang", "doan": f"dich {j}",
                 "ly_do": "lech y"}]}
            for j in range(dau, dau + 10)}})}

    monkeypatch.setattr(ai, "goi_tinh_tien", goi_gia)

    ra = giai_doan_qc_ai.chay(db, kho, run=run)

    tt = ra["tom_tat"]
    assert da_goi["n"] == 3, "khong chay tiep sau lo hong"
    assert tt["so_lo"] == 3 and tt["so_muc"] == 30
    assert tt["so_co_phan_quyet"] == 20, (
        f"co {tt['so_co_phan_quyet']} phan quyet — lo hong phai de lai mot LO "
        "TRONG, khong duoc dem thanh 10 doan DAT")
    assert [d["ma"] for d in tt["qc_ai_khong_dat"]] == ["seg_0005"], (
        "khiem khuyet cua lo con song bi mat theo lo hong")
    assert ra["phan"], "khong ghi artifact bao cao"


def test_lo_MO_HO_khong_sinh_viec_sua(db, monkeypatch):
    """`AiMoHo` = mat ket noi SAU khi gui: khong biet model da chay chua.

    ⛔ Khong duoc thu lai mu va khong duoc doan. Lo do khong co phan quyet, va
       khong co phan quyet nghia la khong sinh viec sua — im lang khong duoc
       doc thanh "co loi".
    """
    from apps.auto_scan_video import ai, giai_doan_qc_ai

    run = _run_da_chay_het(db)
    muc = _don_qc_ai(db, run, so_muc=5)
    kho = _KhoGia(json.dumps({"muc": muc}).encode("utf-8"))
    monkeypatch.setenv(giai_doan_qc_ai.BIEN_BAT, "1")

    def goi_gia(*a, **kw):
        raise ai.AiMoHo("mat ket noi sau khi gui")

    monkeypatch.setattr(ai, "goi_tinh_tien", goi_gia)

    ra = giai_doan_qc_ai.chay(db, kho, run=run)
    tt = ra["tom_tat"]
    assert tt["so_co_phan_quyet"] == 0
    assert tt["qc_ai_khong_dat"] == [], (
        "mot lo mo ho bi doc thanh khiem khuyet — se tra tien dich lai mot cau "
        "chua ai noi la sai")

