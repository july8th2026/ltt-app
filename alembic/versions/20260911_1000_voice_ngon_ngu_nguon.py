"""voice_profile.ngon_ngu_nguon — nguồn gốc làn (RC1, D003).

Đánh dấu MỌI dòng đã có là `mac_dinh_cu`: trước 08/09 form ghi danh không có ô
ngôn ngữ, sau 08/09 form chọn sẵn `vi` — không dòng nào có lời khai chắc chắn.
KHÔNG gán lại `ngon_ngu`. Đo làn thật là việc của `tools/di_tru_lan_asr.py`.

⚠️ `down_revision` trỏ tới `e26c9a41d8b5` (job_scheduler_envelope, 20260910),
không phải `d15b8c30f7a4` như bản gốc: trunk merge mang theo migration đó với
CÙNG cha `d15b8c30f7a4`, tạo hai head (`e26c9a41d8b5`, `d9a1f6c2b3e5`). Cả hai
migration đều additive và không đụng bảng của nhau — nối lại theo thứ tự này
để `alembic upgrade head` chỉ còn đúng một head.
"""
from alembic import op
import sqlalchemy as sa

revision = "e1a2b3c4d5f6"
down_revision = "e26c9a41d8b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("voice_profile") as b:
        b.add_column(sa.Column("ngon_ngu_nguon", sa.String(16),
                               nullable=False, server_default=""))
    op.execute("UPDATE voice_profile SET ngon_ngu_nguon = 'mac_dinh_cu'")


def downgrade() -> None:
    with op.batch_alter_table("voice_profile") as b:
        b.drop_column("ngon_ngu_nguon")
