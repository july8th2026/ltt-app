"""
lint_app_contract.py - kiem CO HOC hop dong app (audit tai dung).

Quet moi apps/<slug>/ va bao cac vi pham hop dong pho bien (theo rubric rà soát):
- manifest.py co MANIFEST, slug == ten thu muc;
- khai job_types thi PHAI co jobs.py::handle + credit_cost != None;
- routes.py co @router.post thi nen dung verify_csrf_token + require_login (CSRF/auth);
- route serve file ({key:path}) nen guard theo user_id (co-lap A-khong-doc-B);
- routes.py khong duoc phinh thanh noi chua logic nghiep vu (xem NGUONG duoi).

ERROR = vi pham chac chan (chan). WARN = dau hieu can nguoi soi. Chay:
    python tools/lint_app_contract.py            # bao cao
    python tools/lint_app_contract.py --strict    # WARN cung tinh la loi (exit 1)

Khong thay the review cua nguoi/agent - chi bat cac loi co hoc re tien, som.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APPS = ROOT / "apps"

# App co ly do rieng, mien tru mot so kiem tra.
#
# Muc `socialbot` bo di 2026-08-25 cung app do (Q108). Danh sach nay nay RONG,
# va giu nguyen no rong la mot muc tieu: moi mien tru la mot app khong bi hop
# dong soi, va ly do mien tru thi song lau hon hoan canh sinh ra no.
SKIP_APPS: set = set()

# ── Nguong tang nghiep vu (audit control-plane 2026-08-06) ──────────────────
#
# Hop dong app quy dinh manifest/routes/jobs nhung KHONG noi logic nghiep vu
# nam o dau. Ket qua do duoc: 5 app dung features.py, 5 app dung cost.py, 1 app
# dung services/, con lai nhet thang vao route. Khong co cho mac dinh thi route
# la cho de moi thu roi vao - hai file route da vuot 1.300 dong vi vay.
#
# Chuan tu 2026-08-06: logic nghiep vu nam o `services/` (nhieu miền) hoac mot
# module rieng nhu `features.py` / `cost.py` (mot miền). Route chi lo HTTP.
#
# Nguong chon theo phan bo thuc te chu khong theo cam tinh: file route lon nhat
# ma van de doc trong repo la ~870 dong / 23 handler (autosubvideo), nen dat
# tran o 900 dong va 30 handler - vua du de khong bao dong gia, vua chan duoc
# hai file 1.300-1.800 dong hien tai.
MAX_ROUTES_LINES = 900
MAX_ROUTES_HANDLERS = 30


class Finding:
    def __init__(self, app: str, level: str, msg: str):
        self.app, self.level, self.msg = app, level, msg

    def __repr__(self) -> str:
        return f"[{self.level}] {self.app}: {self.msg}"


def _read(p: pathlib.Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def lint() -> list:
    findings: list = []
    if not APPS.is_dir():
        return findings
    for d in sorted(APPS.iterdir()):
        app = d.name
        if not d.is_dir() or app.startswith(("_", ".")) or app in SKIP_APPS:
            continue
        man = d / "manifest.py"
        if not man.is_file():
            findings.append(Finding(app, "ERROR", "thieu manifest.py"))
            continue
        mtext = _read(man)
        if "MANIFEST" not in mtext:
            findings.append(Finding(app, "ERROR", "manifest.py khong co MANIFEST"))
        m = re.search(r'slug\s*=\s*["\']([^"\']+)["\']', mtext)
        if m and m.group(1) != app:
            findings.append(Finding(app, "ERROR",
                                    f"slug {m.group(1)!r} != ten thu muc {app!r}"))
        has_jobtypes = bool(re.search(r"job_types\s*=\s*\(\s*['\"]", mtext))
        if has_jobtypes:
            jobs = d / "jobs.py"
            if not jobs.is_file() or "def handle" not in _read(jobs):
                findings.append(Finding(app, "ERROR",
                                        "khai job_types nhung thieu jobs.py::handle"))
            if re.search(r"credit_cost\s*=\s*None", mtext):
                findings.append(Finding(app, "ERROR",
                                        "khai job_types nhung credit_cost=None"))

        # App co the khai route bang MOT file `routes.py` hoac mot package
        # `routes/`. Bo qua dang package thi linter im lang dung voi hai app
        # LON NHAT ngay sau khi chung duoc tach - moi kiem CSRF/auth/co-lap
        # duoi day bien mat ma khong ai biet.
        route_files = ([d / "routes.py"] if (d / "routes.py").is_file()
                       else sorted((d / "routes").glob("*.py"))
                       if (d / "routes").is_dir() else [])
        if route_files:
            # Kiem an toan la thuoc tinh cua CA app -> doc gop.
            rtext = "\n".join(_read(f) for f in route_files)
            if "require_login" not in rtext:
                findings.append(Finding(app, "WARN", "routes.py khong thay require_login"))
            if "@router.post" in rtext and "verify_csrf_token" not in rtext:
                findings.append(Finding(app, "WARN",
                                        "co @router.post nhung khong thay verify_csrf_token (CSRF?)"))
            # Route serve file theo key -> phai guard co-lap user.
            if "{key:path}" in rtext and not re.search(r"u\.id|user_id|segs\[1\]", rtext):
                findings.append(Finding(app, "WARN",
                                        "route serve {key:path} khong thay guard user_id (co-lap?)"))

            # Tang nghiep vu: route phinh to = logic dang nam sai cho.
            #
            # Nguong tinh theo TUNG FILE, khong theo tong. Tach dung thi tong
            # con to hon ban dau (them docstring + import cho moi module) -
            # do chinh la muc dich: moi file nho lai. Do tong se phat dung cai
            # minh muon khuyen khich.
            qua_to = [(f, len(_read(f).splitlines()),
                       len(re.findall(r"^@router\.", _read(f), re.M)))
                      for f in route_files]
            qua_to = [(f, n, h) for f, n, h in qua_to
                      if n > MAX_ROUTES_LINES or h > MAX_ROUTES_HANDLERS]
            handlers = len(re.findall(r"^@router\.", rtext, re.M))
            has_layer = (d / "services").is_dir() or any(
                (d / f"{name}.py").is_file()
                for name in ("features", "cost", "service", "domain"))
            if qua_to:
                for f, n, h in qua_to:
                    findings.append(Finding(
                        app, "WARN",
                        f"{f.name} {n} dong / {h} handler vuot nguong "
                        f"{MAX_ROUTES_LINES}/{MAX_ROUTES_HANDLERS} - tach theo mien "
                        f"ra services/ (debug theo hang muc se de hon nhieu)"))
            elif handlers >= 12 and not has_layer and len(route_files) == 1:
                findings.append(Finding(
                    app, "WARN",
                    f"{handlers} handler nhung khong co services/ hay "
                    f"features.py - logic nghiep vu dang nam trong route?"))
    return findings


def main() -> int:
    strict = "--strict" in sys.argv
    fs = lint()
    errs = [f for f in fs if f.level == "ERROR"]
    warns = [f for f in fs if f.level == "WARN"]
    for f in fs:
        print(f)
    print(f"\nApps quet: {len([d for d in APPS.iterdir() if d.is_dir() and not d.name.startswith(('_','.')) and d.name not in SKIP_APPS])}"
          f" | ERROR: {len(errs)} | WARN: {len(warns)}")
    if errs or (strict and warns):
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
