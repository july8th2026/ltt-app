"""Sức khoẻ vận hành video_crawler: tỉ lệ thành công/lỗi theo nền trong một cửa sổ giờ.

Đọc THẲNG bảng `jobs` của nền tảng (`params.nen_tang`, `result.muc`/`result.loi`, `status`, `error`) —
không có bảng riêng cho sức khoẻ (một sổ, spec §13). Chỉ tính job **tải** (`video_crawler.tai`): khám
phá (`kham_pha`) miễn phí và không phản ánh "nền có tải được hay không".

Ba loại kết quả cho mỗi nền (PLAN_MVP §C dòng L4-a):
  - **mục tải xong** — phần tử trong `result["muc"]` của job `done` (đã lưu tệp).
  - **mục lỗi theo mã** — phần tử trong `result["loi"]` của job `done` (tải một phần), gộp theo `ma`
    (xem `apps/video_crawler/loi.py` cho ý nghĩa từng mã).
  - **job lỗi toàn phần** — job `error`: KHÔNG mục nào tải được (hoặc lỗi trước khi vào vòng tải).
    `jobs.py:_tai_voi` ném exception trước khi trả `result` trong ca này (`raise _loi_job(loi)`), nên
    chi tiết theo từng mục bị mất — chỉ còn đếm được ở mức job, không có `ma`.

Khuyến nghị TẮT (không tự ghi env — chỉ khuyến nghị, người vận hành đặt `LTT_VIDEO_CRAWLER_TAT`,
xem `nen_tang.py`) khi tỉ lệ thành công < 80% VÀ có ≥ 10 mục trong cửa sổ, để mẫu nhỏ không gây nhiễu.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from apps.video_crawler.jobs import JOB_TAI
from apps.video_crawler.manifest import MANIFEST
from platform_core.models import JOB_DONE, JOB_ERROR, Job

#: Dưới tỉ lệ này (0..1) thì khuyến nghị tắt nền — brief L4-a "< 80%".
NGUONG_TY_LE_THANH_CONG = 0.8
#: Cần ít nhất chừng này mục trong cửa sổ mới xét khuyến nghị tắt — brief L4-a "≥ 10 mục".
NGUONG_MAU_TOI_THIEU = 10

_KHONG_RO = "khong_ro"


@dataclass
class SucKhoeNen:
    """Sổ dồn cho một nền trong cửa sổ đang xét."""

    nen_tang: str
    muc_tai_xong: int = 0
    muc_loi_theo_ma: dict[str, int] = field(default_factory=dict)
    job_loi_toan_phan: int = 0
    tong_job: int = 0

    @property
    def muc_loi(self) -> int:
        return sum(self.muc_loi_theo_ma.values())

    @property
    def tong_muc(self) -> int:
        """Mục tải xong + mục lỗi + job lỗi toàn phần (mỗi job lỗi toàn phần tính là một mục lỗi, vì
        không biết chính xác đã thử bao nhiêu mục trước khi hỏng)."""
        return self.muc_tai_xong + self.muc_loi + self.job_loi_toan_phan

    @property
    def ty_le_thanh_cong(self) -> float | None:
        tong = self.tong_muc
        return None if tong == 0 else self.muc_tai_xong / tong

    @property
    def khuyen_nghi_tat(self) -> bool:
        tl = self.ty_le_thanh_cong
        return (tl is not None and self.tong_muc >= NGUONG_MAU_TOI_THIEU
                and tl < NGUONG_TY_LE_THANH_CONG)

    def to_dict(self) -> dict:
        return {
            "nen_tang": self.nen_tang,
            "muc_tai_xong": self.muc_tai_xong,
            "muc_loi": self.muc_loi,
            "muc_loi_theo_ma": dict(sorted(self.muc_loi_theo_ma.items())),
            "job_loi_toan_phan": self.job_loi_toan_phan,
            "tong_job": self.tong_job,
            "tong_muc": self.tong_muc,
            "ty_le_thanh_cong": self.ty_le_thanh_cong,
            "khuyen_nghi_tat": self.khuyen_nghi_tat,
        }


def thong_ke(db, *, gio: int = 24, bay_gio: datetime | None = None) -> dict[str, dict]:
    """`{nen_tang_id: SucKhoeNen.to_dict()}` cho job TẢI trong `gio` giờ gần nhất.

    Chỉ trả nền có ít nhất một job tải trong cửa sổ — nền chưa ai dùng thì không xuất hiện (không phải
    "0/0 = tắt vì lỗi"). Sắp theo id nền (registry giữ thứ tự riêng cho UI khách; vận hành đọc theo tên).
    """
    moc = (bay_gio or datetime.now(timezone.utc)) - timedelta(hours=max(0, gio))
    rows = db.execute(
        select(Job.params, Job.status, Job.result).where(
            Job.app_slug == MANIFEST.slug, Job.job_type == JOB_TAI, Job.created_at >= moc)
    ).all()
    theo_nen: dict[str, SucKhoeNen] = {}
    for params, status, result in rows:
        nen_id = str((params or {}).get("nen_tang") or _KHONG_RO)
        sk = theo_nen.setdefault(nen_id, SucKhoeNen(nen_tang=nen_id))
        sk.tong_job += 1
        if status == JOB_DONE:
            sk.muc_tai_xong += len((result or {}).get("muc") or [])
            for m in (result or {}).get("loi") or []:
                ma = str((m or {}).get("ma") or "loi_khac")
                sk.muc_loi_theo_ma[ma] = sk.muc_loi_theo_ma.get(ma, 0) + 1
        elif status == JOB_ERROR:
            sk.job_loi_toan_phan += 1
    return {nen_id: sk.to_dict() for nen_id, sk in sorted(theo_nen.items())}
