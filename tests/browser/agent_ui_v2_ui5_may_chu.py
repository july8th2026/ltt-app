"""May chu CO LAP de kiem GUI Inspector V2 + ket noi — UI-5 (che do A).

⛔ KHONG chay tren cong 8100: may nay LA production. Cong **8204** — dieu phoi
   cap rieng cho lan UI-5 ngay 28/09 (8198 la cua UI-7, 8201 UI-4, 8202 UI-7,
   8203 UI-1). ⛔ Tuyet doi khong giet tien trinh tren mot cong minh khong tu
   khoi dong: mot cong dang KHOI DONG LAI tra y het mot cong trong.

Khuon lay tu `tests/browser/agent_ui_v2_ui0_may_chu.py` (cung kho), ⛔ khong tu
bia — chi khac ba dieu, va ca ba deu co ly do ghi tai cho.

## Chay

    set AGENT_UI5_FIXTURE_ROOT=<thu muc ngoai kho>
    python -m uvicorn tests.browser.agent_ui_v2_ui5_may_chu:app ^
           --host 127.0.0.1 --port 8204

⚠️ Moi duong dan phai TUYET DOI va NGOAI kho — mot script dev neo theo `.` de
   rac vao chinh cay dang do.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(os.environ["AGENT_UI5_FIXTURE_ROOT"]).resolve()
ROOT.mkdir(parents=True, exist_ok=True)

os.environ["LTT_DATABASE_URL"] = f"sqlite:///{(ROOT / 'agent-ui5.db').as_posix()}"
os.environ["LTT_DATA_DIR"] = str(ROOT / "data")
os.environ["LTT_ENV"] = "development"
os.environ["LTT_SESSION_SECRET"] = "agent-ui5-browser-fixture"
# 🔴 KHAC 1. Kho credential doi mot khoa Fernet. Dat o day (gia tri THU, chi
#    song trong sqlite cua thu muc scratchpad) chu khong de no suy tu dinh danh
#    may: mot phep kiem ma hoa phai biet chinh xac no dang dung khoa nao.
os.environ.setdefault("LTT_TOKEN_ENCRYPTION_KEY", "khoa-browser-ui5-" + "b" * 32)
# 🔴 KHAC 2. ⛔ Khong de mot `LTT_OAUTH_*` that lot vao: phep do tang `cloud`
#    do su VANG MAT cua cau hinh, nen mot cau hinh co that lam no noi nguoc.
for _k in [k for k in os.environ if k.startswith("LTT_OAUTH_")]:
    os.environ.pop(_k, None)

config = ROOT / "config.json"
config.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1}),
                  encoding="utf-8")

#: Tai khoan fixture. Mat khau nam TRONG tep nay co chu dich: no la mot gia tri
#: thu, chi song trong sqlite cua thu muc scratchpad, va khong bao gio cham
#: production. Kich ban Playwright doc tu day, khong ai phai go tay.
EMAIL = "agent-ui5@example.com"
PASSWORD = "Browser-ui5-2026"

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
        cap_tay(db, user.id, 5000, by="fixture", note="UI-5 browser")
    db.commit()
finally:
    try:
        next(gen)
    except StopIteration:
        pass

# 🔴 KHAC 3 — VA LA CAI QUAN TRONG NHAT.
#
#    `apps/agent/routes/__init__.py` la **so dung chung S5** (chu la lan UI-1),
#    nen lan UI-5 KHONG them dong import vao do. Router la MOT doi tuong dung
#    chung (`_shared.router`), nen import o day gan cac cua `/api/v3/ket-noi`
#    vao dung router ma `create_app()` se lap.
#
#    ⚠️ Khi dieu phoi da dau dong import vao `__init__.py` luc gop, dong duoi
#    tro thanh vo hai: import lai mot module da nap khong dang ky route hai lan.
import apps.agent.routes.ket_noi_v3  # noqa: E402,F401

from server.app import create_app  # noqa: E402

app = create_app(env={
    "LTT_ENV": "development",
    "LTT_CONFIG_PATH": str(config),
    "LTT_SESSION_SECRET": os.environ["LTT_SESSION_SECRET"],
    "LTT_ADMIN_USERNAME": "",
    "LTT_ADMIN_PASSWORD_HASH": "",
})
