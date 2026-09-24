"""asv-final lan `bien-tap` — settings -> RenderManifest -> MOT `filter_complex`.

⭐ Khang dinh DUONG, cung khuon `test_474`: moi chang bien tap phai CO MAT trong
   chuoi loc duy nhat, dung THU TU, voi dung MOT `-c:v` — va bo bien tap thi chuoi
   quay ve tung ky tu nhu truoc.

Khong chay ffmpeg. Engine that: `test_2062`.
"""
from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import (ban_dung, che_do_render as cdr, ket_xuat, logo,
                                  lop_phu, phu_de, qc, vung_che)

KE_HOACH = {"doan": [{"ma": "s1", "dai_ms": 2000, "dat_tai_ms": 4000,
                      "he_so_toc": 1.0, "ngan_sach_ms": 500, "troi_sau_ms": 0}]}


def _ban(bien_tap=None, **them):
    return ban_dung.dung(
        khoa_video="v/g.mp4", khoa_nen="n.wav", khoa_master="m.wav",
        ke_hoach=KE_HOACH, ban_ke_tieng={"doan": [{"ma": "s1", "khoa": "v/s1.wav"}]},
        phien_ban_ffmpeg="n8", tong_giay=8.0, che_do=cdr.CAT_MA_HOA_LAI,
        bo_ma_hoa="libx264", khoang_giu=[(0.0, 8.0)], preset="smart_localize",
        rong_khung=1280, cao_khung=720, bien_tap=bien_tap, **them)


def _lenh(ban, tmp_path, **kw):
    hinh = ban["hinh"]
    dchu = lop_phu.viet_tep_chu(list(hinh.get("lop_phu") or ()), tmp_path)
    return ket_xuat.dung_lenh(
        ban, ffmpeg_bin="ffmpeg", duong_video="C:/t/g.mp4",
        duong_master="C:/t/m.wav", duong_lop=["C:/t/s0.wav"],
        duong_ra="C:/t/ra.mp4", bo_ma_hoa="libx264", duong_chu=dchu,
        duong_logo=["C:/t/logo.png"] * len(hinh.get("logo") or ()), **kw)


def _fc(cmd):
    assert cmd.count("-filter_complex") == 1, cmd
    return cmd[cmd.index("-filter_complex") + 1]


# ══ 1. Ban dung ══════════════════════════════════════════════════════════════

def test_khong_bien_tap_thi_ban_dung_KHONG_mang_khoa_moi():
    """Ban dung cu giu nguyen tung byte => van tay tep ra cua ho so cu khong doi."""
    h = _ban()["hinh"]
    assert "bien_tap" not in h and "khung_ra" not in h
    assert _ban()["ra"]["thoi_luong_giay"] == 8.0


def test_ban_dung_ghi_khung_ra_va_thoi_luong_chia_toc_do():
    ban = _ban({"toc_do": 1.25, "khung": {"ti_le": "9:16", "cach": "cat"}})
    assert ban["hinh"]["khung_ra"] == [404, 720]
    assert ban["ra"]["thoi_luong_giay"] == pytest.approx(6.4)
    assert ban_dung.khung_ra(ban["hinh"]) == (404, 720)


def test_kiem_TINH_LAI_khung_ra_va_bat_lech():
    ban = _ban({"khung": {"ti_le": "1:1", "cach": "cat"}})
    ban["hinh"]["khung_ra"] = [720, 700]
    with pytest.raises(ban_dung.BanDungError, match="biên tập khung"):
        ban_dung.kiem(ban)


def test_kiem_chan_bien_tap_o_duong_sao_chep():
    ban = _ban({"toc_do": 1.25})
    ban["hinh"]["cach_render"] = cdr.SAO_CHEP
    with pytest.raises(ban_dung.BanDungError, match="biên tập lại hình"):
        ban_dung.kiem(ban)


def test_khong_biet_khung_nguon_thi_COMPOSE_tu_choi():
    with pytest.raises(ban_dung.BanDungError, match="kích thước khung"):
        ban_dung.dung(
            khoa_video="v", khoa_nen="n", khoa_master="m", ke_hoach=KE_HOACH,
            ban_ke_tieng={"doan": [{"ma": "s1", "khoa": "k"}]},
            phien_ban_ffmpeg="n8", tong_giay=8.0, che_do=cdr.CAT_MA_HOA_LAI,
            bo_ma_hoa="libx264", khoang_giu=[(0.0, 8.0)], preset="smart_localize",
            bien_tap={"zoom": {"he_so": 2.0}})


# ══ 2. MOT filter_complex, dung thu tu ═══════════════════════════════════════

def test_khong_bien_tap_thi_chuoi_loc_GIU_NGUYEN(tmp_path):
    fc = _fc(_lenh(_ban(), tmp_path))
    assert fc == "[0:v]trim=start=0.000000:end=8.000000,setpts=PTS-STARTPTS[v0];" \
                 "[v0]concat=n=1:v=1:a=0[ra]"
    assert "-map" in _lenh(_ban(), tmp_path) and "1:a:0" in _lenh(_ban(), tmp_path)


