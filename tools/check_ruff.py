r"""Banh coc cho `ruff` — chot TAP HOP theo ma luat, khong chot mot con so.

    py tools\check_ruff.py            # kiem, so voi moc
    py tools\check_ruff.py --accept   # ghi lai moc (khi da don bot)

## Vi sao la mot BANH COC chu khong phai mot cong "phai sach"

Do 06/09 khi bat `ruff` lan dau: hang TRAM phat hien voi bo luat
`F,B` (da bo `B008` vi no la `Depends()` cua FastAPI). Bat mot cong
"phai sach" o day nghia la gate do hang tram lan va khong ai sua duoc trong
mot luot — nen no se bi tat.

⚠️ Con SO thi doc o `check_ruff.moc`, dung doc o day. Docstring
   nay khong tu biet no da cu.

⭐ Kho nay da co san khuon: `check_bo_qua.moc`, `check_dich_thieu.moc`. Tep nay
   di theo dung khuon do thay vi nghi ra mot khuon moi.

## Vi sao chot theo MA LUAT chu khong chot TONG

🔴 Mot moc "tong <= 512" co mot cua hoan doi mot-doi-mot di lot: xoa mot
   `F401` roi them mot `F811` thi tong khong doi, ma `F811` (hai ham cung ten,
   cai sau che cai truoc) la mot loi THAT. Do dung la bay `check_so_test` da
   ghi trong `docs/BAY_TRONG_CONG_CHAT_LUONG.md` — banh coc dem SO LUONG luon
   co mot cua hoan doi.

⇒ Chot mot ban do `{ma_luat: so_luong}`. Tang o BAT KY ma nao la do, ke ca khi
  tong giam.

## ⛔ Vi sao KHONG chay `--fix` toan kho

371 trong 512 la `F401 unused-import` va ruff tu sua duoc. Nhung o kho nay mot
import "khong dung" co the dang **dang ky** mot thu: bang CSDL, route, provider.
Go no di thi trang van tra 200, chi la vo trong — dung kieu hong ma `CLAUDE.md`
canh bao ve `Path(__file__).parents[n]`.

⇒ Don theo TUNG TEP khi da cham vao tep do, khong don hang loat.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent

#: Cho phep phep kiem tro moc di noi khac — xem `AGENTS.md` muc "chot khong
#: duoc ghi vao cay": mot phep kiem sua tep that trong kho tu pha luot gate
#: chua no.
_MOC_THU = __import__("os").environ.get("LTT_RUFF_MOC")
TEP_MOC = (pathlib.Path(_MOC_THU) if _MOC_THU
           else pathlib.Path(__file__).with_name("check_ruff.moc"))


def quet() -> dict[str, int]:
    """{ma_luat: so_luong} theo cau hinh trong `ruff.toml`."""
    r = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--output-format", "json", "."],
        cwd=GOC, capture_output=True, text=True, encoding="utf-8", errors="replace")
    # ruff tra 1 khi CO phat hien — do la binh thuong, khong phai loi chay.
    if r.returncode not in (0, 1):
        raise SystemExit(f"ruff khong chay duoc (ma {r.returncode}):\n{r.stderr[:400]}")
    dem: dict[str, int] = {}
    for muc in json.loads(r.stdout or "[]"):
        ma = muc.get("code") or "?"
        dem[ma] = dem.get(ma, 0) + 1
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
        "# Moc `ruff` — sinh boi `py tools\\check_ruff.py --accept`.",
        "# Chot theo MA LUAT, khong chot tong: mot moc tong co cua hoan doi",
        "# mot-doi-mot (xoa mot F401, them mot F811 -> tong khong doi).",
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
        print(f"[ruff] da ghi moc: {sum(hien.values())} phat hien / "
              f"{len(hien)} ma luat -> {TEP_MOC.name}")
        return 0

    moc = doc_moc()
    if not moc:
        print(f"[ruff] CHUA CO MOC. Chay `py tools\\check_ruff.py --accept` mot lan.")
        return 1

    tang = {ma: (moc.get(ma, 0), so) for ma, so in hien.items() if so > moc.get(ma, 0)}
    giam = {ma: (moc[ma], hien.get(ma, 0)) for ma in moc if hien.get(ma, 0) < moc[ma]}

    if tang:
        print("[ruff] TANG so voi moc - moi dong duoi day la mot loi MOI:")
        for ma, (cu, moi) in sorted(tang.items()):
            print(f"   {ma:<8} {cu} -> {moi}")
        print("\n  Sua chung, hoac neu that su co ly do thi `--accept` de doi moc")
        print("  (va noi ro ly do trong commit).")
        return 1

    print(f"[ruff] dat moc: {sum(hien.values())} phat hien / {len(hien)} ma luat")
    if giam:
        print("   da GIAM (nho `--accept` de ha moc, neu khong lan sau se troi lai):")
        for ma, (cu, moi) in sorted(giam.items()):
            print(f"   {ma:<8} {cu} -> {moi}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
