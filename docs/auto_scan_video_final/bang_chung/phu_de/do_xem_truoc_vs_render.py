"""Bang chung lan phu-de (asv-final): XEM TRUOC == RENDER, tung diem anh.

Chay tu goc cay:  python docs/auto_scan_video_final/bang_chung/phu_de/do_xem_truoc_vs_render.py <thu_muc_tam>
Chi DOC video trong Desktop\\TEST VIDEO. Ghi `xem_truoc_vs_render.json` canh tep nay.

Moi che do (tat/tu_dong/nguon/dich/tu_chon) di HAI duong doc lap:

  XEM TRUOC  phu_de.xem_truoc_tu_form(...)           (dung cua HTTP /phu-de/xem-truoc)
  RENDER     phu_de.chuan_hoa -> chot_o_compose (ke hoach + van ban tren TRUC RA,
             co mot khoang CAT) -> viet_tep_ass -> che_do_render.loc_cat_noi
             -> ma hoa KHONG MAT (png/rgb24) -> giai ma khung o cung do lech
             trong su kien

roi so sanh hai khung bang mang diem anh (loai A: so hoc tren diem anh).
Them mot duong THAT: video goc yuv420p + libx264 (tham so LUI_VE cua render) de
do PSNR giua xem truoc va ban ma hoa that (khac biet chi do ma hoa + lay mau mau).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

GOC = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(GOC))

from apps.auto_scan_video import che_do_render as cdr  # noqa: E402
from apps.auto_scan_video import phu_de  # noqa: E402
from apps.auto_scan_video.hop_dong_v4 import PRESET_CAT_THONG_MINH as PRESET_CAT  # noqa: E402

TAM = Path(sys.argv[1])
TAM.mkdir(parents=True, exist_ok=True)
VIDEO = sorted(Path(r"C:\Users\Thang Tuong\Desktop\TEST VIDEO").glob("*.mp4"))[1]  # v2
GIAY_NGUON = 30.0
FPS = 25
# Dai hardsub v2 do bang do_dai_hardsub.py: 0,909-0,971. Danh dau rong hon 0,005.
VUNG = [{"loai": "danh_dau_phu_de", "x0": 0.1, "x1": 0.9, "y0": 0.904, "y1": 0.976}]
KHOANG = [(0.0, 1.0), (2.0, 4.0)]       # cat bo 1..2 s cua nguon
SU_KIEN_BAT_MS = 1000                    # tren TRUC RA = giay 2.0 cua nguon
T_RA = SU_KIEN_BAT_MS / 1000 + phu_de.XEM_TRUOC_GIAY

CHE_DO = {
    "tat": {"che_do": "tat", "xuat_srt": True},
    "tu_dong": {"che_do": "tu_dong"},
    "nguon": {"che_do": "nguon"},
    "dich": {"che_do": "dich"},
    "tu_chon": {"che_do": "tu_chon", "kieu": "tiktok_bold", "chu": "nguon",
                "tinh_chinh": {"font_size": 40, "font_color": "#FFE000",
                               "outline_width": 4, "alignment": 8}},
}


def ff(*a):
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", *a], check=True)


def mang(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.int16)


def psnr(a, b):
    mse = float(((a - b) ** 2).mean())
    return 99.0 if mse == 0 else round(10 * np.log10(255 ** 2 / mse), 2)


khung = TAM / "khung.png"
ff("-ss", str(GIAY_NGUON), "-i", str(VIDEO), "-frames:v", "1", "-pix_fmt", "rgb24", str(khung))
rong, cao = Image.open(khung).size
# Video KHONG MAT dung tu chinh khung do: 4 s, 25 fps, ffv1 o DINH_DANG_VAO (yuv420p) —
# cung phep doi ma xem truoc dung (`phu_de.lenh_xem_truoc` buoc 1), vi render that
# doc h264 yuv420p.
nguon_km = TAM / "nguon_km.mkv"
ff("-loop", "1", "-framerate", str(FPS), "-t", "4", "-i", str(khung),
   "-pix_fmt", phu_de.DINH_DANG_VAO, "-c:v", "ffv1", str(nguon_km))
# Video THAT: 4 s cua v2. Khung so sanh = giay NGUON 3.0 cua doan = giay RA 2.0 (sau cat 1..2 s).
nguon_that = TAM / "nguon_that.mp4"
ff("-ss", str(GIAY_NGUON - 2.0), "-i", str(VIDEO), "-t", "4", "-an", "-r", str(FPS),
   "-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv420p", str(nguon_that))
khung_that = TAM / "khung_that.png"
ff("-i", str(nguon_that), "-vf", f"select=eq(n\\,{int(round((2.0 + phu_de.XEM_TRUOC_GIAY) * FPS))})", "-frames:v", "1",
   "-pix_fmt", "rgb24", str(khung_that))

ke_hoach = {"doan": [{"ma": "d1", "dat_tai_ms": SU_KIEN_BAT_MS, "dai_ms": 4000}]}
van_ban = {"muc": [{"ma": "d1", "goc": phu_de.CAU_MAU["zh"], "chu": phu_de.CAU_MAU["vi"]}]}

ket = {"video": VIDEO.name[:20], "khung": [rong, cao], "giay_nguon": GIAY_NGUON,
       "khoang_giu": KHOANG, "t_ra": T_RA, "vung": VUNG, "che_do": {}}
anh_xt = {}
for ten, tho in CHE_DO.items():
    d = TAM / ten
    d.mkdir(exist_ok=True)
    # ── XEM TRUOC ─────────────────────────────────────────────────────────
    png = phu_de.xem_truoc_tu_form(json.dumps(tho), anh=khung.read_bytes(),
                                   vung=json.dumps(VUNG), preset=PRESET_CAT,
                                   nguon="zh", dich="vi")
    (d / "xem_truoc.png").write_bytes(png)
    # ── RENDER (COMPOSE -> RENDER that) ───────────────────────────────────
    ho = phu_de.chuan_hoa(tho)
    ho = phu_de.chot_o_compose(ho, ke_hoach=ke_hoach, van_ban=van_ban, vung=VUNG)
    ass = phu_de.viet_tep_ass(ho, ho["su_kien"], d, rong=rong, cao=cao)
    loc = cdr.loc_cat_noi(KHOANG, vung=VUNG, duong_ass=ass)
    ra = d / "render.mov"
    ff("-i", str(nguon_km), "-filter_complex", loc, "-map", "[ra]",
       "-c:v", "png", "-pix_fmt", "rgb24", str(ra))
    kr = d / "render_khung.png"
    ff("-i", str(ra), "-vf", f"select=eq(n\\,{int(round(T_RA * FPS))})", "-frames:v", "1",
       "-pix_fmt", "rgb24", str(kr))
    # ── RENDER THAT: yuv420p + libx264 LUI_VE ─────────────────────────────
    ra2 = d / "render_that.mp4"
    ff("-i", str(nguon_that), "-filter_complex", loc, "-map", "[ra]",
       *cdr.tham_so(cdr.LUI_VE), str(ra2))
    kr2 = d / "render_that_khung.png"
    ff("-i", str(ra2), "-vf", f"select=eq(n\\,{int(round(T_RA * FPS))})", "-frames:v", "1",
       "-pix_fmt", "rgb24", str(kr2))
    # xem truoc tren khung CUA VIDEO THAT (cung khung da giai ma) de so PSNR
    png2 = phu_de.xem_truoc_tu_form(json.dumps(tho), anh=khung_that.read_bytes(),
                                    vung=json.dumps(VUNG), preset=PRESET_CAT,
                                    nguon="zh", dich="vi")
    (d / "xem_truoc_that.png").write_bytes(png2)

    a, b = mang(d / "xem_truoc.png"), mang(kr)
    a2, b2 = mang(d / "xem_truoc_that.png"), mang(kr2)
    anh_xt[ten] = a
    ket["che_do"][ten] = {
        "ho_so_render": {k: v for k, v in ho.items() if k != "su_kien"},
        "su_kien_chu": [s["text"] for s in ho["su_kien"]],
        "khong_mat_diem_anh_khac": int((a != b).any(axis=2).sum()),
        "khong_mat_sai_lon_nhat": int(np.abs(a - b).max()),
        "md5_xem_truoc": hashlib.md5(a.astype(np.uint8).tobytes()).hexdigest(),
        "md5_render": hashlib.md5(b.astype(np.uint8).tobytes()).hexdigest(),
        "that_psnr_db": psnr(a2, b2),
    }
    print(ten, json.dumps(ket["che_do"][ten]["khong_mat_diem_anh_khac"]),
          ket["che_do"][ten]["that_psnr_db"])

# Moi che do DOI ban ra: ti le diem anh khac nhau tung cap.
ten = list(anh_xt)
tong = anh_xt[ten[0]].shape[0] * anh_xt[ten[0]].shape[1]
ket["khac_tung_cap_phan_tram"] = {
    f"{x}|{y}": round(100 * float((anh_xt[x] != anh_xt[y]).any(axis=2).sum()) / tong, 3)
    for i, x in enumerate(ten) for y in ten[i + 1:]}
# Dai phu de goc con doc duoc khong: diem "chu trang vien den" trong dai, truoc/sau.
y0, y1 = int(0.909 * cao), int(0.971 * cao)


def chu_trong_dai(arr):
    g = arr.mean(axis=2)
    return round(float(((g[y0:y1, int(rong * .2):int(rong * .8)] >= 200)).mean()), 4)


ket["ti_le_diem_sang_trong_dai_hardsub"] = {
    "khung_goc": chu_trong_dai(mang(khung)),
    **{k: chu_trong_dai(v) for k, v in anh_xt.items()}}
Path(__file__).with_name("xem_truoc_vs_render.json").write_text(
    json.dumps(ket, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(ket["khac_tung_cap_phan_tram"], indent=1))
print(json.dumps(ket["ti_le_diem_sang_trong_dai_hardsub"], indent=1))
