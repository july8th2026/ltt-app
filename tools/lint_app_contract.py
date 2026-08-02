"""
lint_app_contract.py — kiem CO HOC hop dong app (audit tai dung).

Quet moi apps/<slug>/ va bao cac vi pham hop dong pho bien (theo rubric rà soát):
- manifest.py co MANIFEST, slug == ten thu muc;
- khai job_types thi PHAI co jobs.py::handle + credit_cost != None;
- routes.py co @router.post thi nen dung verify_csrf_token + require_login (CSRF/auth);
- route serve file ({key:path}) nen guard theo user_id (co-lap A-khong-doc-B).

ERROR = vi pham chac chan (chan). WARN = dau hieu can nguoi soi. Chay:
    python tools/lint_app_contract.py            # bao cao
    python tools/lint_app_contract.py --strict    # WARN cung tinh la loi (exit 1)

Khong thay the review cua nguoi/agent — chi bat cac loi co hoc re tien, som.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APPS = ROOT / "apps"

# App co ly do rieng, mien tru mot so kiem tra.
#   demo: app test hop dong toi thieu.
#   socialbot: dong bang, khong phat trien.
SKIP_APPS = {"socialbot"}


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

        routes = d / "routes.py"
        if routes.is_file():
            rtext = _read(routes)
            if "require_login" not in rtext:
                findings.append(Finding(app, "WARN", "routes.py khong thay require_login"))
            if "@router.post" in rtext and "verify_csrf_token" not in rtext:
                findings.append(Finding(app, "WARN",
                                        "co @router.post nhung khong thay verify_csrf_token (CSRF?)"))
            # Route serve file theo key -> phai guard co-lap user.
            if "{key:path}" in rtext and not re.search(r"u\.id|user_id|segs\[1\]", rtext):
                findings.append(Finding(app, "WARN",
                                        "route serve {key:path} khong thay guard user_id (co-lap?)"))
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
