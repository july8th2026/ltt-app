"""May chu CO LAP de kiem GUI Canvas — UI-10b (Tro nang + mobile).

⛔ KHONG chay tren cong 8100: may nay LA production. Cong 8209, sqlite rieng
   trong mot thu muc NGOAI kho, khong cham PostgreSQL nao. ⛔ KHONG 8196/8198,
   ⛔ KHONG 8201-8208 — nhung cong do lan khac giu.

Khuon lay tu `tests/browser/agent_ui_v2_ui0_may_chu.py` (cung kho, cua lan
UI-0), doi cong + duong dan fixture RIENG cho lan nay — ⛔ khong tu bia hinh
dang server.

## Chay

    set AGENT_UI10B_FIXTURE_ROOT=<thu muc ngoai kho>
    python -m uvicorn tests.browser.agent_ui_v2_ui10b_may_chu:app ^
           --host 127.0.0.1 --port 8209

⚠️ Moi duong dan phai TUYET DOI va NGOAI kho — mot script dev neo theo `.` se
   lam `gate._anh_chup_cay()` bao "CAY DA DOI TRONG LUC CHAY" roi vut phep do.

## Tai khoan

Tai khoan FIXTURE chi ton tai trong sqlite cua thu muc tren, khong phai
`khach{1,2,3}.thu@lttstudios.local`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(os.environ["AGENT_UI10B_FIXTURE_ROOT"]).resolve()
ROOT.mkdir(parents=True, exist_ok=True)

os.environ["LTT_DATABASE_URL"] = f"sqlite:///{(ROOT / 'agent-ui10b.db').as_posix()}"
os.environ["LTT_DATA_DIR"] = str(ROOT / "data")
os.environ["LTT_ENV"] = "development"
os.environ["LTT_SESSION_SECRET"] = "agent-ui10b-browser-fixture"

config = ROOT / "config.json"
config.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1}),
                  encoding="utf-8")

#: Tai khoan fixture. Mat khau nam TRONG tep nay co chu dich: no la mot gia tri
#: thu, chi song trong sqlite cua thu muc scratchpad, va khong bao gio cham
#: production. Kich ban Playwright doc tu day, khong ai phai go tay.
EMAIL = "agent-ui10b@example.com"
PASSWORD = "Browser-ui10b-2026"

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
        cap_tay(db, user.id, 5000, by="fixture", note="UI-10b browser")
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
