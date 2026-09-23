"""LTT Agent AI app."""
from __future__ import annotations

#: Be mat ma app KHAC duoc phep import tu app nay. Moi thu ngoai danh sach nay
#: la noi bo, va `tools/lint_app_contract.py` chan lai.
#:
#: `apps/agent_dong_co` la CHU KHAI cua job_type `workflow.dong_co` (tach
#: 23/09 de `apps/agent` khong phai khai job_type nao, xem docstring
#: `apps/agent_dong_co/manifest.py`), nhung handler that van song o
#: `apps.agent.jobs` — dung chung than thi hanh voi phan con lai cua app. Nen
#: `apps.agent_dong_co.jobs` chi forward sang `handle` o day.
#:
#: ⛔ Them mot dong vao day la mot QUYET DINH KIEN TRUC. Phai sua CA HAI phia:
#:    o day va o `APP_DUOC_DUNG_APP` trong `tools/lint_app_contract.py`. Linter
#:    doi hai ban khai khop nhau chinh xac, nen khong the noi long mot ben.
BE_MAT_CONG_KHAI = {
    ("apps.agent.jobs", "handle"),
}
