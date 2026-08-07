"""Chống spam L1 — cột `email_chuan` để kiểm trùng theo hộp thư thật

Gmail giao `a@gmail.com`, `a+1@gmail.com`, `a.b@gmail.com` về **cùng một hộp
thư**. Trước migration này hệ thống coi chúng là ba tài khoản khác nhau, mỗi cái
20 credit dùng thử — tức một hộp Gmail tạo được vô hạn tài khoản. Xác thực email
không cản được: chính người đó nhận hết thư xác thực.

Đo trước khi viết (CSDL production 2026-08-07): 13 tài khoản, **0 va chạm** sau
chuẩn hoá — nên backfill chạy sạch. Hai địa chỉ đổi giá trị chuẩn hoá:
`akakenly.design@gmail.com` -> `akakenlydesign@gmail.com`,
`dungnv.forwork@gmail.com` -> `dungnvforwork@gmail.com`. **Email gốc giữ nguyên**;
cột mới chỉ dùng để chống trùng.

CỐ Ý KHÔNG đặt ràng buộc UNIQUE ở migration này. Lý do: nếu về sau luật chuẩn hoá
đổi (thêm nhà cung cấp), một UNIQUE cứng sẽ làm migration đó nổ giữa chừng trên
bảng người dùng. Chống trùng thực thi ở `users.tao_nguoi_dung()`, và cột có chỉ
mục nên tra cứu vẫn nhanh.

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None

_ALIAS = {"gmail.com", "googlemail.com"}


def _chuan(email: str) -> str:
    e = (email or "").strip().lower()
    if "@" not in e:
        return e
    ten, mien = e.rsplit("@", 1)
    if mien == "googlemail.com":
        mien = "gmail.com"
    if mien in _ALIAS:
        ten = ten.split("+", 1)[0].replace(".", "")
    return f"{ten}@{mien}"


def upgrade() -> None:
    op.add_column("users", sa.Column("email_chuan", sa.String(255),
                                     nullable=False, server_default=""))
    op.create_index("ix_users_email_chuan", "users", ["email_chuan"])

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, email FROM users")).fetchall()

    # Đếm va chạm TRƯỚC khi ghi. Không tự gộp hay xoá tài khoản — đó là dữ liệu
    # người dùng, và hai tài khoản trùng hộp thư có thể là hai người thật đã dùng
    # dịch vụ. Nổ ở đây để người vận hành đối soát tay còn hơn âm thầm làm sai.
    thay = {}
    va_cham = {}
    for _id, email in rows:
        k = _chuan(email)
        if k in thay:
            va_cham.setdefault(k, [thay[k]]).append(email)
        thay[k] = email
    if va_cham:
        raise RuntimeError(
            "Co tai khoan trung nhau sau khi chuan hoa email: "
            + "; ".join(f"{k} <- {v}" for k, v in va_cham.items())
            + ". KHONG tu gop — doi soat tay roi chay lai.")

    for _id, email in rows:
        bind.execute(sa.text("UPDATE users SET email_chuan = :c WHERE id = :i"),
                     {"c": _chuan(email), "i": _id})


def downgrade() -> None:
    op.drop_index("ix_users_email_chuan", table_name="users")
    op.drop_column("users", "email_chuan")
