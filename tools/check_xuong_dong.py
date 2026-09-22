"""check_xuong_dong.py - mot tep dang sua khong duoc DOI KIEU XUONG DONG.

    python tools\\check_xuong_dong.py

================================================================================
VI SAO CAN, VA VI SAO NO KHONG PHAI "CA KHO DUNG LF"

Tren Windows, `Path.write_text(...)` dich `\\n` thanh `\\r\\n`. Nen mot script sua
mot dong trong mot tep lon se ghi lai **ca tep**, va `git diff` cua no khong con
doc duoc.

Do that trong du an nay, hai lan:

  26/08  `test_306` ghi lai `messages.po` bang `write_text` -> ban "khoi phuc"
         khac ban goc **10.465 dong**. `git status` cua bat ky ai chay pytest
         bong ban, va `gate.py` in "CAY DA DOI TRONG LUC CHAY" vi dau van tay
         cay doi o ca hai dau. Sua bang `write_bytes`.

  30/08  Cung loi, **25 tep** cung luc, tu mot phien khac:
             5.356 dong nhieu che 266 dong that
             CLAUDE.md              919 dong -> that su 1
             setup/2-cai-dat.ps1  1.211      -> that su 69
         Mot dong thay doi that lan trong 918 dong nhieu thi nguoi duyet se cuon
         qua ca hai.

⛔ NHUNG LUAT KHONG PHAI "MOI TEP DUNG LF" — VA CHO NAY DA SUYT SAI.

   Khi don 25 tep tren, phien do chay mot luot "tra moi tep ve LF" roi kiem lai
   va thay **hai tep von LA CRLF trong git**:

       docs/PUBLIC_API/DEVELOPER_GUIDE.md   721 CRLF  (do build_public_api_docs sinh)
       tools/i18n_baseline.json             118 CRLF

   Ep chung ve LF la **doi thu khong nen doi**, va lan sau cong cu sinh ra chung
   se lai doi nguoc — mot vong lap khong ai thang.

⭐ NEN LUAT DUNG LA: **khop dung thu git dang giu cho TUNG tep.** Va cach re nhat
   de biet khong phai la nho mot quy uoc, ma la **hoi git**.

! Chi soi tep DANG SUA (`git status`). Tep chua doi thi khong co gi de so, va tep
  moi thi chua co ban o HEAD de lam chuan.
"""
from __future__ import annotations

import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

#: Duoi tep nhi phan — dem CRLF trong do la vo nghia.
NHI_PHAN = (".mo", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip",
            ".exe", ".dll", ".pyd", ".woff", ".woff2", ".ttf", ".mp4", ".wav")


def _git(*doi_so) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *doi_so], capture_output=True, timeout=60)


def _dem_crlf(b: bytes) -> tuple:
    """`(so_crlf, so_lf_don)`. Tach hai loai de phan biet 'tron' voi 'thuan'."""
    crlf = b.count(b"\r\n")
    return crlf, b.count(b"\n") - crlf


def _dang_hoa() -> bool:
    """Cay co dang o giua mot luot `git merge` khong."""
    r = _git("rev-parse", "--verify", "--quiet", "MERGE_HEAD")
    return r.returncode == 0 and bool(r.stdout.strip())


