"""Pha V5 — vung che di HET duong: ban dung -> bo loc -> tep ra.

`docs/auto_scan_video_v5/` §17 doi mot control chi duoc goi la XONG khi chuoi
`saved -> engine executes it -> output visibly reflects it` khep kin. Tep nay la
nua sau cua chuoi do; nua dau (ve, kiem, luu) o `test_456` va `test_455`.

## Mot rang buoc VAT LY, khong phai mot chinh sach

🔴 Lam mo mot vung doi hoi mot BO LOC; mot bo loc doi hoi giai ma roi ma hoa
   lai. Duong `sao_chep` phat `-c:v copy` — khong co khung hinh nao ton tai
   trong bo nho de sua mot vung diem anh cua no.

⇒ Vung che chi phuc vu duoc o preset CAT. Ba tang cung chot dieu do: giao dien
  (an cong cu), `ban_dung.kiem` (nem), va tep nay (chot ca hai).
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import che_do_render as cdr


def _hop(**them):
    ra = {"loai": "lam_mo", "y0": 0.60, "y1": 0.95, "x0": 0.10, "x1": 0.90}
    ra.update(them)
    return ra


KHOANG = [(0.0, 2.0), (2.5, 4.0)]


# ══════════════════════════════════════════════════════════════════════════════
#  A. Chuoi bo loc — hinh dang
# ══════════════════════════════════════════════════════════════════════════════

def test_khong_co_vung_thi_chuoi_loc_KHONG_doi():
    """Duong khong vung phai giong het truoc V5 — khong tra them mot dong nao."""
    assert cdr.loc_cat_noi(KHOANG) == cdr.loc_cat_noi(KHOANG, vung=())
    assert "boxblur" not in cdr.loc_cat_noi(KHOANG)


def test_co_vung_thi_co_boxblur_va_van_ket_thuc_o_nhan_ra():
    loc = cdr.loc_cat_noi(KHOANG, vung=[_hop()])
    assert "boxblur" in loc
    # ⭐ `[ra]` la giao uoc voi `ket_xuat.dung_lenh` (`-map "[ra]"`). Doi nhan o
    #    day ma quen sua ben kia thi ffmpeg bao "khong co luong nao de map" —
    #    mot loi o GIUA lan render, sau khi da ton demucs va ASR.
    assert loc.rstrip().endswith("[ra]")


def test_nhieu_vung_thi_NOI_TIEP_nhau_chu_khong_de_len_nhau():
    """Hai vung phai ra hai lop overlay noi tiep. Neu ca hai cung doc mot nhan
    vao thi lop thu hai **xoa** ket qua cua lop thu nhat."""
    loc = cdr.loc_cat_noi(KHOANG, vung=[_hop(), _hop(y0=0.05, y1=0.20)])
    assert loc.count("boxblur") == 2
    assert "[o0]" in loc, "lop thu nhat khong duoc noi vao lop thu hai"


def test_crop_dung_iw_ih_con_overlay_dung_W_H():
    """🔴 Do that tren may nay: `overlay` **KHONG CO** bien `iw`/`ih`.

    Mot `overlay=trunc(iw*0.1/2)*2` lam ffmpeg nem *"Error when evaluating the
    expression ... for x"*, trong khi dung y het bieu thuc do trong `crop` thi
    chay. Hai bo loc, hai bo bien — va tai lieu khong dat chung canh nhau.

    ⭐ Chot ca hai chieu: thieu chieu thu hai thi mot lan "don dep cho nhat quan"
       se doi `W` thanh `iw` va lam vo lenh render.
    """
    loc = cdr.loc_cat_noi(KHOANG, vung=[_hop()])
    phan_crop = [x for x in loc.split(";") if "crop=" in x][0]
    phan_ovl = [x for x in loc.split(";") if "overlay=" in x][0]
    assert "iw*" in phan_crop and "ih*" in phan_crop
    assert "W*" in phan_ovl and "H*" in phan_ovl
    assert "iw*" not in phan_ovl and "ih*" not in phan_ovl


def test_kich_thuoc_va_vi_tri_deu_CHAN():
    """`yuv420p` lay mau 2x2, nen chieu le lam encoder tu choi khoi tao — va
    thong bao cua ffmpeg khi do khong nhac gi toi `crop`."""
    loc = cdr.loc_cat_noi(KHOANG, vung=[_hop()])
    phan_crop = [x for x in loc.split(";") if "crop=" in x][0]
    assert phan_crop.count("trunc(") == 4 and phan_crop.count("/2)*2") == 4


# ══════════════════════════════════════════════════════════════════════════════
#  B. Van tay — L4 cua `vung_che`
# ══════════════════════════════════════════════════════════════════════════════

def test_doi_VUNG_thi_van_tay_DOI():
    """🔴 Thieu phep kiem nay thi doi vung ma van tay khong doi ⇒ **phuc vu lai
    ket qua cu**. Dung cai bay `cache_artifact.py` cua he tham chieu goi ten:
    *"sot tham so = serve nham"*."""
    a = cdr.van_tay_che_do(che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264",
                           khoang=KHOANG, vung=[_hop()])
    b = cdr.van_tay_che_do(che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264",
                           khoang=KHOANG, vung=[_hop(y0=0.61)])
    khong = cdr.van_tay_che_do(che_do=cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264",
                               khoang=KHOANG)
    assert a != b, "doi toa do ma van tay khong doi"
    assert a != khong, "them vung ma van tay khong doi"


# ══════════════════════════════════════════════════════════════════════════════
#  C. Ban dung — chan duong khong thi hanh duoc
# ══════════════════════════════════════════════════════════════════════════════

def _ban_toi_thieu(che_do, vung):
    from apps.auto_scan_video import ban_dung
    return ban_dung.dung(
        khoa_video="v/1.mp4", khoa_nen="a/nen.wav", khoa_master="a/master.wav",
        ke_hoach={"doan": [], "tong_ms": 4000}, ban_ke_tieng={"doan": []},
        phien_ban_ffmpeg="n7.0", tong_giay=4.0, che_do=che_do,
        bo_ma_hoa="libx264" if che_do == cdr.CAT_MA_HOA_LAI else "",
        khoang_giu=KHOANG if che_do == cdr.CAT_MA_HOA_LAI else None,
        vung=vung)


def test_ban_dung_TU_CHOI_vung_o_duong_sao_chep():
    """⛔ Mot ban dung vua `sao_chep` vua co vung la mot ban dung **khong the thi
    hanh dung**. Lot qua day thi `ket_xuat` lang le bo qua vung va giao mot video
    khong che gi — khach tra tien cho mot thu khong xay ra."""
    from apps.auto_scan_video.ban_dung import BanDungError

    # ⭐ `dung()` goi `kiem()` o dong cuoi, nen mot ban dung khong thi hanh duoc
    #    **khong bao gio ton tai** — no chet ngay luc dung. Tot hon la de no ra
    #    doi roi moi bi mot phep kiem rieng bat.
    with pytest.raises(BanDungError):
        _ban_toi_thieu(cdr.SAO_CHEP, [_hop()])


def test_ban_dung_NHAN_vung_o_duong_cat():
    ban = _ban_toi_thieu(cdr.CAT_MA_HOA_LAI, [_hop()])
    assert ban["hinh"]["vung"] and ban["hinh"]["vung"][0]["loai"] == "lam_mo"


def test_ban_dung_LUON_co_khoa_vung_ke_ca_khi_rong():
    """Mot ban dung khong co khoa `vung` la ban dung SCHEMA CU — khac han mot
    ban dung co `vung: []`. Nguoi doc lai phai phan biet duoc hai thu do."""
    ban = _ban_toi_thieu(cdr.SAO_CHEP, None)
    assert ban["hinh"]["vung"] == []
    assert ban["schema"] >= 2


# ══════════════════════════════════════════════════════════════════════════════
#  D. Lenh ffmpeg that
# ══════════════════════════════════════════════════════════════════════════════

def test_lenh_render_MANG_bo_loc_vung():
    """Doi chung o tang lenh: vung co that di vao `-filter_complex`."""
    from apps.auto_scan_video import ket_xuat

    ban = _ban_toi_thieu(cdr.CAT_MA_HOA_LAI, [_hop()])
    cmd = ket_xuat.dung_lenh(ban, ffmpeg_bin="ffmpeg", duong_video="/tmp/v.mp4",
                             duong_master="/tmp/master.wav", duong_lop=[],
                             duong_ra="/tmp/ra.mp4")
    i = cmd.index("-filter_complex")
    assert "boxblur" in cmd[i + 1]
