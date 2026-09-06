r"""Banh coc a11y — `axe-core` tren cac route that, chot TAP HOP theo MA LUAT.

    py tools\check_a11y.py                 # kiem, so voi moc
    py tools\check_a11y.py --accept        # ghi lai moc
    py tools\check_a11y.py --goc http://127.0.0.1:8100

## ⛔ KHONG thay `tools/mobile_quet.js`. Hai bo do hai thu khac nhau

    mobile_quet.js   KHA DUNG tren di dong -- tran ngang, vung cham < 44px,
                     co chu o o nhap, video thieu `playsinline`
    check_a11y.py    WCAG -- tuong phan mau, nhan cho o nhap, thu tu heading,
                     `alt` cua anh, vai tro ARIA

`axe` KHONG do tran ngang, va `mobile_quet` KHONG do tuong phan. Bo cai nao
cung mat mot lop. Day la cung ket luan voi `import-linter` vs
`lint_app_contract` — xem `.importlinter`.

## Vi sao la BANH COC chu khong phai cong "phai sach"

Cung ly do voi `ruff` va `mypy`: mot kho chua tung chay axe se co hang chuc
phat hien ngay luot dau, va mot cong luon do la mot cong se bi tat.

⇒ Chot `{ma_luat: so_nut}`. Tang o BAT KY luat nao la do, ke ca khi tong giam.

## ⛔ `violations` va `incomplete` KHONG duoc cong vao nhau

`axe` tra hai danh sach. `incomplete` nghia la **axe khong tu ket luan duoc,
can nguoi xem** — phan lon la tuong phan tren anh nen. Dem no nhu loi la bao
cao sai, dung kieu bay ma `mobile_quet.js` da ghi cho `target_be`.

Nen moc chi chot `violations`. `incomplete` duoc IN ra de nguoi doc biet, nhung
khong lam do gate.

## Dieu kien chay

1. mot may chu dang phuc vu (`--goc`, mac dinh loopback 8100);
2. `playwright-cli` va mot phien dang mo:  `playwright-cli -s=a11y open --browser=chrome`
3. `tools/vendor_a11y/axe.min.js` — tai bang `--tai-axe` neu chua co.

⚠️ Route can dang nhap thi phai truyen `--cookie`. Thieu no, route bi day ve
   `/login` va bao cao se la cua trang login — bo quet gan co `CHUA_DANG_NHAP`
   va cong cu nay TU CHOI tinh nhung dong do vao moc.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

GOC = pathlib.Path(__file__).resolve().parent.parent
AXE = GOC / "tools" / "vendor_a11y" / "axe.min.js"

_MOC_THU = os.environ.get("LTT_A11Y_MOC")
TEP_MOC = (pathlib.Path(_MOC_THU) if _MOC_THU
           else pathlib.Path(__file__).with_name("check_a11y.moc"))

#: Route CONG KHAI — khong can dang nhap, nen chay duoc o moi may.
ROUTE_MAC_DINH = ("/", "/login", "/dang-ky", "/bang-gia")


def _ra(*p: object) -> None:
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    print(*p)


def quet(goc: str, routes, khung, cookie: str = "", phien: str = "a11y") -> dict:
    if not AXE.is_file():
        raise SystemExit(
            f"thieu {AXE.relative_to(GOC).as_posix()} — chay `--tai-axe` mot lan.")
    mau = (GOC / "tools" / "a11y_quet.js").read_text(encoding="utf-8")
    cau_hinh = {"goc": goc.rstrip("/"), "cookie": cookie,
                "routes": list(routes), "khung": list(khung),
                "axe": AXE.read_text(encoding="utf-8")}
    # ⛔ Chuoi thay the phai la mot HAM, khong duoc la chuoi.
    #
    #    `re.subn` coi doi so thay the la KHUON MAU va dien giai escape trong
    #    do. `axe.min.js` (566 KB) day `\u...`, nen ban truyen chuoi chet ngay:
    #    `re.PatternError: bad escape \u at position 32726`.
    #
    #    `mobile_qa.py` dung duoc chuoi chi vi cau hinh cua no NHO va khong co
    #    backslash — chep y het sang day thi vo.
    moi, so = re.subn(r"const CAU_HINH = \{.*?\};",
                      lambda _m: "const CAU_HINH = " + json.dumps(cau_hinh) + ";",
                      mau, count=1, flags=re.S)
    if so != 1:
        raise SystemExit("khong tim thay dong `const CAU_HINH = {...};` trong a11y_quet.js")

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as f:
        f.write(moi)
        tam = f.name
    # ⚠️ `shutil.which` chu khong goi thang: tren Windows `playwright-cli` cai
    #    bang npm la mot bo ba tep va `subprocess` khong tu chon `.cmd`.
    lenh = shutil.which("playwright-cli")
    if not lenh:
        raise SystemExit("khong tim thay `playwright-cli` trong PATH. "
                         "Cai: npm install -g @playwright/cli@latest")
    try:
        r = subprocess.run([lenh, f"-s={phien}", "--raw", "run-code",
                            f"--filename={tam}"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=1800)
    finally:
        os.unlink(tam)
    out = (r.stdout or "").strip()
    if not out.startswith('"'):
        raise SystemExit("playwright-cli khong tra JSON:\n" + (out or r.stderr)[:700])
    return json.loads(json.loads(out))


def gom_theo_luat(kq: dict) -> tuple[dict[str, int], list[str]]:
    """({ma_luat: so_nut}, [canh bao]). Bo qua dong CHUA_DANG_NHAP."""
    dem: dict[str, int] = {}
    canh: list[str] = []
    for khoa, m in sorted(kq.items()):
        if m.get("CHUA_DANG_NHAP"):
            canh.append(f"CHUA DANG NHAP: {khoa} -> bi day ve {m.get('url_thuc')}"
                        f" — MOI so do cua dong nay VO NGHIA")
            continue
        if m.get("LOI"):
            canh.append(f"LOI: {khoa} -> {m['LOI']}")
            continue
        for v in m.get("vi_pham", []):
            dem[v["id"]] = dem.get(v["id"], 0) + int(v.get("so", 0))
    return dem, canh


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
        "# Moc a11y (`axe-core`) — sinh boi `py tools\\check_a11y.py --accept`.",
        "# Chot theo MA LUAT + so NUT vi pham, khong chot tong: mot moc tong co",
        "# cua hoan doi mot-doi-mot.",
        "#",
        "# ⛔ Chi chot `violations`. `incomplete` la 'axe khong tu ket luan duoc,",
        "#    can nguoi xem' — dem no nhu loi la bao cao sai.",
        "",
    ]
    dong += [f"{ma} = {so}" for ma, so in sorted(dem.items())]
    TEP_MOC.write_text("\n".join(dong) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Banh coc a11y bang axe-core.")
    p.add_argument("--goc", default="http://127.0.0.1:8100")
    p.add_argument("--route", action="append", default=None)
    p.add_argument("--khung", default="p390,d1280")
    p.add_argument("--cookie", default="")
    p.add_argument("--phien", default="a11y")
    p.add_argument("--accept", action="store_true")
    p.add_argument("--tai-axe", action="store_true", help="tai lai axe.min.js")
    a = p.parse_args()

    if a.tai_axe:
        import urllib.request
        AXE.parent.mkdir(parents=True, exist_ok=True)
        ver = json.load(urllib.request.urlopen(
            "https://registry.npmjs.org/axe-core/latest", timeout=30))["version"]
        b = urllib.request.urlopen(
            f"https://cdn.jsdelivr.net/npm/axe-core@{ver}/axe.min.js", timeout=90).read()
        AXE.write_bytes(b)
        _ra(f"[a11y] da tai axe-core {ver} ({len(b) // 1024} KB)")
        return 0

    kq = quet(a.goc, a.route or ROUTE_MAC_DINH, a.khung.split(","), a.cookie, a.phien)
    hien, canh = gom_theo_luat(kq)
    for c in canh:
        _ra(f"  [!] {c}")

    chua_ro = sum(len(m.get("chua_ro", [])) for m in kq.values())
    if chua_ro:
        _ra(f"  ({chua_ro} muc `incomplete` — axe khong tu ket luan duoc, "
            f"KHONG tinh vao moc)")

    if a.accept:
        ghi_moc(hien)
        _ra(f"[a11y] da ghi moc: {sum(hien.values())} nut / {len(hien)} ma luat")
        return 0

    moc = doc_moc()
    if not moc:
        _ra("[a11y] CHUA CO MOC. Chay `--accept` mot lan.")
        return 1

    tang = {ma: (moc.get(ma, 0), so) for ma, so in hien.items() if so > moc.get(ma, 0)}
    giam = {ma: (moc[ma], hien.get(ma, 0)) for ma in moc if hien.get(ma, 0) < moc[ma]}

    if tang:
        _ra("[a11y] TANG so voi moc — moi dong duoi day la mot vi pham MOI:")
        for ma, (cu, moi) in sorted(tang.items()):
            _ra(f"   {ma:<38} {cu} -> {moi}")
        return 1

    _ra(f"[a11y] dat moc: {sum(hien.values())} nut / {len(hien)} ma luat")
    if giam:
        _ra("   da GIAM (nho `--accept` de ha moc):")
        for ma, (cu, moi) in sorted(giam.items()):
            _ra(f"   {ma:<38} {cu} -> {moi}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
