"""Sinh TAI NGUYEN cho nghiem thu tinh nang ASV (B7) — logo, lop chu, ...

⛔ **Vi sao mot BO SINH chu khong mot tep commit vao kho.**
   `tests/fixtures/asv_e2e_that/.gitignore` chan `*` CO CHU Y: thu muc ay giu tu
   lieu cua KHACH, va mot tep da vao lich su git thi con o do sau khi bi xoa. Nen
   tai nguyen thu phai **tai tao duoc**, ⛔ khong phai **duoc luu**.

⭐ **Va logo phai DO DUOC den pixel.** Chu du an chon nghiem thu tren phim Trung
   THAT, nen ⛔ khong co moc dung san. Bu lai bang cach chon MAU: magenta thuan
   (`#FF00FF`) gan nhu ⛔ khong ton tai trong phim thuc, nen tim no tren khung ra
   la mot phep **mat na mau**, ⛔ khong phai mot phep "trong co ve dung". Vien
   trang cho ta do duoc BE RONG logo, tuc kiem duoc `rong` (phan so) da ap dung.

Chay:  python tools/asv_tao_tai_nguyen_thu.py [--ra <thu_muc>]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
# ⭐ Khuon chung cua `tools/` (vd `ab_lay_mau_35.py:53`): console Windows mac dinh
#    la cp1252 va se NEM o mot ky tu nhu "⭐". Mot cong cu trong kho ⛔ khong duoc
#    doi noi goi phai dat `PYTHONIOENCODING`.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RA_MAC_DINH = GOC / "tests" / "fixtures" / "asv_e2e_that" / "tai_nguyen"

#: ⭐ Magenta thuan: kenh U va V deu lech xa nen tu nhien. Do duoc tren khung ra
#:    bang `signalstats` hay mot mat na mau, ⛔ khong can khop mau hinh anh.
MAU_LOGO = "0xFF00FF"
#: Vien trang day 16 px tren canh 240 px ⇒ ti le vien 1/15, do duoc sau khi logo
#: bi thu nho theo `rong`.
CANH = 240
VIEN = 16


def chay(cmd: list[str]) -> None:
    r = subprocess.run([str(x) for x in cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    if r.returncode != 0:
        raise SystemExit("ffmpeg loi: " + (r.stderr or "")[-500:])


def tao_logo(ra: Path) -> Path:
    """Logo vuong magenta co vien trang. ⛔ Khong `drawtext`: no can fontconfig,
    va fontconfig tren may nay bao loi (`Cannot load default config file`) —
    mot tai nguyen thu ⛔ khong duoc phu thuoc vao thu dang hong."""
    dich = ra / "logo_do_duoc.png"
    chay(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
          "-f", "lavfi", "-i", f"color=c={MAU_LOGO}:s={CANH}x{CANH}:d=1",
          "-frames:v", "1",
          "-vf", (f"drawbox=x=0:y=0:w={CANH}:h={CANH}:"
                  f"color=white@1.0:t={VIEN}"),
          str(dich)])
    return dich


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ra", default=str(RA_MAC_DINH))
    a = p.parse_args(argv)
    ra = Path(a.ra)
    ra.mkdir(parents=True, exist_ok=True)

    logo = tao_logo(ra)
    tt = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=width,height,pix_fmt", "-of", "default=nw=1", str(logo)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("logo :", logo)
    for d in (tt.stdout or "").splitlines():
        print("      ", d)
    print("\n⭐ Thu muc nay GITIGNORED co chu y — chay lai lenh nay de tai tao.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
