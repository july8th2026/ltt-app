"""
routes/ - be mat web cua app agent, tach theo mien (AGENTS.md muc 8).

Nen tang chi can bien `router`. Import tung module o day de handler cua chung
duoc dang ky vao router truoc khi nen tang gan vao FastAPI.

    _shared.py      router + helper dung chung
    trang.py           Hai trang HTML: `/agent` va `/agent/canvas` (phuc vu bundle).
    workspace.py       Tuy chon hien thi, bang mau cong cu, tai san va bao gia.
    assistant.py       Tro ly AI: dung ke hoach, xem truoc va ap dung de xuat.
    workflows.py       CRUD workflow va ban chup theo phien ban.
    drafts_v3.py       Ban nhap Canvas v3 (`workflow_draft`) + xuat ban.
    runs_v3.py         Cua v3 cho mot luot chay: tao run (tao_run), doc run (node + su kien).
    sharing.py         Chia se workflow qua link va nhan ban tu link.
    library.py         Thao tac tren workflow: nhat ky, kiem, nhan ban, luu tru, xuat/nhap.
    admin.py           So lieu van hanh cho quan tri (job con doi bao lau).
                       Hai cua `/api/admin/runs*` da di cung bang `agent_runs`
                       ngay 23/09/2026 — xem docstring cua chinh admin.py.
"""
from apps.agent.routes._shared import router
from apps.agent.routes import (  # noqa: F401  (import de dang ky route)
    trang, workspace, assistant, workflows, sharing, library, admin,
    drafts_v3, runs_v3)

__all__ = ["router"]
