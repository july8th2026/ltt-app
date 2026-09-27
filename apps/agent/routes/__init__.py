"""
routes/ - be mat web cua app agent, tach theo mien (AGENTS.md muc 8).

Nen tang chi can bien `router`. Import tung module o day de handler cua chung
duoc dang ky vao router truoc khi nen tang gan vao FastAPI.

    _shared.py      router + helper dung chung
    trang.py           Hai trang HTML: `/agent` va `/agent/canvas` (phuc vu bundle).
    workspace.py       Tuy chon hien thi, bang mau cong cu, tai san va bao gia.
    workflows.py       CRUD workflow v2 (kho luu tru Canvas v2).
    drafts_v3.py       Ban nhap Canvas v3 (`workflow_draft`) + xuat ban.
    runs_v3.py         Cua v3 cho mot luot chay: tao run (tao_run), doc run (node + su kien).
    palette_v3.py      Palette V2 sinh tu registry + luat noi day (plan 02).
    bieu_thuc_v3.py    Goi y cho trinh soan bieu thuc §6 (P2 Task 8).
    bao_gia_v3.py      MOT cua bao gia cho CA do thi (no §5, lan p10-don).
    agent_v3.py        Agent Designer §12.2: soan draft v3 bang AI. KHONG publish.
    phe_duyet_v3.py    Cua duyet/tu choi mot waitpoint `core.human` (lan UI-8a).
                       ⛔ No KHONG tao run, KHONG tinh tien, KHONG di vong qua
                       `tao_run.py` — chi DONG mot waitpoint.
    ket_noi_v3.py      Kho ket noi cua khach (§6 o ket noi, lan UI-5). Bi mat
                       di qua `platform_core/credential.py` — cua nay ⛔ khong
                       bao gio tra lai gia tri bi mat, chi tra `ref` + nhan.
    admin.py           So lieu van hanh cho quan tri (job con doi bao lau).
                       Hai cua `/api/admin/runs*` da di cung bang `agent_runs`
                       ngay 23/09/2026 — xem docstring cua chinh admin.py.

🗑️ ĐÓNG CỬA 24/09/2026 (plan wf-v2 P8 Task 5, no §5): `assistant.py`,
   `sharing.py`, `library.py` va hai route ban chup trong `workflows.py` da bi
   XOA. Chung tra `AgentWorkflow` id trong khi giao dien cam id v3 -> 404 ngay
   lan bam dau; do production 24/09: shares 0 ban ghi moi thoi dai, clone 0,
   restore 0 (doi chung `save` = 78). Banh coc: `test_2924`.
"""
from apps.agent.routes._shared import router
from apps.agent.routes import (  # noqa: F401  (import de dang ky route)
    trang, workspace, workflows, admin,
    drafts_v3, runs_v3, palette_v3, bieu_thuc_v3, bao_gia_v3, agent_v3,
    ket_noi_v3, phe_duyet_v3)

__all__ = ["router"]
