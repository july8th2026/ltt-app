"""asv-final lan `bien-tap` — settings -> RenderManifest -> MOT `filter_complex`.

🔴 **Cap nhat gd2-diem-anh (25/09): khung/zoom/lat guong/dich mau/logo/lop_phu/
   phu-de-DOT da CHUYEN xuong GD2 (`giai_doan_hinh_anh.py`).** GD1 (`ban_dung`/
   `ket_xuat`) o day chi con `vung` (lam mo/dien nen) va `bien_tap["toc_do"]`.
   Bai nay chia lam HAI phia: phia 1 la GD1 con lai (con dung `ban_dung`/
   `ket_xuat`), phia 2 la GD2 moi nhan (dung `che_do_render.loc_cat_hai_dong`/
   `giai_doan_hinh_anh.dung_lenh`) — cung khang dinh DUONG voi `test_474`: moi
   chang bien tap phai CO MAT trong chuoi loc duy nhat, dung THU TU, voi dung
   MOT `-c:v`.

Khong chay ffmpeg. Engine that: `test_2062`, `test_2064`.
"""
from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import (ban_dung, che_do_render as cdr,
                                  giai_doan_hinh_anh as gdha, ket_xuat, logo,
                                  lop_phu, phu_de, qc, vung_che)

KE_HOACH = {"doan": [{"ma": "s1", "dai_ms": 2000, "dat_tai_ms": 4000,
                      "he_so_toc": 1.0, "ngan_sach_ms": 500, "troi_sau_ms": 0}]}


def _ban(bien_tap=None, **them):
    return ban_dung.dung(
        khoa_video="v/g.mp4", khoa_nen="n.wav", khoa_master="m.wav",
        ke_hoach=KE_HOACH, ban_ke_tieng={"doan": [{"ma": "s1", "khoa": "v/s1.wav"}]},
        phien_ban_ffmpeg="n8", tong_giay=8.0, che_do=cdr.CAT_MA_HOA_LAI,
        bo_ma_hoa="libx264", khoang_giu=[(0.0, 8.0)], preset="smart_localize",
        rong_khung=1280, cao_khung=720, bien_tap=bien_tap,
        # ⭐ Nhip NGUON — `ket_xuat` nhan voi `toc_do` de khai `-r`. Fixture phai
        #    khai no nhu production (`giai_doan_ban_dung` doc tu ho so
        #    `media_prepare`); thieu no thi lenh nhan mac dinh `auto` va noi dung
        #    lech 40 ms. 25 x 1,25 = 31,25.
        fps_nguon=them.pop("fps_nguon", 25.0), **them)


def _lenh(ban, **kw):
    return ket_xuat.dung_lenh(
        ban, ffmpeg_bin="ffmpeg", duong_video="C:/t/g.mp4",
        duong_master="C:/t/m.wav", duong_lop=["C:/t/s0.wav"],
        duong_ra="C:/t/ra.mp4", bo_ma_hoa="libx264", **kw)


def _fc(cmd):
    assert cmd.count("-filter_complex") == 1, cmd
    return cmd[cmd.index("-filter_complex") + 1]


# ══ 1. Ban dung GD1 — CHI con `vung` va `bien_tap["toc_do"]` ═════════════════

def test_khong_bien_tap_thi_ban_dung_KHONG_mang_khoa_moi():
    """Ban dung cu giu nguyen tung byte => van tay tep ra cua ho so cu khong doi."""
    h = _ban()["hinh"]
    assert "bien_tap" not in h and "khung_ra" not in h and "logo" not in h
    assert "lop_phu" not in h
    assert _ban()["ra"]["thoi_luong_giay"] == 8.0


def test_ban_dung_GD1_CHI_con_toc_do__khung_KHONG_con_hop_le():
    """`khung_ra` khong con duoc GD1 TINH — chi `toc_do` doi thoi luong ra."""
    ban = _ban({"toc_do": 1.25})
    assert "khung_ra" not in ban["hinh"]
    assert ban["ra"]["thoi_luong_giay"] == pytest.approx(6.4)
    # 🔴 `khung`/`zoom`/`cat_khung`/`lat_guong`/`dich_mau` da chuyen xuong GD2:
    #    mot ban dung GD1 con mang chung la mot hop dong noi doi (khong ai ve no
    #    len hinh o GD1 nua) — `_kiem_bien_tap` NEM.
    with pytest.raises(ban_dung.BanDungError, match="không thuộc về nó"):
        _ban({"toc_do": 1.25, "khung": {"ti_le": "9:16", "cach": "cat"}})