def main() -> int:
    r = _git("status", "--porcelain")
    if r.returncode != 0:
        print("khong chay duoc git status - bo qua (khong phai loi)")
        return 0

    hoa = _dang_hoa()
    lech = []
    for dong in r.stdout.decode("utf-8", "replace").splitlines():
        if len(dong) < 4:
            continue
        trang_thai, ten = dong[:2], dong[3:].strip().strip('"')
        if "?" in trang_thai or "D" in trang_thai:
            continue                      # tep moi / da xoa: khong co chuan de so
        if ten.lower().endswith(NHI_PHAN):
            continue
        cu = _git("show", f"HEAD:{ten}")
        if cu.returncode != 0:
            continue                      # chua co o HEAD
        try:
            with open(ten, "rb") as fh:
                moi_b = fh.read()
        except OSError:
            continue

        crlf_cu, lf_cu = _dem_crlf(cu.stdout)
        crlf_moi, lf_moi = _dem_crlf(moi_b)
        if not crlf_cu and not lf_cu:
            # Tep cu KHONG co dong nao (rong, vd `__init__.py` trong) thi chua
            # co kieu nao de lat — ghi noi dung dau tien vao khong phai "lat".
            continue
        # So KIEU, khong so so luong: them dong that thi ca hai con so deu tang.
        # Kieu doi khi mot tep thuan LF thanh thuan CRLF hoac nguoc lai.
        thuan_cu = "CRLF" if crlf_cu and not lf_cu else ("LF" if lf_cu and not crlf_cu else "tron")
        thuan_moi = "CRLF" if crlf_moi and not lf_moi else ("LF" if lf_moi and not crlf_moi else "tron")
        if thuan_cu != thuan_moi and hoa:
            # \U0001F534 **Giua mot luot HOA, `HEAD` la cha THU NHAT.**
            #
            #    Nhanh kia mang kieu xuong dong cua no vao, va do la dieu DUNG:
            #    ban hoa phai giong ban ta hoa vao. Neu chot chi biet `HEAD` thi
            #    khong luot hoa nao giua hai nhanh khac kieu commit duoc — va
            #    "sua" theo loi khuyen cua chot se lam cay LECH voi nhanh kia.
            #
            # \u2b50 No van bat dung cai no sinh ra de bat: mot tep bi `write_text`
            #    lat kieu se khong khop cha NAO, nen van bi bao.
            kia = _git("show", f"MERGE_HEAD:{ten}")
            if kia.returncode == 0:
                crlf_kia, lf_kia = _dem_crlf(kia.stdout)
                thuan_kia = ("CRLF" if crlf_kia and not lf_kia
                             else ("LF" if lf_kia and not crlf_kia else "tron"))
                if thuan_moi == thuan_kia:
                    continue
        if thuan_cu != thuan_moi:
            that = _git("diff", "--ignore-cr-at-eol", "--numstat", "--", ten)
            # ⭐ `--numstat` RONG chinh la ca dang noi nhat: bo qua CR thi
            #    KHONG con thay doi nao — tuc ca diff la nhieu. In "0" chu dung
            #    in "?", vi "0 dong that" moi la cau lam nguoi doc hieu ngay.
            so_that = "0"
            if that.returncode == 0 and that.stdout.strip():
                cot = that.stdout.decode("utf-8", "replace").split()
                if len(cot) >= 2:
                    so_that = str(int(cot[0]) + int(cot[1]))
            elif that.returncode != 0:
                so_that = "?"
            lech.append((ten, thuan_cu, thuan_moi, so_that))

    if not lech:
        print("Khong tep nao doi kieu xuong dong.")
        print("RESULT: PASS")
        return 0

    print(f"Doi KIEU XUONG DONG o {len(lech)} tep:\n")
    for ten, cu, moi, so_that in lech:
        print(f"  {ten}")
        print(f"     HEAD={cu}  ->  hien tai={moi}   "
              f"(thay doi THAT: {so_that} dong)")
    print("\nMot tep bi ghi lai toan bo se lam `git diff` khong doc duoc, va")
    print("`gate.py` in \"CAY DA DOI TRONG LUC CHAY\" vi dau van tay cay doi.")
    print("\nSua: ghi lai voi DUNG kieu HEAD dang giu, vi du")
    print('  p.write_text(p.read_text(encoding="utf-8"), encoding="utf-8", newline="\\n")')
    print("\n⛔ DUNG ep moi tep ve LF: mot so tep von LA CRLF trong git")
    print("   (vd DEVELOPER_GUIDE.md do cong cu sinh ra). Khop tung tep.")
    print("RESULT: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
