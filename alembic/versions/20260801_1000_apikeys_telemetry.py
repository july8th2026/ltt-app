"""them cot telemetry cho api_keys (H8 Pha 2 - rpm/tpm/token + cua so)

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-08-01 10:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e9f0a1b2c3d4'
down_revision: Union[str, None] = 'd8e9f0a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('api_keys', sa.Column('rpm_limit', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('api_keys', sa.Column('tpm_limit', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('api_keys', sa.Column('total_tokens', sa.BigInteger(), nullable=False, server_default='0'))
    op.add_column('api_keys', sa.Column('window_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('api_keys', sa.Column('window_requests', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('api_keys', sa.Column('window_tokens', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('api_keys', 'window_tokens')
    op.drop_column('api_keys', 'window_requests')
    op.drop_column('api_keys', 'window_start')
    op.drop_column('api_keys', 'total_tokens')
    op.drop_column('api_keys', 'tpm_limit')
    op.drop_column('api_keys', 'rpm_limit')
