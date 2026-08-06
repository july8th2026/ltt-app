"""
metrics.py — job của OMMI chạy bao lâu và tốn bao nhiêu (H19.8).

Câu hỏi thật cần trả lời: *"chậm ở đâu, tốn ở đâu"*. Không có số thì mọi quyết
định tối ưu đều là phỏng đoán, và phỏng đoán thường nhắm vào thứ dễ nhìn thấy
chứ không phải thứ đắt nhất.

Vì sao **P95** chứ không phải trung bình: trung bình bị kéo xuống bởi số đông
job nhanh, nên nó luôn nói "mọi thứ ổn". Người dùng bỏ đi vì lần chờ *tệ*, không
vì lần chờ trung bình. P95 là con số mô tả trải nghiệm tệ mà vẫn còn thường
gặp — P100 thì lại là một lần bất thường duy nhất.

Mọi số ở đây tính theo **từng người dùng**, không gộp toàn hệ thống: Q31 chốt
credit tính theo từng người, và gộp lại sẽ để người này nhìn thấy khối lượng
việc của người khác.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.prompt_ai_ommi.manifest import MANIFEST


def _phan_vi(mau: list[float], p: float) -> float:
    """Phân vị theo phép nội suy tuyến tính. Danh sách rỗng → 0.0.

    Tự tính thay vì dùng `statistics.quantiles`: hàm đó cần ít nhất 2 mẫu và
    ném khi chỉ có 1 — mà "một job trong 30 ngày" là trạng thái hoàn toàn bình
    thường của một người dùng mới.
    """
    if not mau:
        return 0.0
    xep = sorted(mau)
    if len(xep) == 1:
        return float(xep[0])
    vi_tri = (len(xep) - 1) * p
    duoi = int(vi_tri)
    tren = min(duoi + 1, len(xep) - 1)
    le = vi_tri - duoi
    return float(xep[duoi] * (1 - le) + xep[tren] * le)


def job_metrics(db: Session, owner_id: str, *, days: int = 30,
                bay_gio: datetime | None = None) -> dict:
    """Thời gian chạy và chi phí job OMMI của MỘT người, tách theo loại việc."""
    from platform_core.models import JOB_CANCELLED, JOB_DONE, JOB_ERROR, Job

    moc = (bay_gio or datetime.now(timezone.utc)) - timedelta(days=max(1, days))
    rows = db.execute(
        select(Job).where(Job.user_id == owner_id,
                          Job.app_slug == MANIFEST.slug,
                          Job.created_at >= moc)
        .order_by(Job.created_at.desc()).limit(2000)
    ).scalars().all()

    theo_viec: dict[str, dict] = {}
    for job in rows:
        viec = str((job.params or {}).get("operation") or job.job_type or "khac")
        o = theo_viec.setdefault(viec, {"tong": 0, "xong": 0, "loi": 0, "huy": 0,
                                        "giay": [], "credit": 0})
        o["tong"] += 1
        if job.status == JOB_DONE:
            o["xong"] += 1
        elif job.status == JOB_ERROR:
            o["loi"] += 1
        elif job.status == JOB_CANCELLED:
            o["huy"] += 1

        bat_dau, ket_thuc = job.started_at, job.finished_at
        if bat_dau and ket_thuc:
            if bat_dau.tzinfo is None:
                bat_dau = bat_dau.replace(tzinfo=timezone.utc)
            if ket_thuc.tzinfo is None:
                ket_thuc = ket_thuc.replace(tzinfo=timezone.utc)
            giay = (ket_thuc - bat_dau).total_seconds()
            if giay >= 0:
                o["giay"].append(giay)
        o["credit"] += int((job.result or {}).get("credit_cost") or 0)

    ra = []
    for viec, o in sorted(theo_viec.items()):
        giay = o.pop("giay")
        ra.append({
            "viec": viec, **o,
            "so_do_duoc": len(giay),
            "p50_giay": round(_phan_vi(giay, 0.50), 1),
            "p95_giay": round(_phan_vi(giay, 0.95), 1),
            # Tỉ lệ hỏng là thứ người vận hành nhìn trước tiên; tính sẵn để giao
            # diện không phải tự chia rồi chia sai khi `tong` bằng 0.
            "ti_le_loi": round(o["loi"] / o["tong"], 3) if o["tong"] else 0.0,
        })

    tat_ca_giay = [g for o in theo_viec.values() for g in o.get("giay", [])]
    return {
        "days": days,
        "tong_job": len(rows),
        "tong_credit": sum(o["credit"] for o in theo_viec.values()),
        "p95_giay": round(_phan_vi(tat_ca_giay, 0.95), 1),
        "theo_viec": ra,
    }
