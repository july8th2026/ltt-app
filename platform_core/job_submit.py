"""
job_submit.py — nộp job KÈM giữ chỗ credit, trong một giao dịch (H3 × H2).

Đây là chỗ hai thứ phải atomic gặp nhau: tạo job và trừ (giữ chỗ) credit. Cả
hai cùng một `db` session, caller commit một lần — hoặc cả hai thành, hoặc cả
hai rollback. Không bao giờ có job không trả tiền, hay tiền trừ mà không có job.

Thứ tự có chủ ý:
1. `credit_for(...)` tính giá TRƯỚC — nếu app không khai giá thì registry từ
   chối ngay, job không được tạo (khớp bất biến "job không tra được giá thì bị
   từ chối chạy", không chạy miễn phí).
2. `jobs.submit(...)` — dedupe ở đây: gửi trùng khi job cũ còn chạy trả lại job
   cũ.
3. Chỉ giữ chỗ khi job là MỚI (chưa có hold) — nếu dedupe trả job cũ đã giữ
   chỗ rồi thì KHÔNG giữ lần nữa (không trừ tiền hai lần cho một lần bấm lại).
   Đây là chốt chặn nút "Tạo lại" / F5 / double-submit.
"""
from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session as DbSession

from platform_core import credit, jobs
from platform_core.models import Job


def dedupe_key_for(job_type: str, params: dict) -> str:
    """Khoá dedupe ổn định cho một yêu cầu: cùng `job_type` + cùng `params` →
    cùng khoá. `jobs.submit` chỉ dedupe với job CHƯA kết thúc của cùng user, nên
    F5 / double-click / bấm "Tạo lại" trong lúc job đang chạy sẽ trả về job cũ
    (không tạo job mới, KHÔNG trừ tiền lần hai); job xong rồi thì gửi lại tạo job
    mới bình thường. Mọi route submit NÊN truyền khoá này để chặn double-submit.
    """
    canon = json.dumps(params or {}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(f"{job_type}\x00{canon}".encode("utf-8")).hexdigest()


def submit_with_credit(
    db: DbSession, *, user_id: str, app_slug: str, job_type: str,
    params: dict, dedupe_key: str = "", max_attempts: int = 3,
) -> Job:
    """Nộp job và giữ chỗ credit trong cùng transaction. KHÔNG commit — caller
    commit (nhờ vậy job + credit cùng thành hoặc cùng bại).

    Raise `credit.ThieuCreditError` nếu không đủ (job sẽ rollback cùng), hoặc
    `registry.RegistryError` nếu job_type không tra được giá.
    """
    from platform_core.registry import credit_for

    estimate = int(credit_for(job_type, params))   # raise sớm nếu không có giá

    job = jobs.submit(db, user_id=user_id, app_slug=app_slug, job_type=job_type,
                      params=params, dedupe_key=dedupe_key, max_attempts=max_attempts)

    # Chỉ giữ chỗ cho job MỚI. Dedupe trả job cũ → đã giữ rồi → bỏ qua.
    if credit.so_da_giu(db, job.id) == 0 and estimate > 0:
        credit.giu_cho(db, user_id, estimate, job.id)   # raise ThieuCredit → rollback
    return job
