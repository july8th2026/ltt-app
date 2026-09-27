"""May chu CO LAP de kiem GUI Canvas — UI-0 (che do A).

⛔ KHONG chay tren cong 8100: may nay LA production. Cong 8198, sqlite rieng
   trong mot thu muc NGOAI kho, khong cham PostgreSQL nao.

Khuon lay tu `tests/fixtures/image_studio_server.py` (cung kho), ⛔ khong tu bia.

## Chay

    set AGENT_UI0_FIXTURE_ROOT=<thu muc ngoai kho>
    python -m uvicorn tests.browser.agent_ui_v2_ui0_may_chu:app ^
           --host 127.0.0.1 --port 8198

⚠️ Moi duong dan phai TUYET DOI va NGOAI kho. Mot script dev neo theo `.` de rac
   vao chinh cay dang do, va `gate._anh_chup_cay()` se bao "CAY DA DOI TRONG LUC
   CHAY" roi vut bo phep do cua no.

## Tai khoan

Tai khoan FIXTURE chi ton tai trong sqlite cua thu muc tren. ⛔ Day KHONG phai
`khach{1,2,3}.thu@lttstudios.local` — bo do dung cho che do B (web that, xem
`tests/browser/agent_ui_v2_ui0_web_that.js`).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(os.environ["AGENT_UI0_FIXTURE_ROOT"]).resolve()
ROOT.mkdir(parents=True, exist_ok=True)

os.environ["LTT_DATABASE_URL"] = f"sqlite:///{(ROOT / 'agent-ui0.db').as_posix()}"
os.environ["LTT_DATA_DIR"] = str(ROOT / "data")
os.environ["LTT_ENV"] = "development"
os.environ["LTT_SESSION_SECRET"] = "agent-ui0-browser-fixture"

config = ROOT / "config.json"
config.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1}),
                  encoding="utf-8")

#: Tai khoan fixture. Mat khau nam TRONG tep nay co chu dich: no la mot gia tri
#: thu, chi song trong sqlite cua thu muc scratchpad, va khong bao gio cham
#: production. Kich ban Playwright doc tu day, khong ai phai go tay.
EMAIL = "agent-ui0@example.com"
PASSWORD = "Browser-ui0-2026"

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
        cap_tay(db, user.id, 5000, by="fixture", note="UI-0 browser")
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
