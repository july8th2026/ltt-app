"""them project cho Public API + rang buoc IP cho developer key (EXT-04)

Phan cap so huu: User -> Project -> Key. Project la don vi de THU HOI, DAT NGAN
SACH va DOC LOG theo tung tich hop; billing van thuoc User (Q92), khong dung
tang organization thu hai.

Di tru an toan cho du lieu V2 dang co: cot project_id NULLABLE, roi backfill
mot project "Default" cho moi tai khoan dang so huu key. Khoa cu chay y nguyen
o moi buoc; khong co thoi diem nao key mat quyen.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_projects",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False,
                  server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        # Slug duy nhat TRONG mot tai khoan, khong duy nhat toan he thong: hai
        # khach hang deu duoc dat ten "website".
        sa.UniqueConstraint("user_id", "slug", name="uq_api_project_owner_slug"),
    )
    op.create_index("ix_api_projects_user_id", "api_projects", ["user_id"])
    op.create_index("ix_api_projects_owner_status", "api_projects",
                    ["user_id", "status"])

    op.add_column("developer_api_keys",
                  sa.Column("project_id", sa.String(36), nullable=True))
    op.add_column("developer_api_keys",
                  sa.Column("allowed_ips", sa.JSON(), nullable=False,
                            server_default="[]"))
    op.create_index("ix_developer_api_keys_project_id", "developer_api_keys",
                    ["project_id"])
    if op.get_bind().dialect.name != "sqlite":
        # SQLite khong ALTER them duoc rang buoc; batch mode se COPY ca bang
        # developer_api_keys sang bang moi roi doi ten — dat va rui ro tren mot
        # bang chua credential, doi lay mot rang buoc ma production (PostgreSQL,
        # Q1) van co day du. SQLite chi dung cho test/dev.
        op.create_foreign_key("fk_developer_api_keys_project",
                              "developer_api_keys", "api_projects",
                              ["project_id"], ["id"], ondelete="RESTRICT")

    _backfill_default_projects()


def _backfill_default_projects() -> None:
    """Moi tai khoan dang so huu key nhan mot project 'Default', va key tro vao do.

    Lam trong cung migration nay chu khong de lazy: mot key khong project van
    chay duoc, nhung se khong hien ra o bat ky man hinh nao nhom theo project —
    tuc la bien mat ve mat van hanh du van tieu tien duoc.
    """
    connection = op.get_bind()
    owners = connection.execute(sa.text(
        "SELECT DISTINCT user_id FROM developer_api_keys "
        "WHERE project_id IS NULL")).fetchall()
    now = sa.func.now()
    for (user_id,) in owners:
        existing = connection.execute(
            sa.text("SELECT id FROM api_projects "
                    "WHERE user_id = :uid AND slug = 'default'"),
            {"uid": user_id}).fetchone()
        project_id = existing[0] if existing else str(uuid.uuid4())
        if not existing:
            connection.execute(
                sa.text("INSERT INTO api_projects "
                        "(id, user_id, name, slug, status, created_at) "
                        "VALUES (:id, :uid, 'Default', 'default', 'active', "
                        "        CURRENT_TIMESTAMP)"),
                {"id": project_id, "uid": user_id})
        connection.execute(
            sa.text("UPDATE developer_api_keys SET project_id = :pid "
                    "WHERE user_id = :uid AND project_id IS NULL"),
            {"pid": project_id, "uid": user_id})
    del now


def downgrade() -> None:
    # Bo rang buoc truoc, roi cot, roi bang: thu tu nguoc voi upgrade.
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_developer_api_keys_project", "developer_api_keys",
                           type_="foreignkey")
    op.drop_index("ix_developer_api_keys_project_id",
                  table_name="developer_api_keys")
    op.drop_column("developer_api_keys", "allowed_ips")
    op.drop_column("developer_api_keys", "project_id")
    op.drop_index("ix_api_projects_owner_status", table_name="api_projects")
    op.drop_index("ix_api_projects_user_id", table_name="api_projects")
    op.drop_table("api_projects")
