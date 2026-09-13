"""
check_silent_except.py - dem cac cho NUOT LOI LANG LE, va khong cho tang them.

"Nuot lang le" = bat `except Exception`/`except:` roi:
  - khong nem lai,
  - khong ghi log,
  - va KHONG dung gia tri ngoai le (khong bien no thanh mot gia tri nhin thay
    duoc nhu `LoadedApp.error`, `ValidationIssue`, `order.note`).

Dieu kien thu ba quan trong: mot handler bien ngoai le thanh ket qua tuong minh
KHONG phai nuot loi - no xu ly loi. Ban dau cua phep do nay thieu dieu kien do
nen dem thua gap doi o `platform_core` (18 thay vi 8), va neu tin so do se di
"sua" nhung cho vốn da dung.

Cong cu chay theo kieu BANH COC (ratchet): so hien tai duoc chot trong
`tools/silent_except_baseline.json`. Tang len la FAIL. Giam thi bao va nhac ha
moc. Ly do khong doi 0 ngay: 131 cho trong ma song la mot dot sua lon, rui ro
regression cao, gia tri tung cho thap - nhung tuyet doi khong duoc them cho moi.

`core/` truoc day bi loai khoi phep do (78 cho, thuoc socialbot). Tu 2026-08-25
ca thu muc do da bi XOA (Q108), nen phep do nay gio phu toan bo ma song.

    python tools/check_silent_except.py            # kiem theo moc
    python tools/check_silent_except.py --list     # in tung cho
    python tools/check_silent_except.py --update   # ha moc sau khi da sua
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE = ROOT / "tools" / "silent_except_baseline.json"

SCAN = ("apps", "platform_core", "server", "tools")
SKIP_PARTS = {"__pycache__", "vendor", "node_modules", ".venv", "venv", "dist", "build"}

#: Engine CHUYEN NGUYEN VEN tu bot legacy — cung ly do voi `vendor` o tren, va
#: cung danh sach voi `ruff.toml` + `mypy.ini` (ca ba cong cu nhin cung pham vi
#: thi mot tep duoc mien o cho nay khong bat ngo bi bat o cho kia).
#:
#: 🔴 VI SAO MIEN, khi lo hong la that. 37 cho nuot loi trong ba thu muc nay
#:    KHONG phai ma moi — chung la ban sao tung byte cua ma da chay mot nam.
#:    Doi mot `except Exception: pass` thanh mot ban co log/nem la DOI HANH VI:
#:    mot loi truoc day bi nuot se bat dau noi len, va no co the lam hong mot
#:    job von chay xong. Diem cua viec chuyen nguyen ven la parity con do duoc;
#:    "sua lint" o day la vut bo chinh dieu do.
#:
#: ⚠️ Va mien o day CO gia: no che ca nhung cho nuot loi MOI neu ai do them ma
#:    vao ba thu muc nay. Chung la BAN CHUYEN DA DONG BANG — ma moi khong duoc
#:    dat vao do; no thuoc `services/<domain>.py` ben ngoai, noi bo do van soi.
#:
#: ⇒ No ky: 37 cho nuot loi ke thua. Chi sua khi da co fixture parity chay
#:   duoc, vi truoc do khong ai chung minh duoc mot ban sua khong doi dau ra.
BO_QUA_DUONG = (
    "apps/transcript/services/engine/",
    "apps/audio_pause/services/engine/",
    "apps/video_assembly/services/engine/",
)


def _co_dung_ngoai_le(node: ast.ExceptHandler) -> bool:
    """Handler co bien ngoai le thanh mot gia tri nhin thay duoc khong?"""
    if not node.name:
        return False
    return any(isinstance(x, ast.Name) and x.id == node.name
               for x in ast.walk(node))


def _co_ghi_log(node: ast.ExceptHandler) -> bool:
    for x in ast.walk(node):
        if not isinstance(x, ast.Call):
            continue
        f = x.func
        ten = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        if ten in {"exception", "warning", "error", "critical"}:
            return True
        if isinstance(f, ast.Attribute) and "log" in ast.dump(f.value).lower():
            return True
    return False


def quet() -> list[str]:
    ra: list[str] = []
    for area in SCAN:
        for path in sorted((ROOT / area).rglob("*.py")):
            if SKIP_PARTS & set(path.parts):
                continue
            if path.relative_to(ROOT).as_posix().startswith(BO_QUA_DUONG):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                t = node.type
                rong = t is None or (isinstance(t, ast.Name) and
                                     t.id in {"Exception", "BaseException"})
                if not rong:
                    continue
                if any(isinstance(x, ast.Raise) for x in ast.walk(node)):
                    continue
                if _co_ghi_log(node) or _co_dung_ngoai_le(node):
                    continue
                ra.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno}")
    return ra


def _moc() -> int:
    try:
        return int(json.loads(BASELINE.read_text(encoding="utf-8"))["max"])
    except (OSError, ValueError, KeyError):
        return -1


def main() -> int:
    cho = quet()
    n = len(cho)
    if "--list" in sys.argv:
        for c in cho:
            print(" ", c)
    if "--update" in sys.argv:
        BASELINE.write_text(json.dumps({"max": n}, indent=2) + "\n", encoding="utf-8")
        print(f"da ha moc xuong {n}")
        return 0

    moc = _moc()
    print(f"Nuot loi lang le: {n} | moc: {moc}")
    if moc < 0:
        print("Chua co moc. Chay --update de chot.")
        print("RESULT: FAIL")
        return 1
    if n > moc:
        print(f"TANG {n - moc} cho so voi moc. Xem `--list`.")
        print("Bat `except Exception` ma khong nem, khong log, khong dung `exc`")
        print("nghia la loi bien mat - va no bien mat o dung cho kho tim nhat.")
        print("RESULT: FAIL")
        return 1
    if n < moc:
        print(f"Giam {moc - n} cho. Chay --update de ha moc.")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
