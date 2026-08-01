"""them bang thanh toan: credit_packages + payment_orders (H9)

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-08-01 14:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f0a1b2c3d4e5'
down_revision: Union[str, None] = 'e9f0a1b2c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'credit_packages',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('name', sa.String(length=120), nullable=False, server_default=''),
        sa.Column('price_vnd', sa.Integer(), nullable=False),
        sa.Column('credits_base', sa.Integer(), nullable=False),
        sa.Column('bonus_percent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'payment_orders',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('order_code', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('package_id', sa.String(length=36), nullable=False, server_default=''),
        sa.Column('price_vnd', sa.Integer(), nullable=False),
        sa.Column('credits', sa.Integer(), nullable=False),
        sa.Column('bonus_percent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='pending'),
        sa.Column('credited', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('gateway', sa.String(length=32), nullable=False, server_default=''),
        sa.Column('gateway_ref', sa.String(length=120), nullable=False, server_default=''),
        sa.Column('checkout_url', sa.String(length=500), nullable=False, server_default=''),
        sa.Column('note', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_payment_orders_order_code', 'payment_orders', ['order_code'], unique=True)
    op.create_index('ix_payment_orders_user_id', 'payment_orders', ['user_id'])
    op.create_index('ix_payment_orders_status', 'payment_orders', ['status'])


def downgrade() -> None:
    op.drop_index('ix_payment_orders_status', table_name='payment_orders')
    op.drop_index('ix_payment_orders_user_id', table_name='payment_orders')
    op.drop_index('ix_payment_orders_order_code', table_name='payment_orders')
    op.drop_table('payment_orders')
    op.drop_table('credit_packages')
