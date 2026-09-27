"""ASV final (lan ky-thuat) — hop dong: tham chieu VMAF = DUNG chuoi loc render.

🔑 T18 do thiet hai cua BO MA HOA bang cach chay lai chuoi loc render (khong ma
   hoa) lam tham chieu. Neu `qc.loc_tham_chieu` lech chuoi GD2 that
   (`giai_doan_hinh_anh.dung_lenh`) du mot ky tu (vd them mot bien doi o render
   ma quen o QC), VMAF se do su khac nhau cua HAI chuoi loc va bao "ma hoa te"
   mot cach sai. Bai nay chot hai ben bang nhau voi CA NAM bien doi diem anh
   (khung, diem_anh, lop phu chu, logo, phu de) CONG phep cat.

🔴 **Cap nhat gd2-diem-anh (25/09): tham chieu chot bang chuoi GD2, khong con
   GD1.** Bon bien doi (tru vung) da chuyen xuong `giai_doan_hinh_anh.py`;
   `qc.loc_tham_chieu` ghep lai bang `che_do_render.loc_cat_noi` (van CHI mot
   ham, dung cac ham thap giong het GD2 dung) nhung nhan `ds_logo`/`lop_phu`/
   `bien_tap` la THAM SO RIENG (khong con doc tu ban dung GD1).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import giai_doan_hinh_anh as gdha  # noqa: E402
from apps.auto_scan_video import che_do_render as cdr  # noqa: E402
from apps.auto_scan_video import logo, lop_phu, phu_de, qc  # noqa: E402

GOI_SU_KIEN = [{"start": 0.5, "end": 3.0, "text": "Phu de",
               "display_text": "Phu de", "line_count": 1, "scene_id": "s1",
               "index": 0}]


def _ca_bon() -> dict:
    return dict(
        bien_tap={"khung": {"ti_le": "9:16", "cach": "nen_mo"}, "lat_guong": True,
                 "dich_mau": True},
        lop_phu=lop_phu.chuan_hoa([{"chu": "Dang ky kenh", "x": 0.1, "y": 0.8,
                                    "co_chu": 0.06, "mau": "trang",
                                    "vien": True}]),
        ds_logo=[logo.chuan_hoa_mot({"x": 0.8, "y": 0.05, "rong": 0.12,
                                     "khoa": "logo/a.png"})],
        phu_de=dict(phu_de.chuan_hoa({"che_do": "tu_dong", "kieu": "default"}),
                    su_kien=GOI_SU_KIEN),
    )


#: Manh CO NGHIA cho tung bien doi, doc lap voi quy uoc nhan/chi-so-dau-vao cua
#: TUNG ham — `loc_tham_chieu` (video mot minh, logo o `2:v`, dung `loc_cat_noi`)
#: va `giai_doan_hinh_anh.dung_lenh` (video+tieng CHUNG mot dau vao, logo o
#: `1:v`, dung `loc_cat_hai_dong`) KHONG THE giong byte-cho-byte — hai ham nhung
#: vao hai lenh ffmpeg CO HINH DANG dau vao khac nhau mot cach co y
#: (`CHI_SO_LOGO_DAU`), va mot ham lo tieng con ham kia thi khong. Cai phai
#: TRUNG KHOP la THAM SO HINH HOC (crop/scale/toa do) va THU TU — do la dieu
#: chot chuoi loc render THAT SU ap dung, chu khong phai tung ky tu cua lenh.
_MANH = {
    "bien_tap": ("scale=360:640:force_original_aspect_ratio=increase,"
                "crop=360:640,boxblur=luma_radius=min(w\\,h)/20:luma_power=2",
                "hflip,eq=saturation=1.1200"),
    "lop_phu": ("drawtext=expansion=none:fontfile=",),
    "phu_de": ("ass='",),
}


@pytest.mark.parametrize("bo_di", ["", "bien_tap", "lop_phu", "ds_logo", "phu_de"])
def test_loc_tham_chieu_TRUNG_KHOP_THAM_SO_HINH_HOC_cua_GD2_that(tmp_path, bo_di):
    bd = _ca_bon()
    if bo_di:
        bd.pop(bo_di)
    khoang = [(0.0, 2.0), (2.5, 4.0)]
    lp = list(bd.get("lop_phu") or ())
    ds_logo = list(bd.get("ds_logo") or ())
    pd = bd.get("phu_de")
    rong_ra, cao_ra = gdha._khung_ra(bd.get("bien_tap"), 640, 360)
    duong_chu = lop_phu.viet_tep_chu(lp, tmp_path)
    duong_ass = phu_de.viet_tep_ass(pd, (pd or {}).get("su_kien") or [], tmp_path,
                                    rong=rong_ra, cao=cao_ra) if pd else ""
    cmd = gdha.dung_lenh(
        "C:/t/gd1.mp4", "C:/t/ra.mp4", khoang=khoang, bo_ma_hoa="libx264",
        ffmpeg_bin="ffmpeg", bien_tap=bd.get("bien_tap"),
        rong_nguon=640, cao_nguon=360, ds_logo=ds_logo,
        duong_logo=["C:/t/logo.png"] * len(ds_logo), rong_khung=rong_ra,
        lop_phu=lp, duong_chu=duong_chu, cao_khung=cao_ra, duong_ass=duong_ass)
    render = cmd[cmd.index("-filter_complex") + 1]

    hinh = {"khoang_giu": [list(k) for k in khoang], "vung": (),
           "rong_khung": 640, "cao_khung": 360}
    tham = qc.loc_tham_chieu(hinh, duong_chu=duong_chu, duong_ass=duong_ass,
                             ds_logo=ds_logo, lop_phu=lp,
                             bien_tap=bd.get("bien_tap"))

    for khoa, manh_ds in _MANH.items():
        co = khoa != bo_di
        for manh in manh_ds:
            assert (manh in render) is co, (khoa, manh, "render")
            assert (manh in tham) is co, (khoa, manh, "tham")

    # ⭐ Logo: rieng, vi be rong pixel cua no phu thuoc khung BAN RA — thay doi
    #    theo ca `bien_tap` (doi ti le) lan chinh no. Tinh DUNG con so mong doi
    #    tu `logo.rong_px` thay vi go cung mot con so.
    manh_logo = f"scale=w={logo.rong_px(_ca_bon()['ds_logo'][0], rong_ra)}:h=-2"
    co_logo = bo_di != "ds_logo"
    assert (manh_logo in render) is co_logo, (manh_logo, "render")
    assert (manh_logo in tham) is co_logo, (manh_logo, "tham")


def _cua_so_trim(chuoi: str) -> list[tuple[float, float]]:
    """Cac cua so `trim=` doc TU chuoi loc — mot phep do, ⛔ khong phai mot ky vong
    ve cach go. Bai duoi chot TONG THOI LUONG, nen no con dung khi `loc_cat_noi`
    doi cach viet cua so (vd sang `between(t,..)`), chi hong khi CON SO sai."""
    import re

    return [(float(b), float(k)) for b, k in
            re.findall(r"trim=start=([\d.]+):end=([\d.]+)", chuoi)]


def test_2012_tham_chieu_MANG_toc_do_va_cua_so_KHONG_doi_truc():
    """🔴 `duong_nguon` la tep NGUON (`run.source_key`), `duong_ra` la ban giao —
    **da** qua `setpts=PTS/toc` (o GD2 tu B6). Ban tham chieu ⛔ khong ap `toc_do`
    thi hai ben lech tung khung, VMAF do mot thu khong ai hoi, va **T18 bao `hong`
    tren mot tep khong sai gi ca**.

    🔴 **Doi kep o B6 (27/09), va chung NGUOC chieu nhau:**
      1. `toc_do` ⛔ khong con la tham so RIENG — `bien_tap` cua GD2 nay GIU no,
         nen `loc_tham_chieu` doc he so tu chinh ho so ay. Mot con so di rieng
         canh ho so cua no la hai cho khai MOT su that, dung hinh dang sinh T2.
      2. Cua so cat ⛔ KHONG con duoc doi truc. Truoc B6, `khoang_giu` cua
         `image_finish` nam tren truc BAN RA CUA GD1 (sau `setpts`) nen phai nhan
         voi `toc`. Nay GD1 ⛔ khong doi moc, nen `khoang_giu` o truc NGUON —
         **cung truc voi tep ma `loc_cat_noi` cat**. Mot phep nhan o day bay gio
         la mot phep SAI.

    ⭐ Chot CA HAI chieu: chuoi phai CO `setpts` VA cua so phai GIU NGUYEN. Sua
       mot chieu thoi thi lech NANG hon la ⛔ khong sua gi.

    ⚠️ Chot bang TONG THOI LUONG, ⛔ khong bang chuoi ky tu: mot bai chot
       `"start=3.125000"` la mot banh coc do CACH GO — no do khi ai do doi dinh
       dang so, va no im khi he so sai ma dinh dang dung.
    """
    toc = 1.25
    khoang_nguon = [(0.0, 2.0), (2.5, 4.0)]      # ⭐ truc NGUON (B6)
    hinh = {"khoang_giu": [list(k) for k in khoang_nguon], "vung": (),
            "rong_khung": 640, "cao_khung": 360}

    mot = qc.loc_tham_chieu(hinh, duong_chu=[], duong_ass="",
                            bien_tap={"toc_do": 1.0})
    nhanh = qc.loc_tham_chieu(hinh, duong_chu=[], duong_ass="",
                              bien_tap={"toc_do": toc})

    # (1) `setpts` cua toc do: vang khi toc = 1, co khi toc != 1 — va o CUOI.
    assert "setpts=PTS/" not in mot, (
        "toc_do = 1 ma tham chieu van ap mot phep doi moc: " + mot)
    assert "setpts=PTS/" in nhanh, (
        f"toc_do = {toc} ma tham chieu ⛔ khong ap phep doi moc — T18 se bao hong "
        f"tren mot tep khong sai gi: {nhanh}")
    assert "setpts=PTS/" in nhanh.split(";")[-1], (
        "toc do phai la buoc CUOI cua chuoi tham chieu, dung thu tu voi ban "
        "giao (`loc_cat_hai_dong` dat no o duoi): " + nhanh)

    # (2) Cua so GIU NGUYEN — ca hai nhanh doc CUNG mot luong giay tu tep nguon.
    tong_nguon = sum(k - b for b, k in khoang_nguon)
    tong_mot = sum(k - b for b, k in _cua_so_trim(mot))
    tong_nhanh = sum(k - b for b, k in _cua_so_trim(nhanh))

    assert tong_mot == pytest.approx(tong_nguon), (
        f"toc_do = 1: cua so phai giu nguyen, {tong_mot} != {tong_nguon}")
    assert tong_nhanh == pytest.approx(tong_nguon), (
        f"cua so bi DOI TRUC ({tong_nhanh} thay vi {tong_nguon}) — `khoang_giu` "
        f"cua GD2 da o truc NGUON tu B6, mot phep nhan voi toc la phep SAI")

    # ⭐ Ve DOI CHUNG: sau khi ap `setpts`, tham chieu dai DUNG bang tep duoc do
    #    (`tong_nguon / toc`). Day la tinh chat ma T18 that su can, va no chot CA
    #    HAI buoc tren cung mot luc — mot buoc dung mot buoc sai thi so nay lech.
    assert tong_nhanh / toc == pytest.approx(tong_nguon / toc), (
        "tham chieu sau setpts ⛔ khong dai bang ban giao")


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