def test_kiem_chan_bien_tap_o_duong_sao_chep():
    ban = _ban({"toc_do": 1.25})
    ban["hinh"]["cach_render"] = cdr.SAO_CHEP
    with pytest.raises(ban_dung.BanDungError, match="biên tập lại hình"):
        ban_dung.kiem(ban)


# ══ 2a. GD1 — chuoi loc CHI con `vung`/`toc_do` ═══════════════════════════════

def test_khong_bien_tap_khong_vung_thi_GD1_REMUX__khong_ma_hoa_vo_ich():
    """🔴 gd2-diem-anh: preset cat ma GD1 KHONG con vung/toc_do thi REMUX, dung
    nhu preset giu hinh — logo/lop_phu/khung da chuyen xuong GD2 nen o day
    khong con gi de lam."""
    cmd = _lenh(_ban())
    assert "-filter_complex" not in cmd
    assert cmd[cmd.index("-c:v") + 1] == "copy"
    assert "-shortest" not in cmd


def test_co_vung_thi_GD1_VAN_ma_hoa_lai():
    vung = vung_che.chuan_hoa([{"x0": 0.1, "y0": 0.1, "x1": 0.3, "y1": 0.3,
                                "loai": "lam_mo"}])
    cmd = _lenh(_ban(vung=vung))
    fc = _fc(cmd)
    assert fc.startswith(
        "[0:v]trim=start=0.000000:end=8.000000,setpts=PTS-STARTPTS[v0];"
        "[v0]concat=n=1:v=1:a=0[noi]")
    assert "boxblur" in fc
    assert "-shortest" in cmd


def test_toc_do_hinh_va_tieng_CUNG_he_so_trong_MOT_do_thi():
    cmd = _lenh(_ban({"toc_do": 1.25}))
    fc = _fc(cmd)
    assert "setpts=PTS/1.2500[ra]" in fc and "[1:a]atempo=1.2500[a_ra]" in fc
    assert cmd[cmd.index("[a_ra]") - 1] == "-map" and "1:a:0" not in cmd
    # 🔴 `-fps_mode passthrough` -> `-r nguon x toc` (27/09, chu du an chi ra).
    #
    # `setpts` doi MOC; `-r` moi bao bo ma hoa SAP LAI thanh nhip DEU. Thieu no
    # thi moc bi lam tron va nhieu khung roi vao cung mot moc — do duoc 269 moc
    # TRUNG tren mot luot 30 fps, 100 tren 25 fps (T17 do).
    #
    # ⭐ Do tren fixture `test_2064` (nguon 25 fps, chop sang phai ra 3,200 s),
    #    do CA BA cot — vi hai cot thoi da lam toi chon sai hai lan:
    #      nhip khai (-r)        lech chop   troi A/V   loi DTS   khung
    #      passthrough             15,9 ms     15,9        40      199
    #      ⛔ khong khai            40,0 ms     55,9         0      159
    #      25 = nguon              80,0 ms     95,9         0      159
    #      **31,25 = nguon x toc**  **0,0**   **15,9**   **0**    **199**
    #    ⇒ `nguon x toc` la cau tra loi DUY NHAT xanh ca ba, VA giu het khung.
    assert cmd[cmd.index("-r") + 1] == "31.25", cmd
    assert "-fps_mode" not in cmd, cmd
    assert "-fps_mode" not in _lenh(_ban())
    assert [cmd[i + 1] for i, x in enumerate(cmd) if x == "-c:v"] == ["libx264"]


def test_vung_van_o_GD1__dat_TRUOC_toc_do():
    vung = vung_che.chuan_hoa([{"x0": 0.1, "y0": 0.1, "x1": 0.3, "y1": 0.3,
                                "loai": "lam_mo"}])
    ban = _ban({"toc_do": 1.25}, vung=vung)
    fc = _fc(_lenh(ban))
    vi_tri = [fc.index(m) for m in ("boxblur=luma_radius=min(w", "setpts=PTS/1.25")]
    assert vi_tri == sorted(vi_tri), fc


