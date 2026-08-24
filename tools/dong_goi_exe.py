"""dong_goi_exe.py - dung ban .exe cua GUI, va DO xem no co bi bao virus khong.

    python tools\\dong_goi_exe.py pyinstaller
    python tools\\dong_goi_exe.py nuitka
    python tools\\dong_goi_exe.py ca-hai --quet

* VI SAO KHONG DUNG `--onefile`, DU DICH LA "MOT TEP".

  Ca PyInstaller lan Nuitka o che do onefile deu TU GIAI NEN hang chuc DLL vao
  `AppData\\Local\\Temp` moi lan chay. Cong dong noi thang vi sao dieu do te:
  *"Malware does this constantly to hide its true payload."*

  Voi dung cong cu nay thi ho so hanh vi cang giong thu dang nghi: no GHI TEP
  CAU HINH trong thu muc nha va GIU MOT KHOA API. Ket qua thuc te: khach tai ve,
  bam vao, va thay canh bao virus - nguoc han voi muc tieu "nhin chuyen nghiep".

  => Dung che do THU MUC, roi boc bang mot installer. Khach van tai ve DUNG MOT
     TEP .exe, nhung do la TRINH CAI DAT: AV it bao hon, khoi dong nhanh hon, va
     co loi tat + trinh go cai - thu mot .exe tran khong co.

! VA VI SAO CO `--quet`. Du an nay co luat: CHUA DO THI KHONG CHAY. "Nuitka nghe
  an toan hon" khong phai mot so do. `MpCmdRun.exe` cua Windows Defender chay
  CUC BO, khong phai tai tep len dau ca, va Defender dung la thu quyet dinh voi
  da so nguoi dung Windows.

  Neu ca hai deu sach thi CHON PYINSTALLER - dung nhanh hon la loi ich THAT moi
  ngay, con "it bao gia hon ve ly thuyet" thi khong.
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

GOC = pathlib.Path(__file__).resolve().parents[1]
TOOLS = GOC / "tools"
#: Dat duoi `build/` co chu y: ten do DA nam trong EXCLUDED_DIR_NAMES
#: cua `scan_source_secrets.py` va da trong .gitignore. Them mot ngoai le
#: moi cho bo quet la noi rong no; doi mot duong dan thi re hon nhieu.
RA = GOC / "build" / "exe"
TEN = "LTTStudios-CamCLI"

DEFENDER = pathlib.Path(r"C:\Program Files\Windows Defender\MpCmdRun.exe")


def _chay(lenh, cwd=None) -> tuple[int, str]:
    """Chay mot lenh dung. **In ra khi that bai** - dung nuot.

    !! Ban dau ham nay bat het output roi chi tra ve ma thoat. Ket qua: mot lan
       dung hong in ra dung mot dong `ma=1` va KHONG GI KHAC - toi phai chay lai
       bang tay moi biet vi sao. Do la dung loai loi `check_silent_except.py`
       ton tai de chan, chi khac la no o trong mot script cong cu nen khong bi
       banh coc nao bat.
    """
    t = time.monotonic()
    r = subprocess.run(lenh, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    giay = f"{time.monotonic() - t:.0f}s"
    if r.returncode != 0:
        print(f"   --- lenh that bai (ma {r.returncode}) ---")
        for dong in ((r.stdout or "") + (r.stderr or "")).splitlines()[-25:]:
            print(f"   {dong}")
        print("   --- het ---")
    return r.returncode, giay


def _kich_thuoc(thu_muc: pathlib.Path) -> str:
    if not thu_muc.exists():
        return "-"
    n = sum(p.stat().st_size for p in thu_muc.rglob("*") if p.is_file())
    return f"{n / 1_048_576:.1f} MB"


def dung_pyinstaller() -> pathlib.Path | None:
    dich = RA / "pyinstaller"
    if dich.exists():
        shutil.rmtree(dich, ignore_errors=True)
    print("== PyInstaller (che do THU MUC, khong onefile) ==")
    ma, giay = _chay([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--name", TEN,
        "--windowed",                       # khong hien cua so console
        "--distpath", str(dich),
        "--workpath", str(RA / "_work_pyi"),
        "--specpath", str(RA / "_spec"),
        # `tools/gui/` phai di theo: index.html + ltt.css. Thieu no thi .exe chay
        # duoc nhung cua so trang - hong theo kieu kho doan nhat.
        "--add-data", f"{TOOLS / 'gui'}{';'}gui",
        "--add-data", f"{TOOLS / 'cam_cli.py'}{';'}.",
        str(TOOLS / "cam_cli_gui.py"),
    ], cwd=GOC)
    print(f"   ma={ma}  {giay}  kich thuoc={_kich_thuoc(dich)}")
    return (dich / TEN / f"{TEN}.exe") if ma == 0 else None


def dung_nuitka() -> pathlib.Path | None:
    dich = RA / "nuitka"
    if dich.exists():
        shutil.rmtree(dich, ignore_errors=True)
    dich.mkdir(parents=True, exist_ok=True)
    print("== Nuitka (standalone, khong onefile) ==")
    ma, giay = _chay([
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--windows-console-mode=disable",
        f"--output-dir={dich}",
        f"--output-filename={TEN}.exe",
        f"--include-data-dir={TOOLS / 'gui'}=gui",
        f"--include-data-files={TOOLS / 'cam_cli.py'}=cam_cli.py",
        str(TOOLS / "cam_cli_gui.py"),
    ], cwd=GOC)
    print(f"   ma={ma}  {giay}  kich thuoc={_kich_thuoc(dich)}")
    thu = list(dich.glob("*.dist"))
    return (thu[0] / f"{TEN}.exe") if (ma == 0 and thu) else None


ISCC = pathlib.Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe")


def dung_installer() -> pathlib.Path | None:
    """Boc ban THU MUC thanh MOT tep .exe cai dat.

    * Day la cach cho khach "mot tep" ma khong dinh cai gia cua onefile. Xem chu
      thich dau tep, va `tools/installer/cam_cli.iss`.
    """
    print("== Installer (Inno Setup) ==")
    if not ISCC.exists():
        print("   ISCC.exe khong co. Cai Inno Setup 6 tu jrsoftware.org.")
        return None
    nguon = RA / "pyinstaller" / TEN
    if not nguon.exists():
        print("   Chua co ban PyInstaller. Chay truoc:")
        print(r"     python tools\dong_goi_exe.py pyinstaller")
        return None
    ma, giay = _chay([str(ISCC), str(TOOLS / "installer" / "cam_cli.iss")], cwd=GOC)
    ra = sorted((RA / "installer").glob(f"{TEN}-Setup-*.exe")) if ma == 0 else []
    if ra:
        print(f"   ma={ma}  {giay}  {ra[-1].name}  "
              f"{ra[-1].stat().st_size / 1_048_576:.1f} MB")
        # ! KHONG KY SO (quyet dinh 24/08). Bam SHA-256 la thu DUY NHAT con lai
        #   de khach kiem tep dung la cua ta - nen phai in ra, va phai dang canh
        #   duong tai ve.
        import hashlib
        bam = hashlib.sha256(ra[-1].read_bytes()).hexdigest()
        print(f"   SHA256 = {bam}")
        print("   ^ dang bam nay CANH DUONG TAI VE. Khong ky so thi day la thu")
        print("     duy nhat khach dung de kiem tep dung la cua ta.")
        return ra[-1]
    print(f"   ma={ma}  {giay}  THAT BAI")
    return None


def quet(duong: pathlib.Path | None, nhan: str) -> None:
    """Quet bang Windows Defender - CUC BO, khong tai tep len dau ca."""
    if duong is None or not duong.exists():
        print(f"   {nhan:14} khong co tep de quet")
        return
    if not DEFENDER.exists():
        print(f"   {nhan:14} khong thay MpCmdRun.exe")
        return
    r = subprocess.run([str(DEFENDER), "-Scan", "-ScanType", "3",
                        "-File", str(duong.parent), "-DisableRemediation"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    ra = (r.stdout or "") + (r.stderr or "")
    sach = "found no threats" in ra.lower() or r.returncode == 0
    print(f"   {nhan:14} {'SACH' if sach else 'BI BAO'}  (ma {r.returncode})")
    if not sach:
        for d in ra.splitlines():
            if "Threat" in d or "found" in d.lower():
                print(f"      {d.strip()}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Dung .exe cho GUI cam_cli")
    ap.add_argument("bo", choices=["pyinstaller", "nuitka", "ca-hai", "installer"])
    ap.add_argument("--quet", action="store_true",
                    help="quet bang Windows Defender sau khi dung")
    a = ap.parse_args(argv)

    RA.mkdir(parents=True, exist_ok=True)
    kq = {}
    if a.bo in ("pyinstaller", "ca-hai"):
        kq["pyinstaller"] = dung_pyinstaller()
    if a.bo in ("nuitka", "ca-hai"):
        kq["nuitka"] = dung_nuitka()
    if a.bo == "installer":
        kq["installer"] = dung_installer()

    if a.quet:
        print("\n== Quet Windows Defender (cuc bo) ==")
        for ten, duong in kq.items():
            quet(duong, ten)

    print("\n== Ket qua ==")
    for ten, duong in kq.items():
        print(f"   {ten:14} {duong if duong else 'DUNG THAT BAI'}")
    return 0 if all(kq.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
