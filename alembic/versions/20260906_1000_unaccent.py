"""unaccent — để tìm kiếm tiếng Việt KHÔNG DẤU tìm được văn bản CÓ DẤU

## Vì sao cần, và nó không phải "cho đẹp"

Đo 06/09 trên chính máy chủ production, gọi thẳng `to_tsvector`/`plainto_tsquery`
(không tạo bảng, không ghi gì):

    van ban: "Gia moi luot goi duoc tinh theo so token that su dung.
              Phan le duoi mot credit duoc cong don sang luot sau."  (co dau)

    cau hoi                    khong unaccent   co unaccent
    "phần lẻ credit"  (co dau)       KHOP            KHOP
    "phan le credit"  (khong dau)     -              KHOP
    "cong don luot sau"               -              KHOP
    "so token that su dung"           -              KHOP

🔴 Bốn dòng dưới là ca **thường gặp nhất**: người Việt gõ nhanh thì gõ không
dấu. Một tìm kiếm không tìm được `"phan le credit"` là một tính năng phần lớn
người dùng thấy là hỏng — không phải một góc hiếm.

⛔ Ví dụ đầu tôi dùng ở đây (`"tinh tien theo token"`) là ví dụ **bẩn**: nó trượt
ở **cả hai** chế độ vì từ `"tiền"` không có trong văn bản mẫu, chứ không vì
thiếu dấu. `test_821` bác nó khi chạy trên PostgreSQL thật.

Postgres **không có** cấu hình `vietnamese` (30 cấu hình có sẵn, không cái nào).
Nhưng `simple` tách từ tiếng Việt **đúng** — theo khoảng trắng, hạ chữ thường,
giữ nguyên dấu. Nên thứ còn thiếu chỉ là **bỏ dấu**, và `unaccent` làm đúng việc
ấy.

## Vì sao đây là migration bình thường chứ không phải việc cần người

    tai khoan ltt_app   superuser = False   CREATE tren CSDL = True
    unaccent 1.1        trusted   = True

Từ PostgreSQL 13, một phần mở rộng đánh dấu **trusted** cài được bởi người dùng
chỉ cần quyền `CREATE` trên CSDL — không cần superuser.

⛔ Khác hẳn `pgvector`, thứ **không có trên máy này** (đo: 0 phần mở rộng tên
chứa `vector`) và cài nó là một thao tác cấp máy chủ. Hai thứ cùng gọi là "một
extension" nhưng khác nhau ở chỗ quyết định: **có sẵn hay không**.

## Vì sao KHÔNG kèm `pg_trgm` dù nó cũng trusted và cũng có sẵn

`pg_trgm` giải một bài khác — gõ **sai chính tả**, không phải gõ **thiếu dấu**.
P06 chưa có phép đo nào nói rằng sai chính tả là vấn đề ở đây. Thêm một phần mở
rộng "vì nó có sẵn" là thêm một thứ phải bảo trì cho một nhu cầu chưa đo được.

⭐ Migration **chỉ thêm**. Hạ nó lại là `DROP EXTENSION`, và không mất một hàng
dữ liệu nào — `unaccent` không lưu gì, nó chỉ là một hàm.

⚠️ `IF NOT EXISTS` có chủ ý: CSDL test có thể đã có sẵn từ một lượt trước, và
một migration ném vì thứ nó muốn **đã đúng rồi** là một migration sai.

Revision ID: c7d41e8a2b93
Revises: 9f3a71b4c2e8
"""
from __future__ import annotations

from alembic import op

revision = "c7d41e8a2b93"
down_revision = "9f3a71b4c2e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return          # SQLite (test cuc bo) khong co khai niem extension
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP EXTENSION IF EXISTS unaccent")
