"""asv-final lan `bien-tap` — settings -> RenderManifest -> MOT `filter_complex`.

🔴 **Cap nhat B6 (27/09): `toc_do` CUNG da chuyen xuong GD2 — GD1 ⛔ khong con
   THUC THI mot phep bien tap nao.** Truoc B6, GD1 giu rieng `toc_do` va vi the
   doi TRUC thoi gian TRUOC khi GD2 cat, bat ba cho khac tu doi truc bang tay
   (sinh ra T2 · T17 · mot ca cat vao giua cau thoai). Nay GD1 chi con `vung`
   (lam mo/dien nen), va no o lai vi mot rang buoc VAT LY: toa do cua `vung`
   thuoc khung NGUON, dat TRUOC `concat`.
   Hop dong: `docs/auto_scan_video_final/B6_PLAN_MOT_TRUC_THOI_GIAN.md`.
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
    """⭐ `bien_tap` VAN o chu ky — de bai duoi chung minh GD1 **TU CHOI** no."""
    return ban_dung.dung(
        khoa_video="v/g.mp4", khoa_nen="n.wav", khoa_master="m.wav",
        ke_hoach=KE_HOACH, ban_ke_tieng={"doan": [{"ma": "s1", "khoa": "v/s1.wav"}]},
        phien_ban_ffmpeg="n8", tong_giay=8.0, che_do=cdr.CAT_MA_HOA_LAI,
        bo_ma_hoa="libx264", khoang_giu=[(0.0, 8.0)], preset="smart_localize",
        rong_khung=1280, cao_khung=720, bien_tap=bien_tap, **them)


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


def test_ban_dung_GD1_TU_CHOI_moi_ho_so_bien_tap__ke_ca_toc_do():
    """🔴 **B6: GD1 NEM khi bi truyen `bien_tap`, ke ca chi co `toc_do`.**

    ⭐ Va `thoi_luong_ra` cua GD1 nay = `tong_giay` (8,0) — ⛔ KHONG con chia cho
       `toc_do` (6,4 truoc B6). Do la phep do truc tiep cua *"GD1 ⛔ khong con
       doi moc thoi gian"*: neu ai tra lai phep chia thi con so nay doi ngay.

    ⛔ Im lang bo qua se te hon nem: khach xin mot phep ma ⛔ KHONG giai doan nao
       thuc thi — GD2 chi doc `cai_dat.doc(run)`, ⛔ khong doc ban dung nay.
    """
    ban = _ban()
    assert "khung_ra" not in ban["hinh"]
    assert ban["ra"]["thoi_luong_giay"] == pytest.approx(8.0)
    for bt in ({"toc_do": 1.25},
               {"khung": {"ti_le": "9:16", "cach": "cat"}},
               {"toc_do": 1.25, "khung": {"ti_le": "9:16", "cach": "cat"}}):
        with pytest.raises(ban_dung.BanDungError, match="giai đoạn 2"):
            _ban(bt)


def test_kiem_chan_bien_tap_o_duong_sao_chep():
    """⚠️ Tiem `bien_tap` bang TAY: tu B6 `dung()` tu choi no ngay o cua vao, nen
    duong duy nhat mot ban dung co `hinh.bien_tap` la bi ghi truc tiep — vd mot
    ban dung CU doc lai tu kho. `kiem` van phai chan."""
    ban = _ban()
    ban["hinh"]["bien_tap"] = {"toc_do": 1.25}
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


def test_GD1_KHONG_BAO_GIO_phat_setpts_atempo_hay_r():
    """🔴 **Bat bien B6: chuoi cua GD1 ⛔ khong chua MOT phep doi moc thoi gian.**

    `setpts=PTS/` (nen moc hinh), `atempo` (nen moc tieng) va `-r` (khai nhip ra)
    deu la phep doi truc, va hop dong buoc chung xep o CUOI GD2. Do CA hai duong
    GD1: co `vung` (ma hoa lai) va ⛔ khong `vung` (remux).

    ⛔ Va `loc_cat_noi` NEM neu bi truyen `toc_do` — mot lan chay giao tep ⛔ CHUA
       doi toc do la thu khach phat hien ra truoc ta, nen cho nay phai on ao.
    """
    vung = vung_che.chuan_hoa([{"x0": 0.1, "y0": 0.1, "x1": 0.3, "y1": 0.3,
                                "loai": "lam_mo"}])
    for ban in (_ban(), _ban(vung=vung)):
        cmd = _lenh(ban)
        assert "-r" not in cmd and "-fps_mode" not in cmd, cmd
        fc = cmd[cmd.index("-filter_complex") + 1] if "-filter_complex" in cmd else ""
        assert "setpts=PTS/" not in fc and "atempo" not in fc, fc
        # ⭐ Tieng di thang tu ban phoi, ⛔ khong qua mot nhan loc nao.
        assert "1:a:0" in cmd and "[a_ra]" not in cmd

    with pytest.raises(cdr.CheDoError, match="giai đoạn 2"):
        cdr.loc_cat_noi([(0.0, 8.0)], bien_tap={"toc_do": 1.25})


def test_vung_o_GD1_va_toc_do_o_GD2__va_do_la_DUNG_thu_tu():
    """⭐ Truoc B6 hai phep nay nam trong MOT chuoi va thu tu la mot khang dinh
    ve chuoi. Nay chung o HAI lenh khac nhau, va thu tu do CHINH DUONG ONG bao
    dam: GD1 chay truoc GD2. Bai nay chot rang moi phep o dung lenh cua no."""
    vung = vung_che.chuan_hoa([{"x0": 0.1, "y0": 0.1, "x1": 0.3, "y1": 0.3,
                                "loai": "lam_mo"}])
    fc1 = _fc(_lenh(_ban(vung=vung)))
    assert "boxblur=luma_radius=min(w" in fc1 and "setpts=PTS/" not in fc1

    _, fc2 = _fc_gd2(bien_tap={"toc_do": 1.25})
    assert "setpts=PTS/1.2500" in fc2 and "boxblur" not in fc2


# ══ 2b. GD2 — khung -> diem_anh -> logo -> chu -> phu de, MOT chuoi ═════════

def _kiem_do_thi(loc: str) -> None:
    """🔴 **Kiem DO THI loc, ⛔ khong kiem VI TRI chuoi.**

    Do 27/09 bang mot phep tiem: doi `hinh_cuoi` ve `NHAN_HINH_RA` (tuc ap toc do
    ma ⛔ khong noi day chuoi vao no) sinh ra mot do thi **HONG** —

        [v0][a0]concat=...[vr][truoc_toc_a]
        [truoc_toc]setpts=PTS/1.2500[vr]     <- `truoc_toc` ⛔ KHONG ai sinh,
                                                va `vr` bi sinh HAI lan

    ffmpeg se tu choi chuoi ay. Nhung moi khang dinh dua tren **vi tri** (*"setpts
    o buoc thu hai tu duoi"*) van XANH, vi phep tiem ⛔ khong doi thu tu cac buoc
    duoc noi vao. ⇒ Bai kiem do CACH GO chu ⛔ khong do dieu no chot — dung ho
    `banh coc do CACH GO thay vi do tinh chat`.

    ⭐ Phep kiem dung la mot BAT BIEN cua do thi: moi nhan trung gian duoc sinh
       DUNG MOT lan, va moi nhan bi tieu thu phai co ai sinh ra no. No bat ca hai
       khiem khuyet tren cung luc, va bat moi loi noi day khac ma ⛔ khong ai nghi
       ra tu truoc.
    """
    import re

    sinh: list[str] = []
    tieu_thu: list[str] = []
    for buoc in loc.split(";"):
        # ⭐ Tach VAO / RA bang cho dat: nhan o DAU buoc la dau vao, nhan sau ten
        #    bo loc la dau ra. Mot buoc co the co NHIEU ca hai (vd `concat`).
        m_vao = re.match(r"^(\[[^\]]+\])+", buoc)
        vao = re.findall(r"\[([^\]]+)\]", m_vao.group(0)) if m_vao else []
        m_ra = re.search(r"(\[[^\]]+\])+$", buoc)
        ra = re.findall(r"\[([^\]]+)\]", m_ra.group(0)) if m_ra else []
        # ⛔ Nhan dang `0:v` / `1:a` la dau vao NGOAI (tep), ⛔ khong trung gian.
        tieu_thu += [n for n in vao if ":" not in n]
        sinh += ra

    trung = sorted(n for n in set(sinh) if sinh.count(n) > 1)
    assert not trung, "nhan bi SINH nhieu lan: %s\n%s" % (trung, loc)
    mo_coi = sorted(set(tieu_thu) - set(sinh))
    assert not mo_coi, (
        "nhan bi TIEU THU ma ⛔ khong ai sinh: %s — do thi loc HONG, ffmpeg "
        "se tu choi\n%s" % (mo_coi, loc))


def _fc_gd2(**kw):
    cmd = gdha.dung_lenh("C:/t/gd1.mp4", "C:/t/ra.mp4", khoang=[(0.0, 8.0)],
                         bo_ma_hoa="libx264", ffmpeg_bin="ffmpeg", **kw)
    assert cmd.count("-filter_complex") == 1, cmd
    loc = cmd[cmd.index("-filter_complex") + 1]
    # ⭐ MOI chuoi GD2 di qua day deu bi kiem DO THI — xem `_kiem_do_thi`.
    _kiem_do_thi(loc)
    return cmd, loc


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


def test_toc_do_o_DUOI_CHUOI_GD2__sau_ca_phu_de__tren_CA_HAI_dong(tmp_path):
    """🔴 **Toc do la buoc CUOI CUNG tuyet doi (B6), ke ca sau `ass`.**

    Vi sao thu tu nay la mot QUYET DINH: moi buoc tren no DOC moc thoi gian (cat
    theo khoang, dot phu de theo moc). Dat toc do truoc bat ca chung doi truc
    theo — dung cai gia ma T2/T17 da tra. Dat sau thi ⛔ khong ai phai doi.

    ⭐ Va phu de duoc dot TRUOC `setpts` con mang mot mon qua: moc phu de duoc co
       gian CUNG hinh, tu dong, ⛔ khong mot phep doi truc nao.
    """
    ass = tmp_path / "p.ass"
    ass.write_text("[Script Info]\n", encoding="utf-8")
    cmd, fc = _fc_gd2(bien_tap={"toc_do": 1.25}, duong_ass=str(ass),
                      thoi_luong_ra=8.0, fps_vao=25.0)
    buoc = fc.split(";")
    # ⭐ Hai phep doi moc la HAI buoc CUOI, ⛔ khong o giua.
    assert "setpts=PTS/1.2500" in buoc[-2] and "atempo=1.2500" in buoc[-1], fc
    assert "ass=" in ";".join(buoc[:-2]), fc
    # ⭐ CA HAI dong, CUNG he so — `atempo` thieu thi hinh va tieng lech dan.
    assert f"[{cdr.NHAN_HINH_RA}]" in buoc[-2]
    assert f"[{cdr.NHAN_TIENG_RA}]" in buoc[-1]
    # 🔑 **`-r` = nhip VAO x toc (T17): 25 x 1,25 = 31,25.** `setpts` doi MOC;
    #    `-r` moi bao bo ma hoa SAP LAI thanh nhip DEU. Thieu no thi moc bi lam
    #    tron va nhieu khung roi vao CUNG mot moc — do duoc 269 moc TRUNG tren
    #    mot luot 30 fps, 100 tren 25 fps.
    #
    # ⭐ Do tren fixture `test_2064` (nguon 25 fps, chop sang phai ra 3,200 s),
    #    do CA BA cot — vi hai cot thoi da lam chon sai HAI lan:
    #      nhip khai (-r)           lech chop   troi A/V   loi DTS   khung
    #      passthrough                15,9 ms     15,9        40      199
    #      ⛔ khong khai (`auto`)      40,0 ms     55,9         0      159
    #      25 = nhip vao              80,0 ms     95,9         0      159
    #      **31,25 = vao x toc**      **0,0**   **15,9**    **0**   **199**
    #      30                         66,7 ms     82,5         0      191
    #    ⇒ `vao x toc` la cau tra loi DUY NHAT xanh ca ba cot, VA giu het khung.
    #
    # ⚠️ Chu du an de xuat *"fps dau vao = dau ra"*. So do BAC: `-r 25` lam noi
    #    dung TRE 80 ms — te hon ca viec ⛔ khong khai gi — vi CFR buoc phai BO
    #    khung. `vao x toc` la nhip ma noi dung VON DA CO sau khi `setpts` nen
    #    moc, nen khai no thi bo ma hoa dat khung dung luoi, ⛔ bo khung nao.
    assert cmd[cmd.index("-r") + 1] == "31.25", cmd
    # 🔑 `-t` = do dai sau cat CHIA cho toc: 8,0 / 1,25 = 6,4. Thieu phep chia thi
    #    `-t` dai hon tep thuc va ⛔ khong ghim gi (toc > 1).
    assert cmd[cmd.index("-t") + 1] == "6.400000", cmd
    # ⛔ Duong `toc_do = 1` ⛔ khong doi mot byte nao.
    cmd1, fc1 = _fc_gd2(thoi_luong_ra=8.0, fps_vao=25.0)
    assert "setpts=PTS/" not in fc1 and "atempo" not in fc1
    assert "-r" not in cmd1 and cmd1[cmd1.index("-t") + 1] == "8.000000"


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

def test_compose_KHONG_truyen_bien_tap__GD1_khong_logo_khung__GD2_nhan():
    from apps.auto_scan_video import (giai_doan_ban_dung as gdb,
                                      giai_doan_hinh_anh as gh,
                                      giai_doan_ket_xuat as gdk)

    kw = {k.arg for n in ast.walk(ast.parse(inspect.getsource(gdb.chay)))
          if isinstance(n, ast.Call) for k in n.keywords if k.arg}
    # 🔴 **B6: COMPOSE ⛔ khong con truyen `bien_tap` (hay `fps_nguon`) xuong GD1.**
    #    Dung AST chu ⛔ khong chuoi tho: chu thich giai thich LY DO cua lan tai
    #    cau truc CO nhac ten chung, va do ⛔ khong phai loi.
    assert not (kw & {"bien_tap", "fps_nguon"}), kw
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
