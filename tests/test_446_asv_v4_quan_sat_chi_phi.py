"""Pha 20 — quan sat van hanh va giai thich duoc chi phi.

Bon nhom:

  A. Doi soat HAI CHIEU  — moi don vi tinh tien truy duoc, va nguoc lai
  B. Don vi viec         — "succeeded" khong noi duoc da lam bao nhieu viec
  C. Cho khach           — thay chi phi, KHONG thay ten giai doan noi bo
  D. Khong ro ri         — khong duong dan, khong ten may, khong chu so huu
"""
from __future__ import annotations

import json

from apps.auto_scan_video import pipeline, quan_sat, su_dung as sd

from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401
from tests.test_402_asv_mach_doc_gia import (asr_gia, db, dich_gia,  # noqa: F401
                                             giong_gia, kho_tam)


def _chay(db, kho_tam, tmp_path):
    from tests.test_402_asv_mach_doc_gia import _chay_het_hang_doi, _tao_run

    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()
    from apps.auto_scan_video.tables import AsvRun

    return db.get(AsvRun, run.id)


# ══════════════════════════════════════════════════════════════════════════════
#  A. Doi soat HAI CHIEU
# ══════════════════════════════════════════════════════════════════════════════

def test_moi_don_vi_TINH_TIEN_deu_truy_duoc_ve_so_cai(
        tmp_path, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """🔴 Cong thoat pha 20: "mot nguoi van hanh giai thich duoc MOI don vi da
    tinh tien tu bang chung ben vung"."""
    run = _chay(db, kho_tam, tmp_path)
    ds = quan_sat.doi_soat_nhanh(db, run)
    assert ds["khop"], (
        "don vi co tien ma khong co so cai: %s | so cai khong co don vi: %s"
        % (ds["don_vi_co_tien_khong_co_so_cai"], ds["so_cai_khong_co_don_vi"]))
    assert ds["so_don_vi"] > 0, "khong don vi nao duoc ghi — khong co gi de doi soat"


def _mo_coi(db, run, *, stage="gd", item_key="mo_coi", ma_dispatch="bia:1"):
    """Dung mot dong so cai KHONG con don vi viec — va dung cach no THAT SU xay ra.

    🔴 **Phep kiem dau tien cua toi dung sai cach, va do la mot phat hien.**

       Toi goi `su_dung.ghi(...)` voi mot `item_key` khong co that va cho rang no
       tao ra mot dong mo coi. Khong: `ghi` **tu mo don vi viec** (Phase 06 buoc
       hai thu di cung mot giao dich), nen mot dong mo coi **khong sinh ra duoc
       qua API**.

    ⭐ Nhung no van xay ra duoc — chi la bang duong khac: mot don vi bi XOA hay
       bi vo hieu trong khi dong so cai o lai. Do la truong hop that (don don
       dep, migration, mot ban va sua tay), va do la cai phep kiem phai dung.

    ⛔ Neu chi kiem duoc bang API thi phep kiem se noi "khong the xay ra" — trong
       khi thu no canh giu chinh la nhung duong KHONG di qua API.
    """
    from sqlalchemy import delete

    from apps.auto_scan_video.tables import AsvWorkItem

    sd.ghi(db, run, stage=stage, item_key=item_key,
           su_dung=sd.SuDung(nang_luc="x", app_chu="y", trang_thai=sd.DA_GIAO,
                             don_vi=sd.LUOT, so_luong=1.0, credit=5,
                             ma_dispatch=ma_dispatch))
    db.flush()
    db.execute(delete(AsvWorkItem).where(AsvWorkItem.run_id == run.id,
                                         AsvWorkItem.item_key == item_key))
    db.commit()


def test_doi_soat_bat_duoc_DON_VI_co_tien_ma_MAT_dong_so_cai(
        tmp_path, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """🔴 Chieu THU HAI cua phep doi soat, va kiem dot bien chi ra khong ai dung
    no.

    Trong duong chay binh thuong hai thu luon di cung nhau (Phase 06 buoc chung
    vao mot giao dich), nen chieu nay khong tu xuat hien. Nhung no la chieu **ton
    tien nhat**: mot don vi ghi `credit_actual > 0` ma khong con dong so cai nao
    la mot khoan da tru cua khach **khong con chung tu**.

    ⛔ Mot phep doi soat chi kiem duoc chieu de xay ra la mot phep doi soat de ngo
       dung chieu ma nguoi ta so nhat.
    """
    from sqlalchemy import delete

    from apps.auto_scan_video.tables import AsvUsage

    run = _chay(db, kho_tam, tmp_path)
    sd.ghi(db, run, stage="gd", item_key="mat_chung_tu",
           su_dung=sd.SuDung(nang_luc="x", app_chu="y", trang_thai=sd.DA_GIAO,
                             don_vi=sd.LUOT, so_luong=1.0, credit=7,
                             ma_dispatch="mat:1"))
    db.flush()
    db.execute(delete(AsvUsage).where(AsvUsage.run_id == run.id,
                                      AsvUsage.ma_dispatch == "mat:1"))
    db.commit()

    ds = quan_sat.doi_soat_nhanh(db, run)
    assert not ds["khop"], "don vi co tien ma mat chung tu van bao KHOP"
    assert any("mat_chung_tu" in x for x in ds["don_vi_co_tien_khong_co_so_cai"])


def test_doi_soat_bat_duoc_DONG_SO_CAI_khong_co_don_vi(
        tmp_path, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """⛔ Hai chieu, khong phai mot. Chi kiem mot chieu la de ngo dung nua kia
    ma minh khong nghi toi: mot dong so cai khong co don vi nghia la co viec da
    tinh tien ma khong ai ghi la da lam."""
    run = _chay(db, kho_tam, tmp_path)
    _mo_coi(db, run, item_key="khong_co_that")
    ds = quan_sat.doi_soat_nhanh(db, run)
    assert not ds["khop"]
    assert any("khong_co_that" in x for x in ds["so_cai_khong_co_don_vi"])


def test_doi_soat_KHONG_NEM_khi_lech(tmp_path, db, kho_tam, asr_gia, dich_gia,
                                     giong_gia):
    """⭐ `su_dung.doi_soat` nem khi lech — dung, no la mot RANG BUOC. Ham quan
    sat thi khong: mot man quan sat phai tra loi duoc **ca khi he thong dang
    hong**, va do la luc nguoi ta can no nhat."""
    run = _chay(db, kho_tam, tmp_path)
    _mo_coi(db, run, item_key="lech", ma_dispatch="bia:2")
    ds = quan_sat.doi_soat_nhanh(db, run)      # khong nem
    assert not ds["khop"]


def test_danh_sach_lech_bi_CAT_NGAN(tmp_path, db, kho_tam, asr_gia, dich_gia,
                                    giong_gia):
    """⛔ Mot man quan sat khong duoc bien thanh mot bai dai khi he thong hong."""
    run = _chay(db, kho_tam, tmp_path)
    for i in range(40):
        _mo_coi(db, run, item_key=f"bia_{i:03d}", ma_dispatch=f"bia:{i}")
    ds = quan_sat.doi_soat_nhanh(db, run)
    assert len(ds["so_cai_khong_co_don_vi"]) <= 20
    assert ds["so_dong_da_giao"] >= 40, "con so TONG van phai dung du danh sach bi cat"


# ══════════════════════════════════════════════════════════════════════════════
#  B. Don vi viec
# ══════════════════════════════════════════════════════════════════════════════

def test_dong_thoi_gian_NOI_bao_nhieu_viec_da_lam(
        tmp_path, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """🔑 Mot giai doan "succeeded" khong noi duoc **bao nhieu viec da lam that**.

    Hai lan chay cung ra "succeeded" nhung mot lan goi model 200 lan con lan kia
    goi 0 — va hoa don cua chung khac han nhau.
    """
    run = _chay(db, kho_tam, tmp_path)
    dtg = quan_sat.dong_thoi_gian(db, run, cho_van_hanh=True)
    co = [g for g in dtg["giai_doan"] if g.get("don_vi")]
    assert co, "khong giai doan nao bao cao don vi viec"
    for g in co:
        assert g["don_vi"]["tong"] >= g["don_vi"]["xong"]


def test_dem_don_vi_cua_giai_doan_KHONG_co_viec_thi_khong_hien(
        tmp_path, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """Mot khoi rong trong bao cao la nhieu; khong co viec thi khong noi gi."""
    run = _chay(db, kho_tam, tmp_path)
    d = quan_sat.dem_don_vi(db, run, pipeline.MEDIA_PREPARE)
    assert d["tong"] == 0
    dtg = quan_sat.dong_thoi_gian(db, run, cho_van_hanh=True)
    mp = next(g for g in dtg["giai_doan"] if g["giai_doan"] == pipeline.MEDIA_PREPARE)
    assert "don_vi" not in mp


def test_SO_KE_nam_cung_cho_voi_dong_thoi_gian(
        tmp_path, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """🔑 Truoc pha 20 hai thu nay o hai truy van khac nhau, va mot nguoi van hanh
    muon tra loi "vi sao lan chay nay ton bao nhieu" phai TU ghep chung — tuc tu
    lam mot phep noi ma khong ai kiem."""
    run = _chay(db, kho_tam, tmp_path)
    dtg = quan_sat.dong_thoi_gian(db, run, cho_van_hanh=True)
    assert "so_ke" in dtg and "doi_soat" in dtg
    assert dtg["so_ke"]["run_id"] == run.id


# ══════════════════════════════════════════════════════════════════════════════
#  C. Cho khach
# ══════════════════════════════════════════════════════════════════════════════

def test_khach_thay_TIEN_DO_va_CHI_PHI(tmp_path, db, kho_tam, asr_gia, dich_gia,
                                       giong_gia):
    run = _chay(db, kho_tam, tmp_path)
    t = quan_sat.tom_tat_cho_khach(db, run)
    assert t["so_buoc"] == len(pipeline.CHUOI)
    assert 0 <= t["phan_tram"] <= 100
    assert "credit_da_tinh" in t


def test_khach_KHONG_thay_ten_giai_doan_noi_bo(
        tmp_path, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """⛔ Ten giai doan la chi tiet ky thuat cua ta. Lo no ra bien moi lan doi ten
    mot giai doan thanh mot thay doi giao dien, va bien so do chuoi thanh thong
    tin cong khai."""
    run = _chay(db, kho_tam, tmp_path)
    van = json.dumps(quan_sat.tom_tat_cho_khach(db, run), ensure_ascii=False)
    for g in pipeline.CHUOI:
        assert g.ten not in van, f"lo ten giai doan noi bo: {g.ten}"


def test_khach_KHONG_thay_ten_app_chu(tmp_path, db, kho_tam, asr_gia, dich_gia,
                                      giong_gia):
    """⚠️ `app_chu` la ten noi bo cua nha cung cap nang luc — khong phai viec cua
    khach, va la mot manh cua ban do he thong.

    ## ⭐ 25/09/2026 — gia PHANG bo bang theo nang luc khoi HOA DON khach

    Bang `chi_phi_theo_nang_luc` (nam dong: long tieng · dich · viet loi thoai ·
    xem tung canh · ...) co ly do khi gia **cong don** theo tung nang luc. Gia
    phang tinh `10 credit x so phut video nguon`, nen mot bang nam dong cho mot con
    so phang la mot bang **noi doi ve cach tinh** — no goi y rang bo mot nang luc
    di se tra it hon.

    ⇒ Bai nay doi tu *"bang khong mang `app_chu`"* sang *"khach khong doc thay
      `app_chu` o BAT KY dau"* — cung menh de, ⛔ khong con phu thuoc vao mot bang
      da bien mat. Phan **do luong** theo nang luc VAN song o ban van hanh
      (`dong_thoi_gian(cho_van_hanh=True)["so_ke"]`) — xem `test_3900`.
    """
    run = _chay(db, kho_tam, tmp_path)
    t = quan_sat.tom_tat_cho_khach(db, run)
    assert "chi_phi_theo_nang_luc" not in t, "bang theo nang luc con o hoa don khach"

    van = json.dumps(t, ensure_ascii=False)
    assert "app_chu" not in van
    # ⛔ Va khong chi TEN khoa: ca cac GIA TRI `app_chu` that trong so cai.
    for d in sd.cac_dong(db, run):
        if d.app_chu:
            assert d.app_chu not in van, f"lo app_chu `{d.app_chu}` cho khach"


# ══════════════════════════════════════════════════════════════════════════════
#  D. Khong ro ri
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_cho_KHACH_khong_lo_duong_dan_hay_chu_so_huu(
        tmp_path, db, kho_tam, asr_gia, dich_gia, giong_gia):
    run = _chay(db, kho_tam, tmp_path)
    van = json.dumps(quan_sat.tom_tat_cho_khach(db, run), ensure_ascii=False)
    for cam in ("C:\\\\", "/Users/", "AppData", run.owner_id, "Temp"):
        assert cam not in van, f"lo `{cam}` cho khach"


def test_ban_cho_KHACH_khong_lo_van_tay_hay_job_id(
        tmp_path, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """⭐ Van tay va `job_id` la moc de truy vet noi bo. Chung khong bi mat, chung
    chi khong thuoc ve man cua khach."""
    run = _chay(db, kho_tam, tmp_path)
    t = quan_sat.tom_tat_cho_khach(db, run)
    van = json.dumps(t, ensure_ascii=False)
    assert "van_tay" not in van and "job_id" not in van

    # ... va o ban VAN HANH thi chung PHAI co.
    dtg = quan_sat.dong_thoi_gian(db, run, cho_van_hanh=True)
    assert any(g.get("van_tay") for g in dtg["giai_doan"])


def test_hai_nguoi_dung_KHONG_thay_so_ke_cua_nhau(
        tmp_path, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """Chot co lap: mot lan chay chi bao cao don vi va so cai CUA CHINH NO."""
    from tests.test_402_asv_mach_doc_gia import _chay_het_hang_doi, _tao_run

    a = _chay(db, kho_tam, tmp_path)
    b = _tao_run(db, owner="uB", kho=kho_tam, tmp_path=tmp_path / "b")
    _chay_het_hang_doi(db)
    db.expire_all()

    sk_a = sd.so_ke(db, a)
    assert sk_a["run_id"] == a.id
    dong_a = {d.run_id for d in sd.cac_dong(db, a)}
    assert dong_a <= {a.id}, "so cai cua lan chay nay lan sang lan chay khac"
    assert b.owner_id == "uB"
