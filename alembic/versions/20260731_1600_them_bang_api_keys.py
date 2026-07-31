"""them bang api_keys (H8 - bo may APIKEYS)

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-07-31 16:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd8e9f0a1b2c3'
down_revision: Union[str, None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('owner_user_id', sa.String(length=36), nullable=False, server_default=''),
        sa.Column('name', sa.String(length=120), nullable=False, server_default=''),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('categories', sa.JSON(), nullable=False),
        sa.Column('credential_enc', sa.Text(), nullable=False),
        sa.Column('key_preview', sa.String(length=16), nullable=False, server_default=''),
        sa.Column('base_url', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('supported_models', sa.JSON(), nullable=False),
        sa.Column('default_model', sa.String(length=64), nullable=False, server_default=''),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='active'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('health_score', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('auth_error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cooldown_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.String(length=500), nullable=False, server_default=''),
        sa.Column('total_requests', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_success', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_api_keys_owner_user_id', 'api_keys', ['owner_user_id'])
    op.create_index('ix_api_keys_provider', 'api_keys', ['provider'])
    op.create_index('ix_api_keys_status', 'api_keys', ['status'])


def downgrade() -> None:
    op.drop_index('ix_api_keys_status', table_name='api_keys')
    op.drop_index('ix_api_keys_provider', table_name='api_keys')
    op.drop_index('ix_api_keys_owner_user_id', table_name='api_keys')
    op.drop_table('api_keys')
