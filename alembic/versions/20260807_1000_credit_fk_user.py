"""F-01 — khoá ngoại credit_entries.user_id -> users.id

Audit LTT-AQA 2026-08-07 (control-plane/quan-tri-user), finding F-01, severity P0.

Trước migration này, cấp credit cho một UUID không tồn tại vẫn ghi bút toán và
báo thành công. Hai tầng cùng thiếu kiểm: `cap_tay()` gọi thẳng `_ghi()`, và bảng
không có ràng buộc nào. `cap_tay()` đã kiểm ở tầng nghiệp vụ; khoá ngoại ở đây là
**lưới an toàn cuối** cho mọi đường ghi khác — kể cả đường ai đó thêm sau này.

Đo trước khi viết (E2, CSDL production 2026-08-07): **0 bút toán mồ côi**, nên
migration chạy sạch, không phải dọn dữ liệu.

`ondelete="RESTRICT"`: KHÔNG cho xoá người dùng còn bút toán credit. Sổ credit là
append-only và là bằng chứng đối soát tiền; xoá người dùng mà mất sổ của họ thì
không đối soát được nữa. Muốn ngừng một tài khoản thì dùng `is_active=False`.

Revision ID: c1d2e3f4a5b6
Revises: e5f6a4b5c6d7
"""
from __future__ import annotations

from alembic import op

revision = "c1d2e3f4a5b6"
down_revision = "e5f6a4b5c6d7"
branch_labels = None
depends_on = None

TEN = "fk_credit_entries_user_id"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite (test) không thêm được FK vào bảng đã tồn tại mà không dựng lại
        # bảng. Tầng nghiệp vụ `cap_tay()` đã chặn, và test chạy trên SQLite vẫn
        # phủ được hành vi đó — nên bỏ qua ở đây thay vì dựng lại bảng chứa tiền.
        return

    # Dọn trước khi ràng buộc. Hiện production là 0 dòng, nhưng máy khác có thể
    # khác — và một migration nổ giữa chừng ở bảng tiền là thứ phải tránh.
    mo_coi = bind.exec_driver_sql(
        "SELECT count(*) FROM credit_entries ce "
        "LEFT JOIN users u ON u.id = ce.user_id WHERE u.id IS NULL").scalar()
    if mo_coi:
        raise RuntimeError(
            f"Co {mo_coi} but toan credit tro toi nguoi dung khong ton tai. "
            "KHONG tu xoa — day la du lieu tien. Doi soat tay roi chay lai.")

    op.create_foreign_key(TEN, "credit_entries", "users",
                          ["user_id"], ["id"], ondelete="RESTRICT")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_constraint(TEN, "credit_entries", type_="foreignkey")
