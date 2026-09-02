"""check_bien_dich.py - moi tep .py trong cay phai BIEN DICH DUOC.

    python tools\\check_bien_dich.py

🔴 VI SAO CHOT NAY TON TAI - MOT LO THAT, TIM RA 24/08.

   Toi commit `platform_core/public_api/examples.py` voi mot chuoi khong dong
   ngoac (ky tu xuong dong bi nuot khi va tep), va `gate.py --quick` van bao
   **PASS 14/14**. Ma hong nam trong git, va khong chot nao keu.

   Vi sao ca 14 buoc deu bo lot:

     · `--quick` **bo pytest day du** - do la ca muc dich cua no;
     · `check_undefined_names`, `check_silent_except`, `check_i18n` deu **bo qua**
       tep khong parse duoc thay vi bao do (chung dem *xu huong*, nen mot tep
       hong chi la mot tep bi tru khoi phep dem);
     · cac buoc con lai (secret scan, postman, SDK, frontend) khong cham toi
       module do.

⭐ NEN CHOT NAY KHONG DEM GI CA. No chi hoi mot cau, va la cau re nhat trong ca
   gate: **tep nay co bien dich duoc khong?** Mot cau tra loi "khong" thi khong
   co phep do nao khac con y nghia.

⛔ VA DUNG THAY NO BANG "chay pytest la biet": pytest chi import nhung module ma
   test cham toi. Mot module chi duoc goi tu duong web se hong lang le cho toi
   khi co khach mo dung trang do.
"""
from __future__ import annotations

import pathlib
import py_compile
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

GOC = pathlib.Path(__file__).resolve().parents[1]

#: Thu muc bo qua. Giu HEP: moi cai o day la mot vung ma khong ai kiem.
#: `core/` da dong bang (xem CLAUDE.md) nhung van phai bien dich duoc.
BO_QUA = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    "node_modules", "build", "dist", "data", "logs", "secrets",
    ".backup_", "cutclipshort",          # vendor
    # 🔴 `.claude/worktrees/<ten>/` la CAY LAM VIEC CUA PHIEN KHAC, long ngay
    #    ben trong cay chinh. Chot nay la chot duy nhat quet ca cay tu goc, nen
    #    no la chot duy nhat di lac vao do.
    #
    #    Do 2026-09-02: cay chinh do o `bien dich duoc` vi mot tep dang viet do
    #    cua phien khac chua null byte. Thong bao chi thang mot tep ma phien doc
    #    no **khong so huu va khong sua duoc**.
    #
    # ⛔ Vi sao te hon mot phut mat thi gio: `bien dich duoc` la CONG GAC — no
    #    chay MOT MINH va truoc het, va khi no do thi ca luot dung lai. Mot
    #    phien khac go phim la du de chan luot do cua ta.
    #
    # ⭐ Va no day dung cai phan xa nguy hiem nhat: mot chot do vi ly do khong
    #    lien quan se day nguoi ta bo qua chinh no, roi toi luc no do vi ly do
    #    that thi khong ai con nhin.
    #
    # ⚠️ Khong mat che phu: `.claude/` nam trong `.gitignore` (dong 96) VA
    #    trong danh sach `/XD` cua robocopy, nen khong tep nao o do vao git hay
    #    len production.
    ".claude",
}


def bo_qua(p: pathlib.Path) -> bool:
    return any(phan in BO_QUA or phan.startswith(".backup_")
               for phan in p.relative_to(GOC).parts)


def main() -> int:
    hong = []
    n = 0
    for tep in GOC.rglob("*.py"):
        if bo_qua(tep):
            continue
        n += 1
        try:
            py_compile.compile(str(tep), doraise=True, cfile=None)
        except py_compile.PyCompileError as e:
            hong.append((tep.relative_to(GOC), str(e).splitlines()[-1].strip()))
        except OSError as e:
            hong.append((tep.relative_to(GOC), f"khong doc duoc: {e}"))

    print(f"Tep .py da kiem: {n} | hong: {len(hong)}")
    for duong, vi_sao in hong:
        print(f"[LOI] {duong}: {vi_sao}")
    if hong:
        print("\nMot tep khong bien dich duoc thi moi phep do khac deu vo nghia.")
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
