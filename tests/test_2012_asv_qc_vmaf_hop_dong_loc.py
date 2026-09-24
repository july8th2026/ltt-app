"""ASV final (lan ky-thuat) — hop dong: tham chieu VMAF = DUNG chuoi loc render.

🔑 T18 do thiet hai cua BO MA HOA bang cach chay lai chuoi loc render (khong ma
   hoa) lam tham chieu. Neu `qc.loc_tham_chieu` lech `ket_xuat.dung_lenh` du mot
   ky tu (vd them mot bien doi o render ma quen o QC), VMAF se do su khac nhau
   cua HAI chuoi loc va bao "ma hoa te" mot cach sai. Bai nay chot hai ben bang
   nhau voi CA BON bien doi diem anh (vung, chu, logo, phu de).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import (che_do_render as cdr, ket_xuat, lop_phu,  # noqa: E402
                                  phu_de, qc)
from tests.test_474_asv_v6_mot_lan_ma_hoa import _ban, _ca_bon  # noqa: E402


@pytest.mark.parametrize("bo_di", ["", "vung", "lop_phu", "ds_logo", "phu_de"])
def test_loc_tham_chieu_TRUNG_KHOP_chuoi_loc_render(tmp_path, bo_di):
    bd = _ca_bon()
    if bo_di:
        bd.pop(bo_di)
    ban = _ban(**bd)
    duong_chu = lop_phu.viet_tep_chu(list(bd.get("lop_phu") or ()), tmp_path)
    pd = bd.get("phu_de")
    duong_ass = phu_de.viet_tep_ass(pd, (pd or {}).get("su_kien") or [], tmp_path,
                                    rong=640, cao=360) if pd else ""
    so_logo = len(bd.get("ds_logo") or ())
    cmd = ket_xuat.dung_lenh(
        ban, ffmpeg_bin="ffmpeg", duong_video="C:/t/g.mp4",
        duong_master="C:/t/m.wav", duong_lop=["C:/t/s0.wav"],
        duong_ra="C:/t/ra.mp4", bo_ma_hoa="libx264", duong_chu=duong_chu,
        duong_logo=["C:/t/logo.png"] * so_logo, duong_ass=duong_ass)
    render = cmd[cmd.index("-filter_complex") + 1]
    assert qc.loc_tham_chieu(ban["hinh"], duong_chu=duong_chu,
                             duong_ass=duong_ass) == render


def test_lenh_vmaf_dau_vao_DUNG_thu_tu_va_ban_bi_mo_DI_TRUOC():
    """libvmaf: dau vao 1 = ban bi mo (distorted), 2 = tham chieu. Dao nguoc la
    do mot thu khac. Logo o chi so 2.. nhu render, nen `[2:v]` trong chuoi loc
    render van tro dung logo."""
    cmd = qc.lenh_vmaf(duong_nguon="n.mp4", duong_ra="r.mp4",
                       loc_hinh="[0:v]null[ra]", duong_logo=["l.png"],
                       rong=1024, cao=576, duong_log="C:/t/v.json")
    i = [x for j, x in enumerate(cmd) if j and cmd[j - 1] == "-i"]
    assert i == ["n.mp4", "r.mp4", "l.png"]
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "[dist][ref]libvmaf=" in fc
    assert f"n_subsample={qc.VMAF_N_SUBSAMPLE}" in fc
    assert "log_path='C\\:/t/v.json'" in fc


@pytest.mark.parametrize("rong,cao,mo_hinh,co_gian", [
    (1024, 576, "vmaf_v0.6.1", True),
    (576, 1024, "vmaf_v0.6.1", True),     # video doc: van vua khung 1920x1080
    (1920, 1080, "vmaf_v0.6.1", True),
    (3840, 2160, "vmaf_4k_v0.6.1", False),
])
def test_chon_mo_hinh_theo_do_phan_giai(rong, cao, mo_hinh, co_gian):
    m, loc = qc.chon_mo_hinh_vmaf(rong, cao)
    assert m == mo_hinh
    assert bool(loc) is co_gian


def test_doc_vmaf_tong_hop():
    goi = {"frames": [{"metrics": {"vmaf": v}} for v in (90.0, 95.0, 99.0, 80.0)],
           "pooled_metrics": {"vmaf": {"mean": 91.0, "harmonic_mean": 90.5}}}
    r = qc.doc_vmaf(goi)
    assert r["trung_binh"] == 91.0 and r["nho_nhat"] == 80.0 and r["so_khung"] == 4


def _kiem(**kw):
    return qc.kiem(tt_ra={"co_video": True, "co_tieng": True, "thoi_luong": 6.0},
                   tt_nguon={"co_video": True, "co_tieng": True, "thoi_luong": 6.0},
                   am_luong={"lufs": qc.LUFS_DICH, "dinh_that": -2.0},
                   ke_hoach={"doan": []}, ban_ke_tieng={"doan": []}, **kw)


def _t18(bc):
    return next(m for m in bc["muc"] if m["ma"] == "T18")


def test_T18_preset_GIU_HINH_khong_ap_dung_vi_T3_da_chung_minh_bit_exact():
    m = _t18(_kiem(che_do_render=cdr.SAO_CHEP, vmaf={"trung_binh": 10.0}))
    assert m["trang_thai"] == qc.KHONG_AP_DUNG


def test_T18_khong_do_duoc_la_KHONG_KHA_DUNG_khong_lui_ve_heuristic():
    m = _t18(_kiem(che_do_render=cdr.CAT_MA_HOA_LAI, vmaf={"loi": "no libvmaf"}))
    assert m["trang_thai"] == qc.KHONG_AP_DUNG and m["mo_ta"] == "khong_kha_dung"


def test_T18_duoi_nguong_HONG_tren_nguong_DAT():
    lo = {"trung_binh": qc.VMAF_TOI_THIEU - 1, "nho_nhat": 1.0}
    hi = {"trung_binh": qc.VMAF_TOI_THIEU + 1, "nho_nhat": 50.0}
    assert _t18(_kiem(che_do_render=cdr.CAT_MA_HOA_LAI, vmaf=lo))["trang_thai"] == qc.HONG
    assert _t18(_kiem(che_do_render=cdr.CAT_MA_HOA_LAI, vmaf=hi))["trang_thai"] == qc.DAT