def test_toc_do_hinh_va_tieng_CUNG_he_so_trong_MOT_do_thi(tmp_path):
    cmd = _lenh(_ban({"toc_do": 1.25}), tmp_path)
    fc = _fc(cmd)
    assert "setpts=PTS/1.2500[ra]" in fc and "[1:a]atempo=1.2500[a_ra]" in fc
    assert cmd[cmd.index("[a_ra]") - 1] == "-map" and "1:a:0" not in cmd
    # Do 22/09: thieu `passthrough` thi CFR 25 bo khung, hinh tre toi +40 ms.
    assert cmd[cmd.index("-fps_mode") + 1] == "passthrough"
    assert "-fps_mode" not in _lenh(_ban({"khung": {"ti_le": "1:1", "cach": "cat"}}), tmp_path)
    assert [cmd[i + 1] for i, x in enumerate(cmd) if x == "-c:v"] == ["libx264"]


def test_thu_tu_che_KHUNG_logo_chu_phu_de_TOC_DO(tmp_path):
    """Che TRUOC khung (toa do nguon), logo/chu/phu de SAU (toa do ban ra), toc do
    CUOI (sau phu de — cung truc bien tap voi loi long)."""
    vung = vung_che.chuan_hoa([{"x0": 0.1, "y0": 0.1, "x1": 0.3, "y1": 0.3,
                                "loai": "lam_mo"}])
    lp = lop_phu.chuan_hoa([{"chu": "Dang ky", "x": 0.1, "y": 0.8, "co_chu": 0.06,
                             "mau": "trang", "vien": True}])
    lg = [logo.chuan_hoa_mot({"x": 0.8, "y": 0.05, "rong": 0.12, "khoa": "logo/a.png"})]
    pd = dict(phu_de.chuan_hoa({"che_do": "tu_dong", "kieu": "default"}),
              su_kien=[{"start": 4.0, "end": 5.0, "text": "a", "display_text": "a",
                        "line_count": 1, "scene_id": "s1", "index": 0}])
    ban = _ban({"toc_do": 1.25, "khung": {"ti_le": "9:16", "cach": "nen_mo"}},
               vung=vung, lop_phu=lp, ds_logo=lg, phu_de=pd)
    ban_dung.kiem(ban)
    ass = phu_de.viet_tep_ass(pd, pd["su_kien"], tmp_path, rong=720, cao=1280)
    fc = _fc(_lenh(ban, tmp_path, duong_ass=ass))
    vi_tri = [fc.index(m) for m in ("boxblur=luma_radius=min(w", "[kn][kt]",
                                    "[lg0]", "drawtext", "ass=", "setpts=PTS/1.25")]
    assert vi_tri == sorted(vi_tri), fc


def test_logo_va_chu_dat_theo_khung_BAN_RA(tmp_path):
    """Logo rong 25% cua ban ra 9:16 (404 px) = 100 px, khong phai 25% cua 1280."""
    lg = [logo.chuan_hoa_mot({"x": 0.1, "y": 0.1, "rong": 0.25, "khoa": "logo/a.png"})]
    ban = _ban({"khung": {"ti_le": "9:16", "cach": "cat"}}, ds_logo=lg)
    fc = _fc(_lenh(ban, tmp_path))
    assert f"scale=w={logo.rong_px(lg[0], 404)}:h=-2" in fc
    assert f"scale=w={logo.rong_px(lg[0], 1280)}:h=-2" not in fc


def test_logo_va_phu_de_KHONG_lop_phu_khong_trung_nhan(tmp_path):
    """Hoi quy: truoc asv-final chuoi thanh `[ra]ass=...[ra]`."""
    lg = [logo.chuan_hoa_mot({"x": 0.1, "y": 0.1, "rong": 0.2, "khoa": "logo/a.png"})]
    pd = dict(phu_de.chuan_hoa({"che_do": "tu_dong", "kieu": "default"}),
              su_kien=[{"start": 1.0, "end": 2.0, "text": "a", "display_text": "a",
                        "line_count": 1, "scene_id": "s1", "index": 0}])
    ban = _ban(None, ds_logo=lg, phu_de=pd)
    ass = phu_de.viet_tep_ass(pd, pd["su_kien"], tmp_path, rong=1280, cao=720)
    fc = _fc(_lenh(ban, tmp_path, duong_ass=ass))
    assert "[ra]ass=" not in fc and fc.endswith("[ra]") and fc.count("[ra]") == 1


def test_kiem_tep_ra_do_KICH_THUOC_khung_ra(tmp_path):
    ban = _ban({"khung": {"ti_le": "1:1", "cach": "cat"}})
    duong = tmp_path / "ra.mp4"
    duong.write_bytes(b"x")

    def soi(kich):
        return lambda _d: {"co_video": True, "co_tieng": True, "thoi_luong": 8.0,
                           "rong": kich[0], "cao": kich[1]}
    ket_xuat.kiem_tep_ra(str(duong), ban, soi=soi((720, 720)))
    with pytest.raises(ket_xuat.KetXuatError, match="khung"):
        ket_xuat.kiem_tep_ra(str(duong), ban, soi=soi((1280, 720)))


# ══ 3. Noi mach: COMPOSE chuyen, RENDER doc, QC doi truc ═════════════════════

def test_compose_CHUYEN_bien_tap_va_ket_xuat_dung_khung_ra_cho_phu_de():
    from apps.auto_scan_video import giai_doan_ban_dung as gdb, giai_doan_ket_xuat as gdk

    kw = {k.arg for n in ast.walk(ast.parse(inspect.getsource(gdb.chay)))
          if isinstance(n, ast.Call) for k in n.keywords if k.arg}
    assert "bien_tap" in kw
    assert "khung_ra" in inspect.getsource(gdk.chay)


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