# ══ 2b. GD2 — khung -> diem_anh -> logo -> chu -> phu de, MOT chuoi ═════════

def _fc_gd2(**kw):
    cmd = gdha.dung_lenh("C:/t/gd1.mp4", "C:/t/ra.mp4", khoang=[(0.0, 8.0)],
                         bo_ma_hoa="libx264", ffmpeg_bin="ffmpeg", **kw)
    assert cmd.count("-filter_complex") == 1, cmd
    return cmd, cmd[cmd.index("-filter_complex") + 1]


def test_thu_tu_khung_diem_anh_logo_chu_phu_de_GD2(tmp_path):
    """Che (vung) KHONG con o day — no van o GD1. Thu tu con lai: khung ->
    diem_anh -> logo -> chu -> phu de."""
    lp = lop_phu.chuan_hoa([{"chu": "Dang ky", "x": 0.1, "y": 0.8, "co_chu": 0.06,
                             "mau": "trang", "vien": True}])
    lg = [logo.chuan_hoa_mot({"x": 0.8, "y": 0.05, "rong": 0.12, "khoa": "logo/a.png"})]
    pd = dict(phu_de.chuan_hoa({"che_do": "tu_dong", "kieu": "default"}),
              su_kien=[{"start": 4.0, "end": 5.0, "text": "a", "display_text": "a",
                        "line_count": 1, "scene_id": "s1", "index": 0}])
    dchu = lop_phu.viet_tep_chu(lp, tmp_path)
    ass = phu_de.viet_tep_ass(pd, pd["su_kien"], tmp_path, rong=720, cao=1280)
    bien_tap = {"khung": {"ti_le": "9:16", "cach": "nen_mo"}, "lat_guong": True,
               "dich_mau": True}
    _, fc = _fc_gd2(bien_tap=bien_tap, rong_nguon=1280, cao_nguon=720,
                    ds_logo=lg, duong_logo=["C:/t/logo.png"], rong_khung=720,
                    lop_phu=lp, duong_chu=dchu, cao_khung=1280, duong_ass=ass)
    vi_tri = [fc.index(m) for m in ("[kn][kt]", "hflip", "[lg0]", "drawtext",
                                    "ass=")]
    assert vi_tri == sorted(vi_tri), fc
    # ⛔ `toc_do` KHONG co mat o day — no van la viec cua GD1.
    assert "atempo" not in fc and "setpts=PTS/" not in fc


def test_logo_va_chu_dat_theo_khung_BAN_RA_GD2():
    """Logo rong 25% cua ban ra 9:16 (404 px) = 100 px, khong phai 25% cua 1280."""
    lg = [logo.chuan_hoa_mot({"x": 0.1, "y": 0.1, "rong": 0.25, "khoa": "logo/a.png"})]
    _, fc = _fc_gd2(bien_tap={"khung": {"ti_le": "9:16", "cach": "cat"}},
                    rong_nguon=1280, cao_nguon=720,
                    ds_logo=lg, duong_logo=["C:/t/logo.png"], rong_khung=404)
    assert f"scale=w={logo.rong_px(lg[0], 404)}:h=-2" in fc
    assert f"scale=w={logo.rong_px(lg[0], 1280)}:h=-2" not in fc


def test_logo_va_phu_de_KHONG_lop_phu_khong_trung_nhan_GD2(tmp_path):
    """Hoi quy: truoc asv-final chuoi thanh `[ra]ass=...[ra]`."""
    lg = [logo.chuan_hoa_mot({"x": 0.1, "y": 0.1, "rong": 0.2, "khoa": "logo/a.png"})]
    pd = dict(phu_de.chuan_hoa({"che_do": "tu_dong", "kieu": "default"}),
              su_kien=[{"start": 1.0, "end": 2.0, "text": "a", "display_text": "a",
                        "line_count": 1, "scene_id": "s1", "index": 0}])
    ass = phu_de.viet_tep_ass(pd, pd["su_kien"], tmp_path, rong=1280, cao=720)
    _, fc = _fc_gd2(rong_nguon=1280, cao_nguon=720, ds_logo=lg,
                    duong_logo=["C:/t/logo.png"], rong_khung=1280,
                    cao_khung=720, duong_ass=ass)
    assert cdr.NHAN_HINH_RA in fc
    assert f"[{cdr.NHAN_HINH_RA}]ass=" not in fc
    assert fc.endswith(f"[{cdr.NHAN_HINH_RA}]")
    assert fc.count(f"[{cdr.NHAN_HINH_RA}]") == 1


