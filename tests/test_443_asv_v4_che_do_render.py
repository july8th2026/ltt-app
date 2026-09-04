"""Pha 17 — hai duong render, va cai gi quyet dinh duong nao.

Nam nhom:

  A. Chon duong    — preset quyet dinh, khong phai du lieu
  B. Loi hua       — preset giu hinh KHONG BAO GIO ma hoa lai, va co cong cuoi
  C. Cat-noi       — dung thu tu, dung khoang, khong dinh toi tieng
  D. Bo ma hoa     — GPU chi khi DUOC CAP; duong lui duoc KHAI
  E. Tai lap duoc  — ban dung mot minh mo ta du mot lan render
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from apps.auto_scan_video import che_do_render as cdr, hop_dong_v4


# ══════════════════════════════════════════════════════════════════════════════
#  A. Chon duong
# ══════════════════════════════════════════════════════════════════════════════

def test_preset_quyet_dinh_cach_render():
    assert cdr.che_do_cho(hop_dong_v4.PRESET_GIU_HINH) == cdr.SAO_CHEP
    assert cdr.che_do_cho(hop_dong_v4.PRESET_CAT_THONG_MINH) == cdr.CAT_MA_HOA_LAI


def test_preset_khong_hop_le_bi_TU_CHOI():
    with pytest.raises(cdr.CheDoError):
        cdr.che_do_cho("preset khong co that")


def test_preset_CAT_van_ma_hoa_lai_KE_CA_khi_khong_cat_canh_nao():
    """⛔ Suy che do tu DU LIEU (so canh bi cat) thay vi tu KHAI BAO la mo duong
    cho hai lan chay cung mot preset di hai duong khac nhau.

    Va o day suy tu du lieu con **sai**: mot ban bien tap giu tat ca canh van
    phai ma hoa lai, vi ranh cat van khong roi vao keyframe.
    """
    assert cdr.che_do_cho(hop_dong_v4.PRESET_CAT_THONG_MINH) == cdr.CAT_MA_HOA_LAI


# ══════════════════════════════════════════════════════════════════════════════
#  B. Loi hua cua preset giu hinh, va cong cuoi
# ══════════════════════════════════════════════════════════════════════════════

def _ban_toi_thieu(cach, *, preset="", bo="", khoang=None):
    return {
        "schema": 1, "phien_ban": 1, "preset": preset,
        "hinh": {"khoa": "v", "che_do": "copy", "cach_render": cach,
                 "bo_ma_hoa": bo, "khoang_giu": khoang or []},
        "tieng": {"master": {"khoa": "m"}, "nen": {"khoa": "n"}, "lop": [],
                  "tan_so": 48000, "so_kenh": 2},
        "ra": {"container": "mp4", "codec_tieng": "aac", "bitrate_tieng": "192k",
               "faststart": True, "thoi_luong_giay": 10.0},
        "cong_cu": {"ffmpeg": "x"},
    }


def _lenh(ban):
    from apps.auto_scan_video import ket_xuat

    return ket_xuat.dung_lenh(ban, ffmpeg_bin="ffmpeg", duong_video="/t/v.mp4",
                              duong_master="/t/m.wav", duong_lop=[],
                              duong_ra="/t/o.mp4", tien_do=False)


def test_ban_dung_khai_GIU_HINH_ma_xin_MA_HOA_LAI_thi_hong_o_CONG_CUOI():
    """🔴 Menh de trung tam cua nhom B, va `test_427` da doi truoc khi co no.

    Truoc pha 17, trinh render co mot chot VO DIEU KIEN: tu choi moi che do hinh
    khac `copy`. Pha 17 phai noi no ra vi preset CAT buoc phai ma hoa lai — nhung
    cach noi SAI la xoa han chot: khi do preset giu hinh mat bao ve **im lang**,
    va mot ngay nao do mot khach chon "giu nguyen hinh anh" nhan ve mot ban da ma
    hoa lai.
    """
    from apps.auto_scan_video import ket_xuat

    ban = _ban_toi_thieu(cdr.CAT_MA_HOA_LAI,
                         preset=hop_dong_v4.PRESET_GIU_HINH,
                         bo="libx264", khoang=[[0.0, 5.0]])
    with pytest.raises(ket_xuat.KetXuatError, match="preset"):
        _lenh(ban)


def test_preset_GIU_HINH_ra_lenh_SAO_CHEP_khong_bo_ma_hoa_nao():
    cmd = _lenh(_ban_toi_thieu(cdr.SAO_CHEP,
                               preset=hop_dong_v4.PRESET_GIU_HINH))
    assert "copy" in cmd
    assert "-filter_complex" not in cmd
    for bo in cdr.THAM_SO:
        assert bo not in cmd


def test_cach_render_khong_co_that_bi_TU_CHOI():
    from apps.auto_scan_video import ket_xuat

    with pytest.raises(ket_xuat.KetXuatError):
        _lenh(_ban_toi_thieu("phep_thuat"))


# ══════════════════════════════════════════════════════════════════════════════
#  C. Cat-noi
# ══════════════════════════════════════════════════════════════════════════════

def test_cat_noi_giu_DUNG_THU_TU_cac_khoang():
    """⛔ Sap xep lai la dung lai canh phim."""
    loc = cdr.loc_cat_noi([(30.0, 40.0), (0.0, 10.0)])
    assert loc.index("start=30.000000") < loc.index("start=0.000000")
    assert "concat=n=2" in loc


def test_cat_noi_KHONG_dung_toi_luong_tieng():
    """⛔ Ban phoi am da duoc dung theo dung nhung khoang nay va da chuan am
    luong MOT lan. Cho no di qua `concat` lan nua la tron hai quyet dinh am
    thanh o hai cho, va cai thu hai se thang mot cach im lang."""
    loc = cdr.loc_cat_noi([(0.0, 5.0), (10.0, 20.0)])
    assert ":a=0" in loc
    assert "[0:a]" not in loc
    assert "amix" not in loc


def test_khoang_rong_hoac_nguoc_bi_TU_CHOI():
    with pytest.raises(cdr.CheDoError):
        cdr.loc_cat_noi([(5.0, 5.0)])
    with pytest.raises(cdr.CheDoError):
        cdr.loc_cat_noi([(9.0, 2.0)])
    with pytest.raises(cdr.CheDoError):
        cdr.loc_cat_noi([])


def test_setpts_dat_lai_moc_cho_MOI_khoang():
    """Thieu `setpts=PTS-STARTPTS` thi khoang thu hai giu nguyen moc goc cua no,
    va `concat` chen mot khoang trong dai bang phan da cat — dung cai ta vua bo
    cong ra de xoa."""
    loc = cdr.loc_cat_noi([(0.0, 5.0), (10.0, 20.0)])
    assert loc.count("setpts=PTS-STARTPTS") == 2


# ══════════════════════════════════════════════════════════════════════════════
#  D. Bo ma hoa
# ══════════════════════════════════════════════════════════════════════════════

def test_KHONG_duoc_cap_GPU_thi_dung_CPU():
    """⭐ Khong phai mot lan that bai — la mot **chinh sach duoc khai**. Nen tang
    co the tu choi cap GPU vi card dang ban, va khi do CPU la duong dung."""
    assert cdr.chon_bo_ma_hoa(cho_phep_gpu=False, do_duoc="h264_nvenc") == cdr.LUI_VE


def test_duoc_cap_GPU_va_CO_bo_ma_hoa_thi_dung_no():
    assert cdr.chon_bo_ma_hoa(cho_phep_gpu=True, do_duoc="h264_nvenc") == "h264_nvenc"


def test_bo_ma_hoa_khong_khai_thi_LUI_VE_CPU_chu_khong_dung_bua():
    """⛔ Mot ten bo ma hoa la khong biet den ma van duoc truyen thang cho ffmpeg
    la mot lan render hong o phut thu muoi, sau khi da chiem suat."""
    assert cdr.chon_bo_ma_hoa(cho_phep_gpu=True, do_duoc="h264_bia_dat") == cdr.LUI_VE
    assert cdr.chon_bo_ma_hoa(cho_phep_gpu=True, do_duoc="") == cdr.LUI_VE


def test_chi_bo_PHAN_CUNG_moi_chiem_suat_GPU():
    assert cdr.dung_gpu("h264_nvenc")
    assert not cdr.dung_gpu(cdr.LUI_VE)


def test_moi_bo_ma_hoa_deu_co_tham_so_da_khai():
    for bo in cdr.UU_TIEN:
        assert cdr.tham_so(bo), f"{bo} khong co tham so"
    with pytest.raises(cdr.CheDoError):
        cdr.tham_so("khong-co-that")


def test_NVENC_dung_cq28_chu_khong_phai_23():
    """⛔ `cq=23` cho ra tep **lon gap doi** ma mat thuong khong phan biet duoc
    (SSIM 0,99795 vs 0,99519) — tuc tra tien bang dung luong dia va bang thong
    cho mot thu khong ai thay. Xem bang do o dau `che_do_render.py`."""
    assert "28" in cdr.tham_so("h264_nvenc")
    assert "23" not in cdr.tham_so("h264_nvenc")


def test_duong_lui_LUON_o_cuoi_va_LUON_co_mat():
    assert cdr.UU_TIEN[-1] == cdr.LUI_VE
    assert cdr.LUI_VE in cdr.THAM_SO


# ══════════════════════════════════════════════════════════════════════════════
#  E. Tai lap duoc, va KHONG goi model
# ══════════════════════════════════════════════════════════════════════════════

def test_van_tay_doi_theo_BO_MA_HOA():
    """⛔ Doi tu `libx264` sang `h264_nvenc` cho ra mot tep khac — cung noi dung,
    khac byte. Dung lai tep cu tu cache la giao mot thu khong phai ket qua cua
    cau hinh hien tai."""
    kh = [(0.0, 5.0)]
    a = cdr.van_tay_che_do(che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264", khoang=kh)
    b = cdr.van_tay_che_do(che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="h264_nvenc", khoang=kh)
    assert a != b


def test_van_tay_doi_theo_KHOANG_GIU():
    a = cdr.van_tay_che_do(che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264",
                           khoang=[(0.0, 5.0)])
    b = cdr.van_tay_che_do(che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264",
                           khoang=[(0.0, 6.0)])
    assert a != b


def test_ban_dung_MANG_THEO_preset_va_khoang_giu():
    """Muc 7: ban dung mot minh + cac artifact phai tai lap duoc lan render."""
    from apps.auto_scan_video import ban_dung

    ban = ban_dung.dung(
        khoa_video="v", khoa_nen="n", khoa_master="m",
        ke_hoach={"doan": [], "tong_ms": 10_000},
        ban_ke_tieng={"doan": []}, phien_ban_ffmpeg="ff", tong_giay=10.0,
        che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264",
        khoang_giu=[(0.0, 4.0), (6.0, 10.0)],
        preset=hop_dong_v4.PRESET_CAT_THONG_MINH)
    assert ban["preset"] == hop_dong_v4.PRESET_CAT_THONG_MINH
    assert ban["hinh"]["cach_render"] == cdr.CAT_MA_HOA_LAI
    assert ban["hinh"]["khoang_giu"] == [[0.0, 4.0], [6.0, 10.0]]
    assert ban["tieng"]["master"]["khoa"] == "m"


def test_ban_dung_CAT_ma_khong_khai_khoang_nao_thi_NEM():
    from apps.auto_scan_video import ban_dung

    with pytest.raises(ban_dung.BanDungError):
        ban_dung.dung(khoa_video="v", khoa_nen="n", khoa_master="m",
                      ke_hoach={"doan": [], "tong_ms": 10_000},
                      ban_ke_tieng={"doan": []}, phien_ban_ffmpeg="ff",
                      tong_giay=10.0, che_do=cdr.CAT_MA_HOA_LAI,
                      bo_ma_hoa="libx264", khoang_giu=[])


def test_ban_dung_TU_CHOI_cach_render_khong_co_that():
    """🔴 Lo hong ma kiem dot bien tim ra: moi phep kiem cua toi deu truyen mot
    cach render HOP LE vao `ban_dung.dung`, nen viec no co kiem hay khong khong
    do duoc.

    ⛔ Ban dung la thu duoc LUU LAI. Mot cach render khong co that lot vao day se
       nam trong kho cua khach cho toi khi co nguoi render lai tu no — va luc do
       loi hien ra o mot cho khong lien quan gi toi luc no duoc tao ra.
    """
    from apps.auto_scan_video import ban_dung

    with pytest.raises(ban_dung.BanDungError):
        ban_dung.dung(khoa_video="v", khoa_nen="n", khoa_master="m",
                      ke_hoach={"doan": [], "tong_ms": 10_000},
                      ban_ke_tieng={"doan": []}, phien_ban_ffmpeg="ff",
                      tong_giay=10.0, che_do="phep_thuat")


def test_van_tay_BO_MA_HOA_khong_dua_vao_mot_truong_duy_nhat():
    """⚠️ Kiem dot bien chi ra `bo` va `tham_so` trong van tay **noi cung mot
    dieu**: xoa mot cai thi cai kia van lam van tay doi.

    Do khong phai mot loi — mot van tay co du phong thi kho hong hon. Nhung noi
    "phep kiem bat duoc viec xoa `bo`" thi sai; cai bat duoc la `tham_so`. Phep
    kiem nay chot dieu THAT SU quan trong: hai bo ma hoa khac nhau **khong bao
    gio** cho cung mot van tay, bat ke truong nao mang thong tin do.
    """
    kh = [(0.0, 5.0)]
    vt = {bo: cdr.van_tay_che_do(che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa=bo,
                                 khoang=kh)
          for bo in cdr.UU_TIEN}
    assert len(set(vt.values())) == len(vt), (
        "hai bo ma hoa cho cung mot van tay: %s" % vt)


def test_che_do_render_KHONG_goi_model():
    """⛔ Pha 17 cam: "Renderer may not call LLM/VLM/ASR/Voice"."""
    cay = ast.parse(Path(cdr.__file__).read_text(encoding="utf-8"))
    for n in ast.walk(cay):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            ten = (getattr(n, "module", "") or "") + " ".join(a.name for a in n.names)
            for cam in ("dieu_phoi", "giong_noi", "long_tieng", "hieu_canh"):
                assert cam not in ten, f"che_do_render nhap {cam}"
        if isinstance(n, ast.Call):
            goi = (n.func.attr if isinstance(n.func, ast.Attribute)
                   else getattr(n.func, "id", ""))
            assert goi not in ("goi_tinh_tien", "doc_mot_doan", "chep_loi")
