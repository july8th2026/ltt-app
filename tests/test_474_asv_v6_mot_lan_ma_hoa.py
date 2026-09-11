"""ASV V6 pha 26 — Renderer fusion: MOT lan ma hoa cho moi bien doi diem anh.

🔑 **Menh de trung tam, va truoc pha 26 khong bai nao chot no:** khi CA BON bien
   doi diem anh cung bat — vung che, lop phu chu, logo, phu de — lenh ffmpeg van
   co dung **MOT** `-filter_complex`, **MOT** bo ma hoa hinh, **MOT** tep ra.

   Tung bien doi da co bai rieng (`test_457` vung, `test_466` lop phu + logo,
   `test_471` phu de). Nhung chung kiem tung cai MOT MINH — khong bai nao hoi
   dieu gi xay ra khi ca bon cung co mat. Mot lan sua sau them mot luot ffmpeg
   thu hai cho mot bien doi (cach doc tu nhien nhat cua `autosubvideo/burn.py`)
   se xanh o ca bon bai rieng — va video bi ma hoa lai HAI lan.

⭐ Khang dinh DUONG: moi mat xich phai CO MAT trong chuoi loc duy nhat. Mot bai
   chi dem "khong qua mot `-c:v`" se xanh khi ai do lang le bo mot bien doi di
   (`banh-coc-do-su-vang-mat-thi-xoa-cung-xanh`).

⛔ Khong chay ffmpeg. Bang chung may that — lenh nay CHAY, `returncode 0`, va
   benchmark bon bo ma hoa — o `bang_chung/bo_ma_hoa_20260911.json`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import (ban_dung, che_do_render as cdr, ket_xuat, logo,
                                  lop_phu, phu_de, vung_che)

GOC = Path(__file__).resolve().parents[1]
BANG_CHUNG = GOC / "docs/auto_scan_video_v6/bang_chung/bo_ma_hoa_20260911.json"

GOI = [{"start": 0.5, "end": 3.0, "text": "Phu de", "display_text": "Phu de",
        "line_count": 1, "scene_id": "s1", "index": 0}]

#: Mat xich cua tung bien doi trong chuoi loc. Doi mot bo loc (vd `boxblur` ->
#: `gblur`) thi sua o day — va do la mot quyet dinh can noi ra, khong phai im.
#:
#: ⚠️ Logo KHONG danh dau bang `overlay`: vung che CUNG dung `overlay` de dan
#:    manh lam mo tro lai (`[g0][m0]overlay`). Ban dau cua bai nay chon
#:    `overlay` va doi chung cua chinh no bat duoc — bo logo di ma `overlay`
#:    van con. Nhan luong `[lg0]` moi la dau hieu RIENG cua logo.
MAT_XICH = {"vung": "boxblur", "lop_phu": "drawtext", "logo": "[lg0]",
            "phu_de": "ass="}


def _ca_bon():
    return dict(
        vung=vung_che.chuan_hoa([{"x0": 0.1, "y0": 0.1, "x1": 0.3, "y1": 0.3,
                                  "loai": "lam_mo"}]),
        lop_phu=lop_phu.chuan_hoa([{"chu": "Dang ky kenh", "x": 0.1, "y": 0.8,
                                    "co_chu": 0.06, "mau": "trang",
                                    "vien": True}]),
        ds_logo=[logo.chuan_hoa_mot({"x": 0.8, "y": 0.05, "rong": 0.12,
                                     "khoa": "logo/a.png"})],
        phu_de=dict(phu_de.chuan_hoa({"che_do": "tu_dong", "kieu": "default"}),
                    su_kien=GOI),
    )


def _ban(**bien_doi):
    return ban_dung.dung(
        khoa_video="v/g.mp4", khoa_nen="n.wav", khoa_master="m.wav",
        ke_hoach={"doan": [{"ma": "s1", "dai_ms": 2000, "dat_tai_ms": 0,
                            "he_so_toc": 1.0}]},
        ban_ke_tieng={"doan": [{"ma": "s1", "khoa": "v/s1.wav"}]},
        phien_ban_ffmpeg="n8", tong_giay=4.0, che_do=cdr.CAT_MA_HOA_LAI,
        bo_ma_hoa="libx264", khoang_giu=[(0.0, 4.0)], preset="smart_localize",
        rong_khung=640, cao_khung=360, **bien_doi)


def _lenh(tmp_path, ban, bien_doi):
    duong_chu = lop_phu.viet_tep_chu(list(bien_doi.get("lop_phu") or ()), tmp_path)
    pd = bien_doi.get("phu_de")
    duong_ass = phu_de.viet_tep_ass(pd, (pd or {}).get("su_kien") or [], tmp_path,
                                    rong=640, cao=360) if pd else ""
    return ket_xuat.dung_lenh(
        ban, ffmpeg_bin="ffmpeg", duong_video="C:/t/g.mp4",
        duong_master="C:/t/m.wav", duong_lop=["C:/t/s0.wav"],
        duong_ra="C:/t/ra.mp4", bo_ma_hoa="libx264", duong_chu=duong_chu,
        duong_logo=["C:/t/logo.png"] * len(bien_doi.get("ds_logo") or ()),
        duong_ass=duong_ass)


# ══ 1. MOT lan ma hoa, voi CA BON bien doi ═════════════════════════════════

def test_ca_bon_bien_doi_nam_trong_MOT_filter_complex(tmp_path):
    bd = _ca_bon()
    ban = _ban(**bd)
    ban_dung.kiem(ban)
    cmd = _lenh(tmp_path, ban, bd)

    assert cmd.count("-filter_complex") == 1, cmd
    fc = cmd[cmd.index("-filter_complex") + 1]
    thieu = [ten for ten, mat in MAT_XICH.items() if mat not in fc]
    assert not thieu, f"bien doi vang mat khoi chuoi loc duy nhat: {thieu}"


def test_ca_bon_bien_doi_chi_MOT_bo_ma_hoa_hinh_va_MOT_tep_ra(tmp_path):
    """🔴 Hai `-c:v` hay hai tep ra la hai lan ma hoa — dung khoan no pha 26
       ton tai de tra, va dung thu `burn.burn()` se tao ra neu bi goi o day.
    """
    bd = _ca_bon()
    cmd = _lenh(tmp_path, _ban(**bd), bd)
    bo = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-c:v"]
    assert bo == ["libx264"], bo
    assert "copy" not in bo
    ra = [x for x in cmd if str(x).endswith(".mp4") and x != "C:/t/g.mp4"]
    assert ra == ["C:/t/ra.mp4"], ra


def test_phu_de_la_mat_xich_CUOI_tren_ca_logo_va_lop_phu(tmp_path):
    """⭐ Phu de la thu khach doc de HIEU; logo va lop phu la trang tri. Mot phu
       de bi logo de len la mot phu de khong doc duoc.
    """
    bd = _ca_bon()
    fc = _lenh(tmp_path, _ban(**bd), bd)
    fc = fc[fc.index("-filter_complex") + 1]
    vi_tri = {ten: fc.rindex(mat) for ten, mat in MAT_XICH.items()}
    assert vi_tri["phu_de"] == max(vi_tri.values()), vi_tri


@pytest.mark.parametrize("bo_di", sorted(MAT_XICH))
def test_bo_mot_bien_doi_thi_mat_xich_do_VANG_ma_van_mot_lan_ma_hoa(tmp_path, bo_di):
    """Doi chung: moi mat xich xuat hien VI bien doi cua no, khong phai vi mot
    ly do khac. Bo mot bien doi thi dung mat xich do bien mat.
    """
    bd = _ca_bon()
    bd.pop("ds_logo" if bo_di == "logo" else bo_di)
    cmd = _lenh(tmp_path, _ban(**bd), bd)
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert MAT_XICH[bo_di] not in fc
    assert cmd.count("-c:v") == 1


# ══ 2. Thu tu bo ma hoa khop PHEP DO ═════════════════════════════════════════

def _bc():
    return json.loads(BANG_CHUNG.read_text(encoding="utf-8"))


def test_bang_chung_ghi_nguong_TRUOC_va_nvenc_TUONG_DUONG():
    """🔑 Nguong chat luong duoc ghi TRUOC khi doc ket qua, va nam trong chinh
       tep bang chung — mot nguong dat sau khi nhin so la mot nguong ve quanh
       dich.
    """
    bc = _bc()
    assert bc["nguong_ghi_truoc"]["lech_ssim_toi_da"] == 0.010
    assert bc["phan_quyet"]["h264_nvenc"]["tuong_duong"] is True
    assert bc["ket_qua"]["libx264"]["trang_thai"] == "chay"


def test_thu_tu_uu_tien_PHAN_CUNG_truoc_duoc_phep_do_ung_ho():
    """⭐ Luat A (ghi truoc): giu phan cung truoc neu o 1080p bo phan cung chon
       tieu <= 0,5x CPU va <= 2,0x thoi gian cua libx264. Do: NVENC 0,21x CPU,
       0,67x thoi gian. Neu ai doi `UU_TIEN` dat libx264 len dau, bai nay do —
       va nguoi doi phai co mot phep do moi.
    """
    assert cdr.UU_TIEN[0] == "h264_nvenc"
    assert cdr.UU_TIEN[-1] == cdr.LUI_VE
    cpu = _bc()["gia_cpu_1080p"]
    assert cpu["h264_nvenc"]["cpu"] <= 0.5 * cpu["libx264"]["cpu"]
    assert cpu["h264_nvenc"]["wall"] <= 2.0 * cpu["libx264"]["wall"]


def test_moi_bo_da_do_moi_lenh_chi_MOT_c_v():
    for bo, v in _bc()["ket_qua"].items():
        if v.get("trang_thai") == "chay":
            assert v["so_co_c_v_trong_lenh"] == 1, bo
