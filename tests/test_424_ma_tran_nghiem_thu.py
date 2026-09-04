"""Pha 21 — MA TRAN NGHIEM THU: G1–G14 anh xa toi BANG CHUNG chay duoc.

## Vi sao ma tran nay la MA chu khong phai mot bang trong tai lieu

`MVP_ACCEPTANCE_GATES.md` liet ke muoi bon cong, va cach hien nhien de "danh gia
tung cong" la viet mot bang trong bao cao pha 21 roi danh dau. Bang do sai ngay
lan doi ten mot phep kiem dau tien, va no sai **im lang**: khong ai chay mot
bang.

⇒ O day moi cong tro toi ten phep kiem THAT. Hai phep kiem cuoi tep doi chieu
  hai chieu voi bo test da thu thap duoc:

    * moi phep kiem duoc vien dan phai TON TAI  -> khong vien dan mot bang chung
      da bien mat;
    * moi cong phai co it nhat mot bang chung   -> khong de mot cong trong.

⭐ Va mot cong duoc danh dau **CHUA CO BANG CHUNG** thi phai noi ra bang mot muc
   `PENDING`, khong duoc de trong roi hy vong khong ai dem.

## Gioi han cua phep nghiem thu nay, noi truoc

⛔ Ba loai bang chung KHONG the co tren may nay, va chung duoc ghi la `PENDING`
   chu khong duoc goi la dat:

   1. **Provider that.** LLM dich va may sinh tieng deu bi thay bang ban gia
      trong bo do. Hanh vi loi (429, auth, mo ho) duoc kiem o cap PHAN LOAI
      (`test_418`) chu khong bang mot lan goi that bi tu choi.
   2. **GPU that.** Chuoi chay tren CPU o day. Dinh tuyen lan va truyen moi
      truong card duoc kiem, viec **chay tren card** thi khong.
   3. **Video that cua khach.** Moi khuon la 1–3 giay do `testsrc` sinh ra.
"""
from __future__ import annotations

import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parent

