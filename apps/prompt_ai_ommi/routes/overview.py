"""So lieu Tong quan va chi tieu credit."""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.routes._shared import (
    _as_int, _jobs, _production_rows, _user, router, require_login, get_db)


# ── Tổng quan và Chi phí (R4) ──────────────────────────────────────────────
#
# Không dựng sổ tiền thứ hai. Ảnh tham chiếu của chủ sản phẩm hiển thị chi phí
# bằng USD và gộp "toàn team"; cả hai đều trái Q31 (1 credit = 100đ, tính theo
# từng người) và trái mô hình sở hữu. Ở đây đọc thẳng sổ credit của nền tảng và
# chỉ của CHÍNH người gọi.


@router.get("/api/overview")
def overview(request: Request, _identity: str = Depends(require_login),
             db: Session = Depends(get_db)):
    """Số liệu cho màn Tổng quan. Mọi con số đều lọc theo người đang đăng nhập."""
    from apps.prompt_ai_ommi.services import library as lsvc
    from apps.prompt_ai_ommi.services import resources as rsvc
    from apps.prompt_ai_ommi.services import storyboard as ssvc
    from platform_core import credit

    user = _user(request)
    kinds = rsvc.count_by_kind(db, user.id)
    library = lsvc.counts(db, user.id)
    boards = ssvc.list_boards(db, user.id)
    projects = _production_rows(db, user.id)

    scene_total = sum(len(ssvc.scenes(db, board.id, user.id)) for board in boards)

    return {
        "counts": {
            "projects": len(projects),
            "resources": sum(kinds.values()),
            "storyboards": len(boards),
            "scenes": scene_total,
            "meta_prompts": library.get("meta", 0),
            "styles": library.get("style", 0),
            "snippets": library.get("snippet", 0),
        },
        "resource_kinds": kinds,
        "credit_balance": credit.so_du(db, user.id),
        "recent_projects": [
            {"id": row.id, "name": row.name, "revision": row.revision,
             "updated_at": row.updated_at.isoformat()}
            for row in projects[:5]],
        "recent_jobs": _jobs(db, user.id)[:8],
    }


@router.get("/api/credit")
def credit_summary(request: Request, days: int = 30,
                   _identity: str = Depends(require_login),
                   db: Session = Depends(get_db)):
    """Chi tiêu của CHÍNH người gọi, đọc từ sổ credit nền tảng.

    Đơn vị là credit chứ không phải tiền tệ: quy đổi ở đây sẽ tạo cách tính giá
    thứ hai, mà Q31 đã chốt 1 credit = 100đ ở đúng một chỗ.
    """
    from datetime import datetime, timedelta, timezone

    from platform_core import credit
    from platform_core.models import CreditEntry

    user = _user(request)
    window = _as_int(days, 30, 1, 365)
    since = datetime.now(timezone.utc) - timedelta(days=window)

    rows = db.execute(
        select(CreditEntry)
        .where(CreditEntry.user_id == user.id, CreditEntry.created_at >= since)
        .order_by(CreditEntry.created_at.desc()).limit(200)
    ).scalars().all()

    spent = sum(-row.delta for row in rows if row.delta < 0)
    added = sum(row.delta for row in rows if row.delta > 0)
    return {
        "balance": credit.so_du(db, user.id),
        "days": window,
        "spent": spent,
        "added": added,
        "entries": [
            {"delta": row.delta, "kind": row.kind, "job_id": row.job_id,
             "note": row.note, "created_at": row.created_at.isoformat()}
            for row in rows[:60]],
    }


@router.get("/api/metrics")
def job_metrics(request: Request, days: int = 30,
                _identity: str = Depends(require_login),
                db: Session = Depends(get_db)):
    """Job chạy bao lâu, hỏng bao nhiêu, tốn bao nhiêu — của CHÍNH người gọi.

    P95 chứ không phải trung bình: trung bình bị kéo xuống bởi số đông job
    nhanh nên luôn nói "mọi thứ ổn", trong khi người dùng bỏ đi vì lần chờ
    *tệ*. Xem `services/metrics.py`.
    """
    from apps.prompt_ai_ommi.services import metrics as msvc
    user = _user(request)
    return msvc.job_metrics(db, user.id, days=_as_int(days, 30, 1, 365))
