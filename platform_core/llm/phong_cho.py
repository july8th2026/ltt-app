"""phong_cho.py — phòng chờ của cửa TƯƠNG TÁC tới model nhà, và sổ từng lượt. (multijob)

⭐ MỘT hàng, liên tiến trình: dòng nằm trong CSDL (`llm_waiters`) nên mọi web worker
   cùng thấy cùng một thứ tự. Không phải hàng thứ hai của `jobs` (việc nền không có
   dòng ở đây), không phải hàng ẩn trong một tiến trình, không phải hàng ở gateway.

⭐ Bảng cũng là SỔ TỪNG LƯỢT, giữ 30 ngày để phân tích sau khi mở vận hành (chủ dự
   án yêu cầu 11/09): lúc vào, lúc được nhận, lúc xong, lý do chờ cuối, số nhịp.

Spec: `docs/superpowers/specs/2026-09-11-ltt-llm-multijob-design.md` §4.2, §5, §9.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from platform_core.models import LlmWaiter

#: Một người chờ phải đập nhịp (mỗi lần hỏi lại) trong khoảng này; quá thì coi như
#: tiến trình đang giữ nó đã chết và dòng không còn tranh chỗ.
HAN_NHIP_CHO_S = 10.0

#: Dòng `cho` im lặng quá lâu (tiến trình web chết giữa lúc chờ) bị vòng dọn chốt
#: thành `het_han` — để sổ lượt không nói "đang chờ" mãi mãi.
HAN_CHO_MO_COI = timedelta(minutes=10)

#: Sổ lượt ở lại 30 ngày (`governance.py`: OPERATIONAL, 30).
GIU_SO_LUOT = timedelta(days=30)


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


def _aware(t: datetime) -> datetime:
    return t if t.tzinfo is not None else t.replace(tzinfo=timezone.utc)


def chup_nguoi_cho(db: Session, *, resource: str,
                   now: datetime | None = None) -> list:
    """Người đang chờ CÒN SỐNG của một tài nguyên, dưới dạng `luat_nhan.Luot`.

    Dòng mất nhịp quá `HAN_NHIP_CHO_S` không còn tranh chỗ: tiến trình giữ nó đã
    chết hoặc treo, và để nó chặn FCFS là để một xác chết giữ hàng.
    """
    from platform_core.llm import luat_nhan

    now = now or _bay_gio()
    ra = []
    for w in (db.query(LlmWaiter)
              .filter(LlmWaiter.resource == resource, LlmWaiter.trang_thai == "cho")
              .all()):
        if (now - _aware(w.heartbeat_at)).total_seconds() > HAN_NHIP_CHO_S:
            continue
        ra.append(luat_nhan.Luot(
            id=w.id, user_id=w.user_id, lop=w.lop or luat_nhan.TUONG_TAC,
            token_dat_truoc=int(w.token_dat_truoc or 0), la_whale=bool(w.la_whale),
            tuoi_s=max(0.0, (now - _aware(w.created_at)).total_seconds())))
    return ra


def don_het_han(db: Session, *, now: datetime | None = None) -> int:
    """Vòng dọn của worker (`job_runner._don_du_lieu_het_han`). Trả số dòng đã đụng.

    Hai việc, cả hai idempotent:
      1. dòng `cho` mất nhịp quá `HAN_CHO_MO_COI` ⇒ `het_han` (tiến trình chết lúc chờ);
      2. xoá dòng tạo trước `GIU_SO_LUOT` (30 ngày).
    """
    now = now or _bay_gio()
    mo_coi = 0
    for w in db.query(LlmWaiter).filter(LlmWaiter.trang_thai == "cho").all():
        if now - _aware(w.heartbeat_at) > HAN_CHO_MO_COI:
            w.trang_thai = "het_han"
            w.ket_qua = w.ket_qua or "mat_nhip"
            w.finished_at = now
            mo_coi += 1
    if mo_coi:
        db.flush()
    # `synchronize_session=False`: SQLite trả giờ KHÔNG múi, `now` có múi — để
    # SQLAlchemy tự đối chiếu phiên trong Python là so hai kiểu giờ, và nó ném.
    xoa = db.execute(
        delete(LlmWaiter).where(LlmWaiter.created_at < now - GIU_SO_LUOT)
        .execution_options(synchronize_session=False)
    ).rowcount or 0
    return mo_coi + int(xoa)