#: Muoi bon cong -> bang chung. Moi muc la `("<tep>", "<ten ham>")`.
#:
#: ⚠️ Chi ghi ten HAM, khong ghi node id day du: mot phep kiem tham so hoa
#:    (`@parametrize`) co nhieu node nhung mot ten ham, va chot node id se lam
#:    ma tran do moi lan them mot tham so.
MA_TRAN: dict[str, list[tuple[str, str]]] = {
    # ── G1 Pham vi & tuong thich nen tang ──────────────────────────────────
    "G1": [
        ("test_402_asv_mach_doc_gia.py", "test_thu_tu_giai_doan_do_MAY_CHU_quyet_khong_phai_client"),
        ("test_421_asv_tach_khoi_di_san.py", "test_khong_duong_nao_toi_module_di_san"),
        ("test_423_asv_giao_dien.py", "test_KHONG_co_node_keo_tha_hay_do_thi"),
        ("test_190_public_api_coverage.py", "test_the_disposition_document_lists_every_app"),
    ],
    # ── G2 Nguon chan ly thi hanh ──────────────────────────────────────────
    "G2": [
        ("test_402_asv_mach_doc_gia.py", "test_run_chay_het_CHIN_giai_doan_va_ve_done"),
        ("test_402_asv_mach_doc_gia.py", "test_thu_tu_giai_doan_do_MAY_CHU_quyet_khong_phai_client"),
        ("test_402_asv_mach_doc_gia.py", "test_lan_ffmpeg_KHONG_nhat_duoc_job_GPU"),
        ("test_421_asv_tach_khoi_di_san.py", "test_KHONG_vong_lap_worker_rieng_trong_app"),
        ("test_417_asv_vo_hieu_ha_nguon.py", "test_moi_giai_doan_chi_co_MOT_dong_du_da_thu_lai"),
    ],
    # ── G3 Tinh tien dung ──────────────────────────────────────────────────
    "G3": [
        ("test_402_asv_mach_doc_gia.py", "test_KHONG_job_giai_doan_nao_giu_credit"),
        ("test_402_asv_mach_doc_gia.py", "test_quyet_toan_MOT_LAN_va_hoan_phan_khong_dung"),
        ("test_402_asv_mach_doc_gia.py", "test_tran_chi_chan_truoc_khi_tieu_vuot_hold"),
        ("test_419_asv_tiem_loi.py", "test_giu_cho_ve_0_o_moi_ket_cuc"),
        ("test_419_asv_tiem_loi.py", "test_job_con_KHONG_giu_them_credit_nao"),
        ("test_419_asv_tiem_loi.py", "test_quyet_toan_KHONG_chay_hai_lan"),
        ("test_417_asv_vo_hieu_ha_nguon.py", "test_thu_lai_KHONG_giu_them_mot_khoan_credit_nao"),
    ],
    # ── G4 Cach ly nguoi dung / thong tin dang nhap ────────────────────────
    "G4": [
        ("test_402_asv_mach_doc_gia.py", "test_nguoi_khac_KHONG_doc_duoc_run_du_biet_id"),
        ("test_404_pham_vi_khoa_api.py", "test_khoa_rieng_cua_A_KHONG_den_tay_B"),
        ("test_404_pham_vi_khoa_api.py", "test_pool_nen_tang_KHONG_BAO_GIO_cham_khoa_rieng"),
        ("test_419_asv_tiem_loi.py", "test_hai_nguoi_dung_chay_dong_thoi_khong_lan_du_lieu"),
        ("test_423_asv_giao_dien.py", "test_nguoi_khac_KHONG_xem_duoc_lan_chay_cua_toi"),
        ("test_423_asv_giao_dien.py", "test_nguoi_khac_KHONG_tai_duoc_ket_qua"),
        ("test_423_asv_giao_dien.py", "test_nguoi_khac_KHONG_huy_duoc_lan_chay_cua_toi"),
    ],
    # ── G5 Tai nguyen ──────────────────────────────────────────────────────
    "G5": [
        ("test_402_asv_mach_doc_gia.py", "test_lan_ffmpeg_KHONG_nhat_duoc_job_GPU"),
        ("test_419_asv_tiem_loi.py", "test_KHONG_giai_doan_nao_tu_chon_card_GPU"),
        ("test_419_asv_tiem_loi.py", "test_giai_doan_GPU_xin_moi_truong_qua_ctx_chu_khong_tu_dat"),
        ("test_419_asv_tiem_loi.py", "test_RENDER_khong_TU_GIANH_GPU_va_khong_dat_cho_mot_tai_nguyen_nao"),
        ("test_421_asv_tach_khoi_di_san.py", "test_KHONG_khoa_GPU_di_san"),
    ],
    # ── G6 Ben vung / bat bien lap ─────────────────────────────────────────
    "G6": [
        ("test_403_asv_vong_doi_artifact.py", "test_lineage_noi_giai_doan_voi_thuong_nguon_cua_no"),
        ("test_419_asv_tiem_loi.py", "test_artifact_bien_mat_thi_CACHE_khong_dung_lai_no"),
        ("test_419_asv_tiem_loi.py", "test_checkpoint_HONG_bi_phat_hien_chu_khong_duoc_dung_tiep"),
        ("test_416_asv_van_tay_engine.py", "test_doi_phien_ban_engine_thi_van_tay_PHAI_doi"),
        ("test_417_asv_vo_hieu_ha_nguon.py", "test_advance_TU_DAT_LAI_giai_doan_lech_thay_vi_ket_thuc"),
        ("test_415_asv_cong_thoat_render.py", "test_render_hong_KHONG_de_lai_ket_qua_dang_do"),
    ],
    # ── G7 An toan tac dung phu cua provider ───────────────────────────────
    "G7": [
        ("test_418_asv_phan_loai_loi.py", "test_mo_ho_thanh_AmbiguousProviderError_KHONG_BAO_GIO_tu_dong_thu_lai"),
        ("test_418_asv_phan_loai_loi.py", "test_loi_nguoi_dung_thanh_LoiNguoiGoi_KHONG_thu_lai"),
        ("test_418_asv_phan_loai_loi.py", "test_may_ban_thanh_BanError_XEP_LAI_chu_khong_dot_mot_lan_thu"),
        ("test_418_asv_phan_loai_loi.py", "test_moi_lop_ngoai_le_cua_app_deu_duoc_phan_loai"),
        ("test_419_asv_tiem_loi.py", "test_video_KHONG_CO_TIENG_hong_ngay_va_khong_thu_lai"),
    ],
    # ── G8 Media / chep loi / giong / thoi gian ────────────────────────────
    "G8": [
        ("test_405_asv_nhap_media.py", "test_video_KHONG_co_tieng_bi_tu_choi"),
        ("test_407_asv_chep_loi.py", "test_ban_ghi_dai_hon_ban_tieng_bi_TU_CHOI"),
        ("test_409_asv_giong_noi.py", "test_MOT_tep_cho_MOI_doan"),
        ("test_410_asv_thoi_gian.py", "test_ngan_sach_keo_toi_luc_doan_SAU_bat_dau"),
        ("test_422_asv_parity_engine.py", "test_LECH_CO_Y_5_tran_troi_la_CUA_TA"),
    ],
    # ── G9 Dung ban / render / QC ──────────────────────────────────────────
    "G9": [
        ("test_411_asv_ban_dung.py", "test_composer_KHONG_sinh_media"),
        ("test_415_asv_cong_thoat_render.py", "test_RENDER_that_su_sinh_ra_mot_mp4_PHAT_DUOC"),
        ("test_415_asv_cong_thoat_render.py", "test_render_lai_KHONG_danh_thuc_mot_giai_doan_thuong_nguon_nao"),
        ("test_420_asv_qc.py", "test_QC_hong_thi_RUN_KHONG_ve_done"),
        ("test_420_asv_qc.py", "test_moi_dung_sai_deu_NO_duoc"),
        ("test_420_asv_qc.py", "test_lan_chay_that_QUA_duoc_cong"),
    ],
    # ── G10 Huy va phuc hoi ────────────────────────────────────────────────
    "G10": [
        ("test_419_asv_tiem_loi.py", "test_huy_TRUOC_khi_job_con_chay"),
        ("test_419_asv_tiem_loi.py", "test_huy_GIUA_CHUNG_khong_bi_mot_job_ve_dich_muon_ghi_de"),
        ("test_417_asv_vo_hieu_ha_nguon.py", "test_sau_khi_huy_thi_chay_tiep_KHONG_lam_run_song_lai"),
        ("test_417_asv_vo_hieu_ha_nguon.py", "test_huy_KHONG_de_lai_job_con_dang_song"),
        ("test_414_asv_ket_xuat.py", "test_huy_giua_chung_thi_GIET_tien_trinh_va_khong_de_lai_ket_qua"),
    ],
    # ── G11 An toan di tru ─────────────────────────────────────────────────
    "G11": [
        ("test_421_asv_tach_khoi_di_san.py", "test_do_thi_goi_KHONG_RONG"),
        ("test_421_asv_tach_khoi_di_san.py", "test_khong_duong_nao_toi_goi_dieu_phoi_ngoai"),
        ("test_421_asv_tach_khoi_di_san.py", "test_moi_tien_trinh_con_deu_la_CONG_CU_da_khai"),
        ("test_422_asv_parity_engine.py", "test_giu_chinh_sach_ma_hoa_cua_ban_di_san"),
        ("test_422_asv_parity_engine.py", "test_LECH_CO_Y_6_ban_nen_giu_44k1_cua_htdemucs_chu_khong_48k"),
    ],
    # ── G12 Quan sat ───────────────────────────────────────────────────────
    "G12": [
        ("test_420_asv_qc.py", "test_dong_thoi_gian_dung_tu_du_lieu_ben_khong_tu_log"),
        ("test_420_asv_qc.py", "test_ky_su_ho_tro_dinh_vi_duoc_giai_doan_hong_MA_KHONG_doc_thu_muc_tam"),
        ("test_420_asv_qc.py", "test_ban_cho_KHACH_khong_lo_chi_tiet_van_hanh"),
        ("test_420_asv_qc.py", "test_mac_dinh_la_ban_CHO_KHACH"),
        ("test_414_asv_ket_xuat.py", "test_ho_so_chan_doan_khong_lo_duong_dan"),
    ],
    # ── G13 Dung duoc (MVP) ────────────────────────────────────────────────
    "G13": [
        ("test_423_asv_giao_dien.py", "test_trang_khach_KHONG_lo_chi_tiet_ky_thuat"),
        ("test_423_asv_giao_dien.py", "test_chin_buoc_hien_bang_NHAN_TIENG_VIET"),
        ("test_423_asv_giao_dien.py", "test_MOI_route_ghi_deu_doi_CSRF"),
        ("test_423_asv_giao_dien.py", "test_lich_su_chi_hien_lan_chay_CUA_MINH"),
        # ⚠️ Nguon THU HAI, doc lap voi tep giao dien: neu ca G13 chi duoc
        #    chung minh boi `test_423` thi no dang do chinh tep do.
        ("test_420_asv_qc.py", "test_ban_cho_KHACH_khong_lo_chi_tiet_van_hanh"),
    ],
    # ── G14 Bang chung ─────────────────────────────────────────────────────
    "G14": [
        ("test_400_asv_bat_bien_thi_hanh.py", "test_worker_chi_nhat_job_cua_app_ma_no_du_nang_luc"),
        ("test_402_asv_mach_doc_gia.py", "test_run_chay_het_CHIN_giai_doan_va_ve_done"),
        ("test_415_asv_cong_thoat_render.py", "test_RENDER_that_su_sinh_ra_mot_mp4_PHAT_DUOC"),
        ("test_424_ma_tran_nghiem_thu.py", "test_moi_cong_deu_co_it_nhat_mot_bang_chung"),
    ],
}

