"""ASV V6 pha 26 — Renderer fusion: MOT lan ma hoa cho moi bien doi diem anh.

🔴 **Cap nhat gd2-diem-anh (25/09): mat xich CHUYEN nha, menh de KHONG doi.**

   Truoc lan nay, ca bon bien doi (vung, lop phu, logo, phu de) BAT buoc nam
   trong MOT `-filter_complex` cua **GD1** (`render`). Chu du an chot 25/09
   chuyen `logo · watermark(lop_phu) · phu de · lat guong · dich mau · zoom` (=
   khung/`bien_tap` hinh hoc + diem_anh) xuong **GD2** (`image_finish`) — va do
   CHINH LA tai cau truc lam menh de trung tam nay TIEP TUC dung khi GD2 GIO
   CUNG lam viec cat canh: khi CA logo/lop_phu/khung/lat-guong/dich-mau/phu-de
   VA phep cat cung bat, lenh ffmpeg cua GD2 van chi co **MOT** `-filter_complex`,
   **MOT** bo ma hoa hinh, **MOT** tep ra — VA GD1 lui ve REMUX (`-c copy`,
   ⛔ khong ma hoa) vi no khong con viec pixel nao. ⇒ **MOT lan ma hoa THAT cho
   ca lan chay**, khong phai hai (mot o GD1 dan logo, mot o GD2 cat).

   `vung` (lam mo/dien nen) VAN o GD1 — no khong chuyen (xem giao viec). Bai
   nay vi vay tach lam hai phan: GD1 (`vung`, van con) va GD2 (nam bien doi con
   lai, MOI).

⭐ Khang dinh DUONG: moi mat xich phai CO MAT trong chuoi loc duy nhat. Mot bai
   chi dem "khong qua mot `-c:v`" se xanh khi ai do lang le bo mot bien doi di
   (`banh-coc-do-su-vang-mat-thi-xoa-cung-xanh`).

⛔ Khong chay ffmpeg cau truc (phan 1/2). Bang chung may that — lenh nay CHAY,
   `returncode 0` — o phan 3 (`test_mot_luot_ffmpeg_THAT...`).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import (ban_dung, che_do_render as cdr,
                                  giai_doan_hinh_anh as gdha, ket_xuat, logo,
                                  lop_phu, phu_de)

GOC = Path(__file__).resolve().parents[1]
BANG_CHUNG = GOC / "docs/auto_scan_video_v6/bang_chung/bo_ma_hoa_20260911.json"

GOI = [{"start": 0.5, "end": 3.0, "text": "Phu de", "display_text": "Phu de",
        "line_count": 1, "scene_id": "s1", "index": 0}]

#: Mat xich cua tung bien doi trong chuoi loc GD2. Doi mot bo loc (vd `boxblur`
#: -> `gblur`) thi sua o day — va do la mot quyet dinh can noi ra, khong phai im.
#:
#: ⚠️ Logo KHONG danh dau bang `overlay`: `nen_mo` (khung) CUNG dung `overlay`
#:    de dan phan hinh giua len nen mo (`[kn2][kt2]overlay`). Nhan luong `[lg0]`
#:    moi la dau hieu RIENG cua logo.
MAT_XICH = {"khung": "[kn][kt]", "diem_anh": "hflip", "lop_phu": "drawtext",
           "logo": "[lg0]", "phu_de": "ass="}


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
                    su_kien=GOI),
    )


def _lenh(tmp_path, bd: dict, *, khoang=((0.0, 2.0), (2.5, 4.0))):
    lp = list(bd.get("lop_phu") or ())
    ds_logo = list(bd.get("ds_logo") or ())
    pd = bd.get("phu_de")
    duong_chu = lop_phu.viet_tep_chu(lp, tmp_path)
    duong_ass = phu_de.viet_tep_ass(pd, (pd or {}).get("su_kien") or [], tmp_path,
                                    rong=360, cao=640) if pd else ""
    return gdha.dung_lenh(
        "C:/t/gd1.mp4", "C:/t/ra.mp4", khoang=list(khoang), bo_ma_hoa="libx264",
        ffmpeg_bin="ffmpeg", bien_tap=bd.get("bien_tap"),
        rong_nguon=640, cao_nguon=360,
        ds_logo=ds_logo, duong_logo=["C:/t/logo.png"] * len(ds_logo),
        rong_khung=360, lop_phu=lp, duong_chu=duong_chu, cao_khung=640,
        duong_ass=duong_ass)


# ══ 1. GD2 — MOT lan ma hoa, voi CA NAM bien doi + phep cat ═══════════════════

def test_ca_nam_bien_doi_NAM_trong_MOT_filter_complex_GD2(tmp_path):
    bd = _ca_bon()
    cmd = _lenh(tmp_path, bd)

    assert cmd.count("-filter_complex") == 1, cmd
    fc = cmd[cmd.index("-filter_complex") + 1]
    thieu = [ten for ten, mat in MAT_XICH.items() if mat not in fc]
    assert not thieu, f"bien doi vang mat khoi chuoi loc duy nhat: {thieu}"
    # ⭐ VA phep CAT van co mat trong CUNG chuoi do — hai `trim`, mot `concat`.
    assert fc.count("[0:v]trim=") == 2 and "concat=n=2:v=1:a=1" in fc


def test_ca_nam_bien_doi_chi_MOT_bo_ma_hoa_hinh_va_MOT_tep_ra(tmp_path):
    """🔴 Hai `-c:v` hay hai tep ra la hai lan ma hoa — dung khoan no pha 26
       ton tai de tra, va GD2 la noi khoan no CHUYEN toi (gd2-diem-anh)."""
    bd = _ca_bon()
    cmd = _lenh(tmp_path, bd)
    bo = [cmd[i + 1] for i, x in enumerate(cmd) if x == "-c:v"]
    assert bo == ["libx264"], bo
    assert "copy" not in bo
    ra = [x for x in cmd if str(x).endswith(".mp4") and x != "C:/t/gd1.mp4"]
    assert ra == ["C:/t/ra.mp4"], ra


def test_phu_de_la_mat_xich_CUOI_tren_ca_logo_va_lop_phu(tmp_path):
    """⭐ Phu de la thu khach doc de HIEU; logo va lop phu la trang tri. Mot phu
       de bi logo de len la mot phu de khong doc duoc."""
    bd = _ca_bon()
    cmd = _lenh(tmp_path, bd)
    fc = cmd[cmd.index("-filter_complex") + 1]
    vi_tri = {ten: fc.rindex(mat) for ten, mat in MAT_XICH.items()}
    assert vi_tri["phu_de"] == max(vi_tri.values()), vi_tri
    # ⭐ Va logo/chu KHONG bi LAT: `hflip` (diem_anh) dat TRUOC ca hai — chung
    #    dan len tren mot khung DA lat, ⛔ khong bi ban than chung lat lai.
    assert vi_tri["diem_anh"] < vi_tri["logo"] < vi_tri["lop_phu"]
    assert vi_tri["khung"] < vi_tri["diem_anh"]


@pytest.mark.parametrize("bo_di", sorted(MAT_XICH))
def test_bo_mot_bien_doi_thi_mat_xich_do_VANG_ma_van_mot_lan_ma_hoa(tmp_path, bo_di):
    """Doi chung: moi mat xich xuat hien VI bien doi cua no, khong phai vi mot
    ly do khac. Bo mot bien doi thi dung mat xich do bien mat."""
    bd = _ca_bon()
    if bo_di in ("khung", "diem_anh"):
        # Ca hai cung tu `bien_tap`; bo TUNG TRUONG rieng de mat xich do vang
        # ma mat xich kia (con lai trong `bien_tap`) van con.
        bt = dict(bd["bien_tap"])
        if bo_di == "khung":
            bt.pop("khung")
        else:
            bt.pop("lat_guong")
            bt.pop("dich_mau")
        bd["bien_tap"] = bt
    else:
        bd.pop("ds_logo" if bo_di == "logo" else bo_di)
    cmd = _lenh(tmp_path, bd)
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert MAT_XICH[bo_di] not in fc
    assert cmd.count("-c:v") == 1


# ══ 2. GD1 — `vung` van o day, VA GD1 lui ve REMUX khi khong con gi khac ═════

def test_GD1_van_giu_vung__nhung_KHONG_con_logo_lop_phu_khung():
    """`ban_dung.dung()` GD1 KHONG con nhan `lop_phu`/`ds_logo` — TypeError neu
    goi voi chung, chot bang `inspect`."""
    import inspect

    tham = set(inspect.signature(ban_dung.dung).parameters)
    assert "lop_phu" not in tham and "ds_logo" not in tham
    assert "vung" in tham and "phu_de" in tham and "bien_tap" in tham


def test_GD1_REMUX_khi_khong_vung_khong_toc_do__du_preset_la_CAT():
    """🔑 Day la nua CON LAI cua "mot lan ma hoa": GD1 khong con dot logo/chu/
    phu de/doi khung, nen mot lan chay CHI dung nhung tinh nang do (khong
    vung, khong doi toc do) khong con ly do gi de GD1 ma hoa lai."""
    ban = ban_dung.dung(
        khoa_video="v/g.mp4", khoa_nen="n.wav", khoa_master="m.wav",
        ke_hoach={"doan": [{"ma": "s1", "dai_ms": 2000, "dat_tai_ms": 0,
                            "he_so_toc": 1.0}]},
        ban_ke_tieng={"doan": [{"ma": "s1", "khoa": "v/s1.wav"}]},
        phien_ban_ffmpeg="n8", tong_giay=4.0, che_do=cdr.CAT_MA_HOA_LAI,
        bo_ma_hoa="libx264", khoang_giu=[(0.0, 4.0)], preset="smart_localize",
        rong_khung=640, cao_khung=360)
    cmd = ket_xuat.dung_lenh(
        ban, ffmpeg_bin="ffmpeg", duong_video="C:/t/g.mp4",
        duong_master="C:/t/m.wav", duong_lop=["C:/t/s0.wav"],
        duong_ra="C:/t/ra.mp4", bo_ma_hoa="libx264")
    assert "-filter_complex" not in cmd
    assert cmd[cmd.index("-c:v") + 1] == "copy"


# ══ 3. MOT LUOT FFMPEG THAT — bang chung, khong suy luan ═════════════════════

def test_mot_luot_ffmpeg_THAT_GD1_remux_GD2_ma_hoa_MOT_lan(tmp_path):
    """🔴 Dem SO LAN ffmpeg thuc su MA HOA (co `-c:v <encoder>`, khong phai
    `copy`) qua CA HAI giai doan, tren mot nguon TONG HOP THAT.

    Kich ban: preset cat, KHONG vung, KHONG toc_do, CO logo + lat guong + cat
    canh — dung hinh dang "co phep doi diem anh VA co cat" ma chu du an mo ta
    la cai gia HAI lan ma hoa truoc lan tai cau truc nay.
    """
    ff = "ffmpeg"
    nguon = tmp_path / "nguon.mp4"
    r = subprocess.run(
        [ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
         "-i", "testsrc2=size=320x240:rate=25:duration=4",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
         "-c:v", "libx264", "-c:a", "aac", str(nguon)],
        capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr

    dem_ma_hoa = 0

    def _dem_va_chay(cmd):
        nonlocal dem_ma_hoa
        if "-c:v" in cmd and cmd[cmd.index("-c:v") + 1] != "copy":
            dem_ma_hoa += 1
        rr = subprocess.run([str(x) for x in cmd], capture_output=True, timeout=120)
        assert rr.returncode == 0, rr.stderr
        return rr

    # ── GD1: khong vung, khong toc_do -> REMUX ──────────────────────────────
    ban = ban_dung.dung(
        khoa_video="v", khoa_nen="n", khoa_master="m",
        ke_hoach={"doan": [{"ma": "s1", "dai_ms": 2000, "dat_tai_ms": 0,
                            "he_so_toc": 1.0}]},
        ban_ke_tieng={"doan": [{"ma": "s1", "khoa": "s1"}]},
        phien_ban_ffmpeg="n8", tong_giay=4.0, che_do=cdr.CAT_MA_HOA_LAI,
        bo_ma_hoa="libx264", khoang_giu=[(0.0, 4.0)], preset="smart_localize",
        rong_khung=320, cao_khung=240)
    master = tmp_path / "m.wav"
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                    "-i", "anullsrc=r=48000:cl=stereo", "-t", "4.0",
                    "-c:a", "pcm_s16le", str(master)], check=True,
                   capture_output=True)
    gd1 = tmp_path / "gd1.mp4"
    cmd1 = ket_xuat.dung_lenh(
        ban, ffmpeg_bin=ff, duong_video=str(nguon), duong_master=str(master),
        duong_lop=[str(master)], duong_ra=str(gd1), bo_ma_hoa="libx264",
        tien_do=False)
    _dem_va_chay(cmd1)
    assert dem_ma_hoa == 0, "GD1 khong vung/toc_do phai REMUX, khong ma hoa"

    # ── GD2: cat + logo + lat guong, MOT lan ma hoa ─────────────────────────
    lg = [logo.chuan_hoa_mot({"x": 0.75, "y": 0.05, "rong": 0.2,
                              "khoa": "logo/a.png"})]
    logo_png = tmp_path / "logo.png"
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                    "-i", "color=c=red:s=64x64", "-frames:v", "1", str(logo_png)],
                   check=True, capture_output=True)
    gd2 = tmp_path / "gd2.mp4"
    cmd2 = gdha.dung_lenh(
        str(gd1), str(gd2), khoang=[(0.0, 1.5), (2.0, 4.0)], bo_ma_hoa="libx264",
        ffmpeg_bin=ff, bien_tap={"lat_guong": True}, rong_nguon=320, cao_nguon=240,
        ds_logo=lg, duong_logo=[str(logo_png)], rong_khung=320, cao_khung=240,
        tien_do=False)
    _dem_va_chay(cmd2)
    assert dem_ma_hoa == 1, (
        "mot lan chay co phep doi diem anh VA phep cat phai ma hoa lai DUNG "
        f"MOT lan qua ca hai giai doan — do duoc {dem_ma_hoa}")
    assert gd2.is_file() and gd2.stat().st_size > 0


def test_mot_luot_ffmpeg_THAT_logo_KHONG_bi_lat_guong(tmp_path):
    """🔴 Do BANG DIEM ANH THAT (khong suy tu vi tri chuoi loc): nguon nua trai
    DO / nua phai XANH, lat guong o GD2 CUNG luot voi mot logo XANH LA o goc
    tren-trai. Sau khi ra, ⛔ hinh nen PHAI da lat (trai/phai doi mau) NHUNG
    logo PHAI VAN o goc tren-trai (⛔ khong nhay sang goc tren-phai) — dung
    thu tu `khung -> diem_anh (hflip) -> logo` ma `loc_cat_hai_dong` dung."""
    ff = "ffmpeg"
    nguon = tmp_path / "nguon.mp4"
    r = subprocess.run(
        [ff, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "color=c=red:s=160x240:d=2",
         "-f", "lavfi", "-i", "color=c=blue:s=160x240:d=2",
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-filter_complex", "[0:v][1:v]hstack,format=yuv420p[v]",
         "-map", "[v]", "-map", "2:a", "-t", "2",
         "-c:v", "libx264", "-c:a", "aac", str(nguon)],
        capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr

    logo_png = tmp_path / "logo_xanh_la.png"
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                    "-i", "color=c=lime:s=20x20", "-frames:v", "1", str(logo_png)],
                   check=True, capture_output=True)

    lg = [logo.chuan_hoa_mot({"x": 0.02, "y": 0.02, "rong": 0.0625,
                              "khoa": "logo/xanh_la.png"})]
    ra = tmp_path / "ra.mp4"
    cmd = gdha.dung_lenh(
        str(nguon), str(ra), khoang=[(0.0, 2.0)], bo_ma_hoa="libx264",
        ffmpeg_bin=ff, bien_tap={"lat_guong": True}, rong_nguon=320, cao_nguon=240,
        ds_logo=lg, duong_logo=[str(logo_png)], rong_khung=320, cao_khung=240,
        tien_do=False)
    r = subprocess.run([str(x) for x in cmd], capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr

    def _mau(x, y, w=8, h=8):
        rr = subprocess.run(
            [ff, "-hide_banner", "-loglevel", "error", "-ss", "1.0", "-i", str(ra),
             "-vf", f"crop={w}:{h}:{x}:{y}", "-frames:v", "1", "-f", "rawvideo",
             "-pix_fmt", "rgb24", "-"], capture_output=True, timeout=30)
        assert rr.returncode == 0, rr.stderr
        return rr.stdout[:3]

    # ⭐ Nen: DA lat — trai (nguon do) nay phai la XANH DUONG, phai (nguon xanh)
    #    nay phai la DO. Do la BANG CHUNG `hflip` THAT SU chay tren hinh nen.
    trai = _mau(8, 200)
    phai = _mau(304, 200)
    assert trai[2] > 200 and trai[0] < 50, f"goc duoi-trai phai la XANH DUONG: {trai}"
    assert phai[0] > 200 and phai[2] < 50, f"goc duoi-phai phai la DO: {phai}"

    # 🔴 Logo: VAN o goc tren-TRAI cua man hinh (toa do x=0.02 la toa do BAN
    #    RA, ap SAU hflip) — logo mau XANH LA, ⛔ khong bi chinh no lat lai va
    #    ⛔ khong nhay sang goc tren-phai.
    goc_trai = _mau(8, 8)
    goc_phai = _mau(304, 8)
    assert goc_trai[1] > 200 and goc_trai[0] < 50 and goc_trai[2] < 50, (
        f"logo phai o goc tren-TRAI (mau xanh la): {goc_trai}")
    assert not (goc_phai[1] > 200 and goc_phai[0] < 50 and goc_phai[2] < 50), (
        f"logo bi nhay/lat sang goc tren-phai: {goc_phai}")


# ══ 4. Thu tu bo ma hoa khop PHEP DO (khong doi, van chot o day) ═════════════

def _bc():
    return json.loads(BANG_CHUNG.read_text(encoding="utf-8"))


def test_bang_chung_ghi_nguong_TRUOC_va_nvenc_TUONG_DUONG():
    """🔑 Nguong chat luong duoc ghi TRUOC khi doc ket qua, va nam trong chinh
       tep bang chung — mot nguong dat sau khi nhin so la mot nguong ve quanh
       dich."""
    bc = _bc()
    assert bc["nguong_ghi_truoc"]["lech_ssim_toi_da"] == 0.010
    assert bc["phan_quyet"]["h264_nvenc"]["tuong_duong"] is True
    assert bc["ket_qua"]["libx264"]["trang_thai"] == "chay"


def test_thu_tu_uu_tien_PHAN_CUNG_truoc_duoc_phep_do_ung_ho():
    """⭐ Luat A (ghi truoc): giu phan cung truoc neu o 1080p bo phan cung chon
       tieu <= 0,5x CPU va <= 2,0x thoi gian cua libx264. Do: NVENC 0,21x CPU,
       0,67x thoi gian. Neu ai doi `UU_TIEN` dat libx264 len dau, bai nay do —
       va nguoi doi phai co mot phep do moi."""
    assert cdr.UU_TIEN[0] == "h264_nvenc"
    assert cdr.UU_TIEN[-1] == cdr.LUI_VE
    cpu = _bc()["gia_cpu_1080p"]
    assert cpu["h264_nvenc"]["cpu"] <= 0.5 * cpu["libx264"]["cpu"]
    assert cpu["h264_nvenc"]["wall"] <= 2.0 * cpu["libx264"]["wall"]


def test_moi_bo_da_do_moi_lenh_chi_MOT_c_v():
    for bo, v in _bc()["ket_qua"].items():
        if v.get("trang_thai") == "chay":
            assert v["so_co_c_v_trong_lenh"] == 1, bo
