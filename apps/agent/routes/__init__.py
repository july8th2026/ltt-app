"""
routes/ - be mat web cua app agent, tach theo mien (AGENTS.md muc 8).

Nen tang chi can bien `router`. Import tung module o day de handler cua chung
duoc dang ky vao router truoc khi nen tang gan vao FastAPI.

    _shared.py      router + helper dung chung
    legacy_runs.py     Luong plan/run doi dau, truoc canvas. Giu cho link cu.
    workspace.py       Tuy chon hien thi, bang mau cong cu, tai san va bao gia.
    assistant.py       Tro ly AI: dung ke hoach, xem truoc va ap dung de xuat.
    runs.py            Vong doi lan chay canvas: tao, duyet, tick, huy, artifact, bundle.
    workflows.py       CRUD workflow va ban chup theo phien ban.
    sharing.py         Chia se workflow qua link va nhan ban tu link.
    library.py         Thao tac tren workflow: nhat ky, kiem, nhan ban, luu tru, xuat/nhap.
    admin.py           Man hinh van hanh cho quan tri: lan chay, so lieu, huy.
"""
from apps.agent.routes._shared import router
from apps.agent.routes import (  # noqa: F401  (import de dang ky route)
    legacy_runs, workspace, assistant, runs, workflows, sharing, library, admin)

__all__ = ["router"]
