"""May chu CO LAP de kiem GUI Data picker — UI-6 (che do A).

⛔ KHONG chay tren cong 8100: may nay LA production. Cong **8205** — dieu phoi
   cap rieng cho lan UI-6 ngay 28/09 (8198 UI-0, 8201 UI-4, 8202 UI-7, 8203
   UI-1, 8204 UI-5). ⛔ Tuyet doi khong giet tien trinh tren mot cong minh
   khong tu khoi dong: mot cong dang KHOI DONG LAI tra y het mot cong trong.

Khuon lay tu `tests/browser/agent_ui_v2_ui0_may_chu.py` (cung kho), ⛔ khong tu
bia.

## Chay

    set AGENT_UI6_FIXTURE_ROOT=<thu muc ngoai kho>
    python -m uvicorn tests.browser.agent_ui_v2_ui6_may_chu:app ^
           --host 127.0.0.1 --port 8205

⚠️ Moi duong dan phai TUYET DOI va NGOAI kho — mot script dev neo theo `.` de
   rac vao chinh cay dang do.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(os.environ["AGENT_UI6_FIXTURE_ROOT"]).resolve()
ROOT.mkdir(parents=True, exist_ok=True)

os.environ["LTT_DATABASE_URL"] = f"sqlite:///{(ROOT / 'agent-ui6.db').as_posix()}"
os.environ["LTT_DATA_DIR"] = str(ROOT / "data")
os.environ["LTT_ENV"] = "development"
os.environ["LTT_SESSION_SECRET"] = "agent-ui6-browser-fixture"

config = ROOT / "config.json"
config.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1}),
                  encoding="utf-8")

#: Tai khoan fixture. Mat khau nam TRONG tep nay co chu dich: no la mot gia tri
#: thu, chi song trong sqlite cua thu muc scratchpad, va khong bao gio cham
#: production. Kich ban Playwright doc tu day, khong ai phai go tay.
EMAIL = "agent-ui6@example.com"
PASSWORD = "Browser-ui6-2026"

import platform_core.db as dbmod  # noqa: E402
import platform_core.models  # noqa: E402,F401
from platform_core.credit import cap_tay  # noqa: E402
from platform_core.models import User  # noqa: E402
from platform_core.users import tao_nguoi_dung  # noqa: E402

dbmod.Base.metadata.create_all(dbmod.get_engine())
gen = dbmod.get_session()
db = next(gen)
try:
    user = db.query(User).filter_by(email=EMAIL).one_or_none()
    if user is None:
        user = tao_nguoi_dung(db, email=EMAIL, password=PASSWORD,
                              is_verified=True)
        db.flush()
        cap_tay(db, user.id, 5000, by="fixture", note="UI-6 browser")
    db.commit()
finally:
    try:
        next(gen)
    except StopIteration:
        pass

from server.app import create_app  # noqa: E402

app = create_app(env={
    "LTT_ENV": "development",
    "LTT_CONFIG_PATH": str(config),
    "LTT_SESSION_SECRET": os.environ["LTT_SESSION_SECRET"],
    "LTT_ADMIN_USERNAME": "",
    "LTT_ADMIN_PASSWORD_HASH": "",
})
