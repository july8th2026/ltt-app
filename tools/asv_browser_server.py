"""Ban chay CO LAP cua Auto Scan Video, danh cho kiem GUI bang trinh duyet.

`CLAUDE.md` luat 5 doi mo trinh duyet that sau moi thay doi giao dien, va luat
9 cua chuong trinh V6 doi lam viec do tren mot **ban dev rieng**, khong dung
dich vu production o cong 8100.

## Hai cai chan, va ca hai deu can

Mot cai chan don le la mot cai chan se bi go "cho nhanh". Hai cai o hai truc
khac nhau — mot co y dinh, mot ve du lieu — thi go ca hai la mot hanh vi khong
the lam nham.

⛔ Va cai thu hai chan dung thu nguy hiem: neu `LTT_DATABASE_URL` khong mang
   chuoi `asv-browser-test`, tep nay **thoat** truoc khi cham toi `drop_all`.
   Khong co dong do thi mot lan chay nham bien no thanh mot lenh xoa sach CSDL
   dang phuc vu khach.

## Chay

```
set LTT_ASV_BROWSER_TEST=1
set LTT_DATABASE_URL=sqlite:///C:/.../asv-browser-test.db
set LTT_DATA_DIR=C:/.../asv-ui-data
set LTT_CONFIG_PATH=C:/.../config.json
set LTT_SESSION_SECRET=asv-ui-dev
python -m uvicorn tools.asv_browser_server:app --host 127.0.0.1 --port 8199
```

⚠️ Moi duong dan tren phai la duong TUYET DOI ngoai kho. Mot script dev neo
   theo `.` se de rac vao chinh cay dang do — va `gate._anh_chup_cay()` se bao
   "CAY DA DOI TRONG LUC CHAY" roi vut bo phep do cua no.
"""
from __future__ import annotations

import os

if os.environ.get("LTT_ASV_BROWSER_TEST") != "1":
    raise SystemExit("Dat LTT_ASV_BROWSER_TEST=1 cho ban chay co lap nay.")
if "asv-browser-test" not in os.environ.get("LTT_DATABASE_URL", ""):
    raise SystemExit("Tu choi chay khi LTT_DATABASE_URL khong mang "
                     "'asv-browser-test'.")

from platform_core import credit
from platform_core.db import Base, get_engine, get_session
import platform_core.models  # noqa: F401
# ⚠️ Phai nap CA bang cua app: `asv_run` chi vao `Base.metadata` khi module nay
#    duoc import. Thieu no thi trang chinh do voi `no such table: asv_run`, va
#    thong bao do khong nhac gi toi mot dong import.
import apps.auto_scan_video.tables  # noqa: F401
from platform_core.users import tao_nguoi_dung

Base.metadata.drop_all(get_engine())
Base.metadata.create_all(get_engine())
gen = get_session()
db = next(gen)
user = tao_nguoi_dung(db, email="asv-ui@example.com",
                      password="Browser-test-123", is_verified=True)
credit.cap_tay(db, user.id, 1000, by="browser-test")
db.commit()
db.close()

from server.app import create_app

app = create_app(env={
    "LTT_ENV": "local-server-test",
    "LTT_CONFIG_PATH": os.environ["LTT_CONFIG_PATH"],
    "LTT_SESSION_SECRET": os.environ["LTT_SESSION_SECRET"],
    "LTT_ADMIN_USERNAME": "",
    "LTT_ADMIN_PASSWORD_HASH": "",
})