#: Cong CHUA co bang chung day du, kem ly do. ⛔ Mot cong o day KHONG duoc goi
#: la dat, va bao cao pha 21 phai liet ke chung nhu blocker.
#:
#: ⭐ Danh sach nay RONG hom nay khong co nghia moi thu da duoc chung minh —
#:    xem `THIEU_BANG_CHUNG_NGOAI` ngay duoi, la thu that su con thieu.
CHUA_DU_BANG_CHUNG: dict[str, str] = {}

#: Bang chung KHONG the lay tren may nay. Day la danh sach that cua pha 21.
THIEU_BANG_CHUNG_NGOAI = {
    "G7": ("Provider THAT chua bi tu choi lan nao. 429 / auth / quota duoc kiem "
           "o cap PHAN LOAI (`test_418`), khong bang mot lan goi that. Can mot "
           "khoa provider that va mot lan bi gioi han that."),
    "G5": ("GPU THAT chua chay. Dinh tuyen lan va truyen `ctx.gpu_env` / "
           "`ctx.gpu_uuid` deu duoc kiem, viec **chay tren card** thi khong — "
           "ca chuoi chay tren CPU o day."),
    "G8": ("Video THAT cua khach chua chay. Moi khuon la 1-3 giay do `testsrc` "
           "sinh ra, khong co giong nguoi that, khong co nhac nen that. Dung "
           "sai thoi gian (T7/T11) chua duoc do tren loi noi that."),
    "G10": ("Worker chua bi GIET that (RISK-17-01). Ngat duoc mo phong bang "
            "ngoai le va bang giet tien trinh con, khong bang mot `SIGKILL` "
            "giua mot transaction."),
}


