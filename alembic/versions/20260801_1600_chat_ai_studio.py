"""them bang chat ai studio: chat_conversations + chat_messages (CHAT AI STUDIO)

Revision ID: a1b2c3d4e5f6
Revises: f0a1b2c3d4e5
Create Date: 2026-08-01 16:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f0a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'chat_conversations',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('model', sa.String(length=64), nullable=False, server_default='gpt-5.6-sol'),
        sa.Column('custom_instructions', sa.Text(), nullable=False, server_default=''),
        sa.Column('codex_thread_id', sa.String(length=64), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_chat_conversations_user_id', 'chat_conversations', ['user_id'])
    op.create_index('ix_chat_conversations_updated_at', 'chat_conversations', ['updated_at'])

    op.create_table(
        'chat_messages',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False, server_default='user'),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('image_key', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('image_prompt', sa.String(length=500), nullable=False, server_default=''),
        sa.Column('tokens_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_chat_messages_conversation_id', 'chat_messages', ['conversation_id'])
    op.create_index('ix_chat_messages_user_id', 'chat_messages', ['user_id'])
    op.create_index('ix_chat_messages_conv_created', 'chat_messages',
                    ['conversation_id', 'created_at'])


def downgrade() -> None:
    op.drop_table('chat_messages')
    op.drop_table('chat_conversations')