def test_kiem_khung_ra_BAN_GIAO_do_KICH_THUOC():
    bien_tap = {"khung": {"ti_le": "1:1", "cach": "cat"}}

    def tt(kich):
        return {"rong": kich[0], "cao": kich[1]}
    gdha._kiem_khung_ra(tt((720, 720)), bien_tap, 1280, 720)
    with pytest.raises(ket_xuat.KetXuatError, match="khung"):
        gdha._kiem_khung_ra(tt((1280, 720)), bien_tap, 1280, 720)


# ══ 3. Noi mach: COMPOSE chuyen toc_do, GD1 KHONG con logo/khung, GD2 nhan ═══

def test_compose_CHUYEN_toc_do__GD1_KHONG_con_logo_khung__GD2_nhan():
    from apps.auto_scan_video import (giai_doan_ban_dung as gdb,
                                      giai_doan_hinh_anh as gh,
                                      giai_doan_ket_xuat as gdk)

    kw = {k.arg for n in ast.walk(ast.parse(inspect.getsource(gdb.chay)))
          if isinstance(n, ast.Call) for k in n.keywords if k.arg}
    assert "bien_tap" in kw
    # ⛔ GD1 khong con GOI ham voi cac tu khoa nay (dung AST, khong phai chuoi
    #    tho — chu thich giai thich LY DO cua lan tai cau truc CO the nhac ten
    #    chung, va do khong phai loi).
    goi_gd1 = {k.arg for n in ast.walk(ast.parse(inspect.getsource(gdk.chay)))
              if isinstance(n, ast.Call) for k in n.keywords if k.arg}
    assert not (goi_gd1 & {"khung_ra", "logo", "lop_phu", "duong_ass",
                           "duong_chu", "duong_logo"}), goi_gd1
    ma_gd2 = inspect.getsource(gh.chay)
    assert "cai.logo" in ma_gd2 and "cai.lop_phu" in ma_gd2
    assert "bien_tap_gd2" in ma_gd2


def test_T15_doi_moc_phu_de_sang_truc_BAN_RA():
    """Ban ra 6,4 s (8 s x 1/1,25). Dong phu de ket o 7,9 s truc bien tap = 6,32 s
    ban ra: NAM TRONG. Doi chung: bo `bien_tap` khoi hinh thi T15 phai HONG."""
    su_kien = [{"start": 7.0, "end": 7.9}]
    hinh = {"bien_tap": {"toc_do": 1.25}, "phu_de": {"su_kien": su_kien}}

    def t15(h):
        bc = qc.kiem(tt_ra={"co_video": True, "co_tieng": True, "thoi_luong": 6.4,
                            "thoi_luong_video": 6.4, "thoi_luong_tieng": 6.4},
                     tt_nguon={"thoi_luong": 8.0}, am_luong={"lufs": -14, "dinh_that": -2},
                     ke_hoach=KE_HOACH, ban_ke_tieng={"doan": [{"ma": "s1", "khoa": "k"}]},
                     che_do_render=cdr.CAT_MA_HOA_LAI, thoi_luong_mong_doi=6.4,
                     ban_hinh=h)
        return {m["ma"]: m for m in bc["muc"]}

    m = t15(hinh)
    assert m["T15"]["trang_thai"] == qc.DAT and m["T15"]["toc_do"] == 1.25
    assert m["T2"]["trang_thai"] == qc.DAT and m["T16"]["trang_thai"] == qc.DAT
    assert t15({"phu_de": {"su_kien": su_kien}})["T15"]["trang_thai"] == qc.HONG