def _cac_ten_ham_trong(tep: str) -> set[str]:
    import ast

    p = GOC / tep
    if not p.is_file():
        return set()
    cay = ast.parse(p.read_text(encoding="utf-8"))
    ra = set()
    for nut in ast.walk(cay):
        if isinstance(nut, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ra.add(nut.name)
    return ra


@pytest.mark.parametrize("cong", sorted(MA_TRAN))
def test_moi_cong_deu_co_it_nhat_mot_bang_chung(cong):
    """⛔ Mot cong khong co bang chung phai NOI RA, khong duoc de trong."""
    if cong in CHUA_DU_BANG_CHUNG:
        pytest.fail(f"{cong} khai la chua du bang chung: "
                    f"{CHUA_DU_BANG_CHUNG[cong]}")
    assert MA_TRAN[cong], f"{cong} khong co bang chung nao"


def test_MOI_bang_chung_duoc_vien_dan_deu_TON_TAI():
    """🔑 Phep kiem giu cho ma tran nay khoi muc.

    Doi ten mot phep kiem ma quen sua ma tran se lam do NGAY, thay vi de mot
    bao cao nghiem thu vien dan mot bang chung khong con ton tai.
    """
    thieu: list[str] = []
    for cong, muc in MA_TRAN.items():
        for tep, ham in muc:
            if ham not in _cac_ten_ham_trong(tep):
                thieu.append(f"{cong}: {tep}::{ham}")
    assert thieu == [], (
        "ma tran nghiem thu vien dan phep kiem KHONG TON TAI:\n  "
        + "\n  ".join(thieu))


def test_ma_tran_phu_DU_muoi_bon_cong():
    """Chot theo TAP HOP. Them mot cong vao `MVP_ACCEPTANCE_GATES.md` ma quen
    dua vao day se lam do."""
    assert set(MA_TRAN) == {f"G{i}" for i in range(1, 15)}


def test_bang_chung_KHONG_tap_trung_vao_mot_tep():
    """⚠️ Neu ca mot cong chi duoc chung minh boi mot tep, thi cong do dang do
    chinh tep do chu khong do he thong.

    Nguong thap co chu y: muc dich la bat truong hop mot cong co **mot** nguon
    bang chung duy nhat, khong phai ep phan bo deu.
    """
    yeu = {cong: sorted({t for t, _ in muc})
           for cong, muc in MA_TRAN.items()
           if len({t for t, _ in muc}) < 2}
    assert yeu == {}, f"cong chi co mot nguon bang chung: {yeu}"


def test_thieu_bang_chung_ngoai_duoc_GHI_RO_chu_khong_giau():
    """⭐ Pha 21 chi PASS neu moi cong quan trong co bang chung. Nhung "co bang
    chung" khong bang "da chay tren that", va gop hai thu do lam mot la cach mot
    ban MVP duoc goi la san sang trong khi chua ai chay no tren du lieu that.

    Danh sach nay ton tai de bao cao pha 21 khong the noi "tat ca deu dat".
    """
    assert THIEU_BANG_CHUNG_NGOAI, (
        "danh sach thieu-bang-chung RONG — neu that su khong con gi thieu thi "
        "phai co mot lan chay tren video that, GPU that va provider that de "
        "chung minh dieu do")
    for cong, ly_do in THIEU_BANG_CHUNG_NGOAI.items():
        assert cong in MA_TRAN, f"{cong} khong phai mot cong co that"
        assert len(ly_do) > 60, f"{cong}: ly do qua ngan de kiem chung"
