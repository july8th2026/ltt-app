r"""chay_web_that.py — chay mot kich ban Playwright tren WEB THAT, dang nhap
bang cookie cua tai khoan thu.

    python tools\chay_web_that.py tests\browser\agent_ui_v2_ui0_web_that.js
    python tools\chay_web_that.py <kich ban> --email khach2.thu@lttstudios.local
    python tools\chay_web_that.py <kich ban> --phien ui4

## Vi sao co tep nay

Luat du an bat kiem giao dien bang trinh duyet that va **chot tren URL cong
khai** (`CLAUDE.md` luat 7 — loopback bo qua Cloudflare). Ca hai doi mot phien
dang nhap. `tools/tai_khoan_thu.py --cookie` cho cookie ay ma khong ai phai
thay hay go mat khau.

⛔ **`process.env` KHONG dung duoc trong kich ban Playwright.** `playwright-cli
   run-code` chay ham trong mot hop cat, khong phai tien trinh node — doc
   `process` o do nem `ReferenceError: process is not defined`. Do la ly do
   cookie di vao bang DAU THAY THE chu khong bang bien moi truong.

## ⭐ Cookie KHONG BAO GIO cham cay lam viec

Kich ban trong kho giu dau `__LTT_COOKIE__`. Tep nay chep no ra **thu muc tam
cua he dieu hanh**, dien cookie vao BAN SAO do, chay, roi **xoa ban sao** o
`finally`. Cay lam viec khong bao gio chua bi mat, ke ca khi kich ban nem loi.

⚠️ Doc `secrets\app.env` doi Administrator, nen buoc lay cookie di qua
   `tools/nang_quyen.py` (nang quyen im lang — khong phai diem dung).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# stdout mac dinh tren Windows la cp1252 — in mot ky tu tieng Viet ra do nem
# `UnicodeEncodeError` va giet ca luot chay, SAU KHI da lay cookie. Mot loi
# trinh bay khong duoc phep giet mot phep do.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

GOC = Path(__file__).resolve().parent.parent
#: Dau thay the trong kich ban. Phai khop `agent_ui_v2_*_web_that.js`.
DAU = "__LTT_COOKIE__"
VENV_PROD = r"C:\LTTPlatform\venv\Scripts\python.exe"
APP_ENV = r"C:\LTTPlatform\secrets\app.env"


def lay_cookie(email: str) -> str:
    """`session=...` cua tai khoan thu, qua nang quyen. ⛔ Khong in ra."""
    r = subprocess.run(
        [sys.executable, str(GOC / "tools" / "nang_quyen.py"), "--lenh",
         f'{VENV_PROD} {GOC / "tools" / "tai_khoan_thu.py"} '
         f'--app-env {APP_ENV} --cookie {email}'],
        capture_output=True, text=True, cwd=GOC, encoding="utf-8", errors="replace")
    for dong in r.stdout.splitlines():
        if dong.startswith("session="):
            return dong[len("session="):].strip()
    raise SystemExit(
        "KHONG lay duoc cookie. Kiem tai khoan ton tai chua:\n"
        f"  python tools\\nang_quyen.py --lenh \"{VENV_PROD} "
        f"{GOC / 'tools' / 'tai_khoan_thu.py'} --app-env {APP_ENV} --liet-ke\"\n"
        f"--- stdout ---\n{r.stdout[-500:]}\n--- stderr ---\n{r.stderr[-500:]}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kich_ban", help="duong dan .js, vd tests/browser/xxx_web_that.js")
    p.add_argument("--email", default="khach1.thu@lttstudios.local")
    p.add_argument("--phien", default="webthat",
                   help="ten profile trinh duyet rieng cua lan (playwright-cli -s=)")
    a = p.parse_args()

    goc_kb = (GOC / a.kich_ban).resolve()
    if not goc_kb.is_file():
        raise SystemExit(f"khong thay kich ban: {goc_kb}")
    ma = goc_kb.read_text(encoding="utf-8")
    if DAU not in ma:
        raise SystemExit(f"kich ban khong co dau {DAU} — xem docstring tep nay")

    cookie = lay_cookie(a.email)
    print(f"[cookie] {a.email}: da lay, dai {len(cookie)} ky tu")

    # ⛔ Ban sao mang bi mat nam NGOAI kho, va bi xoa o `finally`.
    tam = Path(tempfile.mkdtemp(prefix="ltt-webthat-")) / goc_kb.name
    try:
        tam.write_text(ma.replace(DAU, cookie), encoding="utf-8", newline="\n")
        subprocess.run(["playwright-cli", f"-s={a.phien}", "open",
                        "https://app.lttstudios.com/"],
                       capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace")
        r = subprocess.run(["playwright-cli", f"-s={a.phien}", "run-code",
                            f"--filename={tam}"],
                           capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace")
        # ⛔ Loc moi dong co the mang cookie ra man hinh/nhat ky.
        ra = "\n".join(d for d in ((r.stdout or "") + (r.stderr or "")).splitlines()
                       if cookie not in d)
        print(ra)
        return 0 if '"status": "PASS"' in ra or '"status":"PASS"' in ra else 1
    finally:
        try:
            tam.unlink()
            tam.parent.rmdir()
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
