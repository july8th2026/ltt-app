# DA CHAY 23/09/2026 tren CSDL production o che do DEM (dry-run):
#     tim_thay=0 da_dong=0 hoan_credit=0 bo_qua_planning=0
# => khong co run nao dang do, khong co credit nao dang bi giu, nen
#    khong can luot --that. Giu lai lam bang chung.
# ⛔ KHONG import duoc nua sau khi AgentRun bi go (cung commit).
r"""One-off §17.3 — đóng `AgentRun` chưa kết thúc, hoàn hold, trước khi drop bảng.

    python tools\dong_agent_run_con_do.py          # chi DEM (mac dinh)
    python tools\dong_agent_run_con_do.py --that   # ghi that

Chạy MỘT lần trên production, ngay trước migration drop `agent_runs`
(plan 01b Task 10). Số đếm ghi vào `docs/NHAT_KY.md`.

## Vì sao mặc định là DRY-RUN

Thao tác này chạy một lần, trên sổ tiền thật, trên một bảng sắp biến mất. Sai
thì không có lần hai để sửa. Mặc định chỉ đếm; `--that` mới ghi.
"""
from __future__ import annotations

import argparse

from platform_core.agent import budget
from platform_core.models import (AGENT_AWAITING_APPROVAL, AGENT_PLANNING,
                                  AGENT_RUNNING, AgentRun)

#: Hai trạng thái CHƯA kết thúc mà `budget.cancel` đóng được.
DANG_DO = (AGENT_AWAITING_APPROVAL, AGENT_RUNNING)

#: ⛔ `planning` KHÔNG nằm trong `DANG_DO`, và đó là mệnh đề về mã chứ không
#:    phải một lựa chọn cho tiện:
#:      1. `runs._TRANSITIONS` **không có** cạnh `planning -> cancelled`, nên
#:         `budget.cancel` với một hàng `planning` sẽ rơi xuống `settle()` rồi
#:         `ensure_can_spend()` ném `BudgetError`. Gộp nó vào đây là làm cả
#:         lượt chạy chết giữa chừng.
#:      2. Nó không giữ credit: `credit.giu_cho` chỉ được gọi ở
#:         `budget.approve`, tức chỉ khi đã sang `running`.
#:    Nó vẫn phải được ĐẾM RA — một hàng biến mất cùng bảng mà không ai nói
#:    tên là đúng thứ báo cáo này tồn tại để chặn.

#: Ba trạng thái CHẠM SỔ: chỉ `running` đã qua `credit.giu_cho`.
#: `awaiting_approval` chưa từng giữ đồng nào (`budget.cancel`:
#: *"pre-approval cancellation never touches credit"*) — hoàn cho nó là in tiền.


def dong(db, *, that: bool = False) -> dict:
    rows = list(db.query(AgentRun).filter(AgentRun.status.in_(DANG_DO)).all())
    bo_qua = db.query(AgentRun).filter(
        AgentRun.status == AGENT_PLANNING).count()
    bao_cao = {"tim_thay": len(rows), "da_dong": 0, "hoan_credit": 0,
               "bo_qua_planning": int(bo_qua)}
    if not that:
        return bao_cao
    for run in rows:
        # ⭐ `budget.cancel` tự phân hai nhánh: chưa duyệt ⇒ chuyển trạng thái
        #    KHÔNG chạm credit; đã duyệt ⇒ `settle(actual=0)` hoàn phần giữ.
        #    Gọi thẳng `credit.hoan` ở đây sẽ in tiền cho nhánh thứ nhất.
        truoc = int(run.estimated or 0) if run.status == AGENT_RUNNING else 0
        budget.cancel(db, run_id=run.id, user_id=run.user_id, actual=0)
        bao_cao["da_dong"] += 1
        bao_cao["hoan_credit"] += truoc
    db.flush()
    return bao_cao


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--that", action="store_true", help="ghi that, khong chi dem")
    args = ap.parse_args()
    import platform_core.db as dbmod
    db = next(dbmod.get_session())
    try:
        bc = dong(db, that=args.that)
        if args.that:
            db.commit()
        print(f"tim_thay={bc['tim_thay']} da_dong={bc['da_dong']} "
              f"hoan_credit={bc['hoan_credit']} "
              f"bo_qua_planning={bc['bo_qua_planning']} that={args.that}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
