r"""Banh coc cho `mypy` — chot TAP HOP theo ma loi, khong chot mot con so.

    py tools\check_mypy.py            # kiem, so voi moc
    py tools\check_mypy.py --accept   # ghi lai moc (khi da don bot)

## Vi sao la mot BANH COC chu khong phai cong "phai sach"

Do 06/09 khi bat `mypy` lan dau (da co `plugins = pydantic.mypy`): **600** phat
hien / 16 ma loi. Bat mot cong "phai sach" o day nghia la gate do 600 lan va
khong ai sua duoc trong mot luot — nen no se bi TAT. Banh coc chi cam TANG.

⭐ Di theo dung khuon da co trong kho (`check_bo_qua.moc`, `check_dich_thieu.moc`,
   `check_ruff.moc`) thay vi nghi ra mot khuon moi.

## Vi sao chot theo MA LOI chu khong chot TONG

🔴 Mot moc "tong <= 600" co mot cua hoan doi mot-doi-mot di lot: xoa mot
   `var-annotated` (mypy xin them chu thich — vo hai) roi them mot
   `attr-defined` (cham thuoc tinh KHONG TON TAI — `AttributeError` luc chay)
   thi tong khong doi. Do dung la bay `check_so_test` da ghi trong
   `docs/BAY_TRONG_CONG_CHAT_LUONG.md`: banh coc dem SO LUONG luon co mot cua
   hoan doi.

⇒ Chot mot ban do `{ma_loi: so_luong}`. Tang o BAT KY ma nao la do, ke ca khi
  tong giam.

## Ba ma dang chu y nhat trong moc hien tai

    attr-defined   cham mot thuoc tinh khong ton tai   -> AttributeError
    union-attr     cham thuoc tinh tren thu co the None -> 'NoneType' has no ...
    arg-type       truyen sai KIEU cho tham so

⭐ `union-attr` va `attr-defined` bat dung lop loi lop A trong `AGENTS.md` muc
   4d: **doan hinh dang API thay vi doc no**. Ngay 06/09 chinh toi mac ba lan
   trong mot buoi (`resources.create(kind="style")`, `add_variant(prompt_text=)`,
   cookie `session=` truyen ca chuoi). Mot cong cu doc chu ky that thi khong
   doan.

## ⛔ Vi sao KHONG bat `disallow_untyped_defs`

Kho nay phan lon chua chu thich kieu. Bat no la doi hang nghin dong khai bao
truoc khi bat duoc mot loi nao — va no do bang mot bien phap KIEU DANG, khong
phai bang mot loi. Xem `mypy.ini`.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent

#: Cung danh sach voi phep do dat moc. KHONG doc ca kho: `core/` va
#: `cutclipshort/` da mien trong `mypy.ini`, con `frontend/` la JS.
THU_MUC = ("apps", "platform_core", "server", "tools", "llm_gateway",
           "render_gateway", "sdk", "nexus_agent", "codex_sidecar")

#: Cay de QUET + thu muc trong no. Cho phep tro sang mot cay MAU da biet
#: truoc so loi.
#:
#: 🔴 VI SAO CAN. Do 06/09 bang `cosmic-ray` tren `check_ruff.py` (cung mot
#:    khuon): doi `dem[ma] = ... + 1` thanh `** 1` lam MOI so dem thanh 0,
#:    nen `tang` luon rong va banh coc XANH VINH VIEN — ma khong phep kiem
#:    nao thay, vi tat ca deu lay moc tu chinh `quet()`. Hong so voi hong
#:    thi van bang nhau.
#:
#: ⛔ THU_MUC phai TRUYEN VAO chu khong duoc "tu bo qua thu muc khong ton
#:    tai": mot thu muc bi doi ten se am tham roi khoi pham vi quet, va so
#:    phat hien GIAM — trong y het mot cai thien.
_GOC_THU = os.environ.get("LTT_MYPY_GOC")
GOC_QUET = pathlib.Path(_GOC_THU) if _GOC_THU else GOC
_TM_THU = os.environ.get("LTT_MYPY_THU_MUC")
THU_MUC_QUET = tuple(t.strip() for t in _TM_THU.split(",") if t.strip()) if _TM_THU else THU_MUC

#: Cho phep phep kiem tro moc di noi khac — xem `AGENTS.md` muc "chot khong
#: duoc ghi vao cay": mot phep kiem sua tep that trong kho tu pha luot gate
#: chua no.
_MOC_THU = os.environ.get("LTT_MYPY_MOC")
TEP_MOC = (pathlib.Path(_MOC_THU) if _MOC_THU
           else pathlib.Path(__file__).with_name("check_mypy.moc"))

#: ⛔ Phai co ca " error: " chu khong chi `[ma]` o cuoi dong. Dong `note:` cua
#:   mypy cung ket thuc bang `[ma]` trong vai truong hop, va dem ca chung thi
#:   moc phong len theo thu KHONG PHAI loi.
_DONG_LOI = re.compile(r" error: .*\[([a-z][a-z-]*)\]\s*$")


def quet() -> dict[str, int]:
    """{ma_loi: so_luong} theo cau hinh trong `mypy.ini`."""
    r = subprocess.run(
        [sys.executable, "-m", "mypy", "--no-error-summary", *THU_MUC_QUET],
        cwd=GOC_QUET, capture_output=True, text=True, encoding="utf-8", errors="replace")
    # mypy tra 1 khi CO phat hien — binh thuong. 2 la CHET (cau hinh hong,
    # trung ten module, tep .ini khong doc duoc): do KHONG duoc im lang thanh
    # "0 loi", vi mot moc 0 se nuot moi thu ve sau.
    if r.returncode not in (0, 1):
        raise SystemExit(
            f"mypy khong chay duoc (ma {r.returncode}). DOC dau ra duoi day —\n"
            f"dung doan nguyen nhan tu ma tra ve. Ba cai da gap that, nhung\n"
            f"danh sach nay KHONG day du:\n"
            f"  - `mypy.ini` co ky tu ngoai ASCII (configparser doc no theo\n"
            f"    bang ma HE THONG, khong phai UTF-8) -> UnicodeDecodeError\n"
            f"  - hai tep giai ra cung mot ten module (thieu `__init__.py`)\n"
            f"  - thu muc quet nam o O KHAC voi `mypy.ini` -> ValueError o\n"
            f"    `ntpath.relpath` khi mypy khop `exclude`\n"
            f"{r.stdout[-1500:]}\n{r.stderr[-600:]}")
    dem: dict[str, int] = {}
    for dong in r.stdout.splitlines():
        m = _DONG_LOI.search(dong)
        if m:
            dem[m.group(1)] = dem.get(m.group(1), 0) + 1
    return dem


def doc_moc() -> dict[str, int]:
    if not TEP_MOC.exists():
        return {}
    ra: dict[str, int] = {}
    for dong in TEP_MOC.read_text(encoding="utf-8").splitlines():
        d = dong.strip()
        if not d or d.startswith("#"):
            continue
        ma, _, so = d.partition("=")
        ra[ma.strip()] = int(so.strip() or 0)
    return ra


def ghi_moc(dem: dict[str, int]) -> None:
    dong = [
        "# Moc `mypy` — sinh boi `py tools\\check_mypy.py --accept`.",
        "# Chot theo MA LOI, khong chot tong: mot moc tong co cua hoan doi",
        "# mot-doi-mot (xoa mot var-annotated vo hai, them mot attr-defined",
        "# la AttributeError luc chay -> tong khong doi).",
        "",
    ]
    dong += [f"{ma} = {so}" for ma, so in sorted(dem.items())]
    TEP_MOC.write_text("\n".join(dong) + "\n", encoding="utf-8")


def main() -> int:
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    hien = quet()
    if "--accept" in sys.argv:
        ghi_moc(hien)
        print(f"[mypy] da ghi moc: {sum(hien.values())} phat hien / "
              f"{len(hien)} ma loi -> {TEP_MOC.name}")
        return 0

    moc = doc_moc()
    if not moc:
        print("[mypy] CHUA CO MOC. Chay `py tools\\check_mypy.py --accept` mot lan.")
        return 1

    tang = {ma: (moc.get(ma, 0), so) for ma, so in hien.items() if so > moc.get(ma, 0)}
    giam = {ma: (moc[ma], hien.get(ma, 0)) for ma in moc if hien.get(ma, 0) < moc[ma]}

    if tang:
        print("[mypy] TANG so voi moc - moi dong duoi day la mot loi MOI:")
        for ma, (cu, moi) in sorted(tang.items()):
            print(f"   {ma:<16} {cu} -> {moi}")
        print("\n  Sua chung, hoac neu that su co ly do thi `--accept` de doi moc")
        print("  (va noi ro ly do trong commit).")
        return 1

    print(f"[mypy] dat moc: {sum(hien.values())} phat hien / {len(hien)} ma loi")
    if giam:
        print("   da GIAM (nho `--accept` de ha moc, neu khong lan sau se troi lai):")
        for ma, (cu, moi) in sorted(giam.items()):
            print(f"   {ma:<16} {cu} -> {moi}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
