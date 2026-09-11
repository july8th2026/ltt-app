r"""Bat ky tu dieu khien vo hinh trong tai lieu — SOM, truoc khi no vao commit.

VI SAO CAN, VA VI SAO `test_61` CHUA DU
=======================================

`test_61::test_doc_has_no_invisible_control_characters` da quet dung dai ky tu
nay tu lau. No van o nguyen do va van dang canh — dung go no. Cai thieu la HAI
thu khac:

1. **Pham vi.** `test_61` dung `DOC_DIR.glob("*.md")` — KHONG de quy. No phu 43
   tep o `docs/` cap tren cung, va bo qua `docs/admin_mvp_v3/`, `docs/PUBLIC_API/`,
   `docs/nexus/`, `docs/VLM_NOI_BO/`, `CLAUDE.md`, `AGENTS.md`... Mot tai lieu
   hong trong thu muc con di qua ma khong ai thay.

2. **Thoi diem.** No chay o pha test, tuc vai phut sau khi tep da hong — va
   ngay 2026-08-29 no bat dung BA lan trong mot ngay, moi lan sau khi thiet hai
   da xay ra. Buoc gate chay trong `--vong-lap` (~15 giay) bat som hon nhieu.

NGUON GOC — ba lan trong mot ngay, cung mot co che
==================================================

Viet duong dan Windows trong mot chuoi Python KHONG phai raw-string:

    "C:\\LTTPlatform\\app.previous"   ->  `\a` = BEL (0x07)

`\app.previous` bi Python doc thanh escape. Mat thuong khong thay gi. Ba lan
deu la `\a`, nhung dai nay con nhieu bay khac va kho nay dung DUNG nhung chuoi
do trong tai lieu:

    \b -> `\backup`    \f -> `\files`    \v -> `\venv`

`\venv` va `\backup` xuat hien khap tai lieu cua kho nay, nen chan mot minh
`\x07` la chan dung cai vua no chu khong phai cai lop.

⛔ CACH DUNG DE TRANH, khong phai cach de "sua sau": ghi ra tep `.py` roi chay
   (quy tac 3 cua CLAUDE.md), va dung raw-string `r"..."` cho MOI duong dan
   Windows. Neu phai ghi tep bang Python thi dung `read_bytes`/`write_bytes` —
   che do van ban con dien giai ca ket thuc dong.

Chay:
    python tools/check_ky_tu_dieu_khien.py
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Duoi tep duoc quet. Chi tai lieu va cau hinh dang van ban — ma nguon da co
#: `check_bien_dich` va linter rieng, va mot ky tu dieu khien trong ma se lam
#: Python vo ngay chu khong nam im.
DUOI = (".md", ".txt")

#: Cho phep dung ba ky tu nay. Giong het `test_61` — hai tang phai noi cung mot
#: dinh nghia, neu khong thi mot tang xanh mot tang do va khong ai biet tin cai
#: nao.
CHO_PHEP = "\n\r\t"

#: Tep sinh tu dong hoac chua du lieu do, khong phai tai lieu nguoi viet.
BO_QUA = (
    "locale/",                     # catalog dich
    "node_modules/",
)


def _tep_can_quet() -> list[pathlib.Path]:
    """Moi tep van ban ma GIT dang theo doi.

    Dung `git ls-files` chu khong `rglob`: no tu loai `node_modules/`, `vendor/`
    va moi thu trong `.gitignore` ma khong phai bao tri mot danh sach loai tru
    thu hai — mot danh sach nhu the se lech khoi `.gitignore` trong vong mot
    thang.
    """
    ra = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                        capture_output=True, timeout=60)
    if ra.returncode != 0:
        print("Khong chay duoc `git ls-files` — bo qua buoc nay.")
        return []
    tep = []
    for ten in ra.stdout.decode("utf-8", "replace").split("\0"):
        if not ten or not ten.endswith(DUOI):
            continue
        if any(bo in ten for bo in BO_QUA):
            continue
        tep.append(ROOT / ten)
    return tep


def _dong_cot(text: str, vi_tri: int) -> tuple[int, int]:
    dau = text.rfind("\n", 0, vi_tri) + 1
    return text.count("\n", 0, vi_tri) + 1, vi_tri - dau + 1


def quet(tep: pathlib.Path) -> list[tuple[int, int, str]]:
    try:
        text = tep.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    ra = []
    for i, c in enumerate(text):
        n = ord(c)
        if (n < 32 and c not in CHO_PHEP) or n == 0x7F:
            dong, cot = _dong_cot(text, i)
            ra.append((dong, cot, f"0x{n:02x}"))
    return ra


def _tep_tu_doi_so(doi_so: list[str]) -> list[pathlib.Path]:
    """Chi nhung tep duoc DUA VAO, da loc theo `DUOI` va `BO_QUA`.

    🔑 **Duong nay ton tai cho `pre-commit`, va no khac duong cua gate o mot
       cho co that.**

       Gate hoi *"ca kho co sach khong"* — no phai quet het. `pre-commit` hoi
       *"lan commit nay co dua vao mot ky tu dieu khien khong"*, va cau ay chi
       phu thuoc nhung tep DANG duoc commit.

    ⭐ Va khac biet ay DO DUOC (10/09, 955 tep duoc git theo doi):

           ca kho          0,85 giay
           hai tep .md     0,06 giay

       Tep `.pre-commit-config.yaml` mo dau bang mot cau: *"moi hook o day phai
       NHANH"*. Tong bon hook hien co la 0,6 giay; them 0,85 giay la tang gap
       hai ruoi, va mot cong cham la mot cong se bi `--no-verify` mot lan roi
       bi go mai.

    ⚠️ Tep khong ton tai bi BO QUA im lang: `pre-commit` co the dua vao mot
       duong vua bi xoa trong cung lan commit, va do khong phai loi.
    """
    ra = []
    for ten in doi_so:
        if not ten.endswith(DUOI):
            continue
        if any(bo in ten.replace("\\", "/") for bo in BO_QUA):
            continue
        p = pathlib.Path(ten)
        if not p.is_absolute():
            p = ROOT / ten
        if p.is_file():
            ra.append(p)
    return ra


def main(doi_so: list[str] | None = None) -> int:
    # ⛔ Doi so RONG khong phai la "quet ca kho". `pre-commit` voi
    #    `pass_filenames: true` co the goi ma khong co tep nao khop bo loc, va
    #    khi do dung viec la KHONG QUET GI — quet ca kho o do se bien mot hook
    #    0,01 giay thanh 0,90 giay o dung nhung commit khong lien quan.
    #
    # ⇒ `None` (khong ai truyen gi) = gate, quet het.
    #   `[]` (truyen mot danh sach rong) = khong co gi de quet.
    if doi_so is None:
        tep = _tep_can_quet()
    else:
        tep = _tep_tu_doi_so(doi_so)
    loi = []
    for f in tep:
        for dong, cot, ma in quet(f):
            loi.append((f.relative_to(ROOT).as_posix(), dong, cot, ma))

    if loi:
        print(f"KY TU DIEU KHIEN trong {len({x[0] for x in loi})} tep:")
        for ten, dong, cot, ma in loi[:20]:
            print(f"  {ten}:{dong}:{cot}  {ma}")
        if len(loi) > 20:
            print(f"  ... va {len(loi) - 20} cho nua")
        print()
        print("Gan nhu chac chan la duong dan Windows trong chuoi Python KHONG")
        print("raw: `\\app.previous` -> BEL, `\\venv` -> VT, `\\backup` -> BS.")
        print("Sua bang raw-string r\"...\" va ghi ra tep .py roi chay")
        print("(quy tac 3 cua CLAUDE.md), khong phai bang cach xoa ky tu.")
        print("RESULT: FAIL")
        return 1

    if doi_so is None:
        print(f"Ky tu dieu khien: 0 trong {len(tep)} tep van ban duoc git theo doi.")
    else:
        print(f"Ky tu dieu khien: 0 trong {len(tep)} tep dua vao.")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    # ⭐ `sys.argv[1:]` chu khong `None` khi CO doi so: xem ghi chu o `main`.
    raise SystemExit(main(sys.argv[1:] if len(sys.argv) > 1 else None))
