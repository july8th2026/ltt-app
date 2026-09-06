"""Chỉ số FTS cho `chatltt_doan` — và vì sao phải bọc `unaccent`. (H44 P06 b4)

## 🔴 Ràng buộc quyết định: `unaccent` là STABLE, không IMMUTABLE

Đo 06/09 trên chính máy chủ:

    SELECT provolatile FROM pg_proc WHERE proname='unaccent'  ->  's'  (STABLE)

Postgres **từ chối** biểu thức chỉ số không IMMUTABLE. Nên
`CREATE INDEX ... to_tsvector('simple', unaccent(noi_dung))` không chạy được.

## Hai lối ra, và tôi đã đo cái tưởng an toàn hơn TRƯỚC khi loại nó

Lối thứ hai nghe sạch hơn: bỏ dấu **ở Python** rồi lưu vào một cột phụ, và chỉ
số chạy trên cột ấy — hoàn toàn IMMUTABLE, không phải hứa gì với bộ tối ưu.

Đo thì nó **đổi hành vi tìm kiếm**:

    goc              Postgres unaccent   Python NFD
    "Đầu tư"         Dau tu              Đau tu       ✗
    "đồng"           dong                đong         ✗
    "Số điện thoại"  So dien thoai       So đien thoai ✗
    "Việt Nam"       Viet Nam            Viet Nam     ✓

Postgres ánh xạ **`đ → d`**; `unicodedata.normalize("NFD")` thì không, vì `đ`
là một ký tự riêng chứ không phải `d` + dấu tổ hợp. Ba trên sáu mẫu lệch, và
chúng là từ **rất thường** trong tiếng Việt.

⇒ Người gõ `"dong"` sẽ **không tìm ra** `"đồng"` — trái đúng điều `test_821` đã
  đo và chốt. Lối đó bị loại vì **hành vi**, không vì cú pháp.

## Nên: bọc bằng một hàm IMMUTABLE, và nói rõ ta đang hứa gì

    CREATE FUNCTION f_unaccent(text) RETURNS text
    AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$ LANGUAGE sql IMMUTABLE

⭐ Dạng **hai tham số** (`public.unaccent('public.unaccent'::regdictionary, $1)`) là thứ làm lời hứa này bảo
   vệ được: nó gọi đích danh từ điển. Dạng một tham số tra từ điển mặc định qua
   `search_path`, tức kết quả phụ thuộc phiên — và khi đó `IMMUTABLE` là một
   lời nói dối thật sự với bộ tối ưu.

⚠️ **Ta vẫn đang hứa một điều có điều kiện**: rằng tệp từ điển `unaccent.rules`
   không đổi. Nếu ai đó sửa nó, chỉ số thành sai **lặng lẽ** — hàng cũ giữ giá
   trị cũ. Cách chữa khi điều đó xảy ra: `REINDEX INDEX ix_chatltt_doan_fts`.
   Ghi ở đây vì đó là loại sự thật không ai nhớ ra vào lúc cần.

## Migration CHỈ THÊM

Một hàm mới + một chỉ số mới. Không `alter`, không `drop`, không chạm hàng nào.
Hạ lại là bỏ đúng hai thứ vừa tạo.

Revision ID: b8c31f6e9d24
Revises: e5b2d9c4a71f
"""
from __future__ import annotations

from alembic import op

revision = "b8c31f6e9d24"
down_revision = "e5b2d9c4a71f"
branch_labels = None
depends_on = None

#: Tên hàm bọc. Dùng ở `apps/chatltt/services/tim_doan.py` — một chỗ khai, một
#: chỗ dùng, để hai bên không lệch tên rồi hỏng lặng lẽ.
HAM = "f_unaccent"
CHI_SO = "ix_chatltt_doan_fts"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return          # SQLite (test cuc bo) khong co tsvector lan unaccent
    op.execute(
        f"CREATE OR REPLACE FUNCTION {HAM}(text) RETURNS text "
        "AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$ "
        "LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT")
    op.execute(
        f"CREATE INDEX IF NOT EXISTS {CHI_SO} ON chatltt_doan "
        f"USING GIN (to_tsvector('simple', {HAM}(noi_dung)))")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(f"DROP INDEX IF EXISTS {CHI_SO}")
    op.execute(f"DROP FUNCTION IF EXISTS {HAM}(text)")
