"""
check_undefined_names.py - bat ten chua dinh nghia truoc khi nguoi dung bat.

Vi sao can: 2026-08-06 tim ra `POST /upscalevideo/queue` - duong nop viec CHINH
cua app - goi `get_session()` ma khong import. Moi lan nop deu NameError -> 500.
Loi nam trong repo tu 2026-08-02 (3ea1f2c) va khong test nao cham route do.

Test khong the phu het moi nhanh route. Nhung mot cai ten chua dinh nghia thi
doc tinh la thay duoc - khong can chay. Do la viec cua file nay.

Chay:
    python tools/check_undefined_names.py

Dung pyflakes vi no phan tich pham vi bien that su (biet local/global/comprehension),
khong phai grep. Thieu pyflakes thi BAO LOI chu khong bo qua: mot buoc kiem tra
lang le tat di con te hon khong co buoc do.
"""
from __future__ import annotations

import io
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Chi quet ma cua minh. Bo qua thu vien ben thu ba va engine vendor.
SCAN = ["apps", "platform_core", "server", "tools", "worker.py"]
SKIP_PARTS = {"__pycache__", "node_modules", "vendor", ".venv", "venv",
              "dist", "build", ".git"}

# pyflakes bao nhieu thu; chi nhung loai nay la LOI CHAC CHAN vo luc chay.
FATAL = ("undefined name", "undefined local", "local variable defined in "
         "enclosing scope referenced before assignment")


def _files() -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for entry in SCAN:
        path = ROOT / entry
        if path.is_file():
            out.append(path)
        elif path.is_dir():
            out += [p for p in path.rglob("*.py")
                    if not SKIP_PARTS & set(p.parts)]
    return sorted(out)


def main() -> int:
    try:
        from pyflakes.api import check
        from pyflakes.reporter import Reporter
    except ImportError:
        print("THIEU pyflakes. Cai bang:  pip install pyflakes")
        print("RESULT: FAIL")
        return 1

    warn = io.StringIO()
    reporter = Reporter(warn, warn)
    for path in _files():
        try:
            check(path.read_text(encoding="utf-8"), str(path), reporter)
        except (OSError, UnicodeDecodeError) as exc:
            print(f"[BO QUA] {path}: {exc}")

    fatal = [line for line in warn.getvalue().splitlines()
             if any(marker in line for marker in FATAL)]
    for line in fatal:
        print("[ERROR]", line)
    print(f"\nFile quet: {len(_files())} | ten chua dinh nghia: {len(fatal)}")
    if fatal:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
