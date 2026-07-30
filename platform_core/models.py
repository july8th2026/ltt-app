"""
models.py — lược đồ CSDL của nền tảng.

Mọi model kế thừa `platform_core.db.Base`. Alembic dò `Base.metadata` để sinh
migration, nên **model mới phải được import ở đây** (hoặc import gián tiếp từ
đây), nếu không Alembic sẽ không thấy và sinh ra một migration rỗng.

Quy ước đặt tên: dùng tiếng Anh cho tên bảng và tên cột (chúng xuất hiện trong
câu lệnh SQL, công cụ quản trị, thông báo lỗi của driver), tiếng Việt cho phần
giải thích.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base


def _bay_gio() -> datetime:
    """Thời điểm hiện tại, luôn kèm múi giờ.

    Dùng hàm thay vì `datetime.utcnow` vì `utcnow()` trả về datetime **không có
    múi giờ**, và một giá trị như vậy đem so sánh với giá trị có múi giờ sẽ ném
    TypeError ở đúng chỗ khó ngờ nhất.
    """
    return datetime.now(timezone.utc)


class PlatformInfo(Base):
    """Một dòng duy nhất ghi lược đồ này được dựng khi nào, bởi bản nào.

    Vì sao cần: khi hỗ trợ một cài đặt đang gặp sự cố, câu hỏi đầu tiên luôn là
    "CSDL này dựng lúc nào, bằng bản nào". Không có bảng này thì phải đoán qua
    log — mà log thì bị xoay vòng.

    Đây cũng là bảng của migration đầu tiên, nên nó làm cho việc kiểm chứng
    `upgrade` → `downgrade` → `upgrade` có ý nghĩa thật.
    """

    __tablename__ = "platform_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_bay_gio, nullable=False)
    app_version: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    def __repr__(self) -> str:      # pragma: no cover - chi de doc khi go roi
        return f"<PlatformInfo v{self.app_version} @ {self.installed_at:%Y-%m-%d}>"
