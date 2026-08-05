"""Initial schema - All LinguaMate AI tables

Revision ID: 001_initial
Revises:
Create Date: 2026-08-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Users ────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.Text, nullable=False),
        sa.Column('english_level', sa.String(20), server_default='beginner'),
        sa.Column('goal', sa.Text, nullable=True),
        sa.Column('avatar_emoji', sa.String(10), server_default='😊'),
        sa.Column('parent_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "english_level IN ('beginner', 'intermediate', 'advanced')",
            name='check_english_level',
        ),
    )

    # ── Conversations ────────────────────────────────────────────────────────
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('channel', sa.String(10), server_default='text'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('summary', sa.Text, nullable=True),
        sa.CheckConstraint("channel IN ('text', 'voice')", name='check_channel'),
    )

    # ── Messages ─────────────────────────────────────────────────────────────
    op.create_table(
        'messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('conversation_id', sa.String(36), sa.ForeignKey('conversations.id'), nullable=False),
        sa.Column('role', sa.String(10), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('audio_url', sa.Text, nullable=True),
        sa.Column('corrections', sa.JSON, nullable=True),
        sa.Column('vocab_used', sa.JSON, nullable=True),
        sa.Column('mood_signal', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('user', 'assistant')", name='check_role'),
    )

    # ── Memories ─────────────────────────────────────────────────────────────
    op.create_table(
        'memories',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('fact_text', sa.Text, nullable=False),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('importance', sa.SmallInteger, server_default='3'),
        sa.Column('is_active', sa.Boolean, server_default='1'),
        sa.Column('embedding', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_referenced_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('importance BETWEEN 1 AND 5', name='check_importance'),
    )

    # ── Daily Tasks ──────────────────────────────────────────────────────────
    op.create_table(
        'daily_tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('task_date', sa.Date, nullable=False),
        sa.Column('task_type', sa.String(30), nullable=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('difficulty', sa.String(20), server_default='medium'),
        sa.Column('completed', sa.Boolean, server_default='0'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('performance_notes', sa.Text, nullable=True),
    )

    # ── Vocabulary Progress ──────────────────────────────────────────────────
    op.create_table(
        'vocabulary_progress',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('word', sa.String(100), nullable=False),
        sa.Column('times_used', sa.Integer, server_default='1'),
        sa.Column('mastery_level', sa.String(20), server_default='new'),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'word', name='uq_user_word'),
        sa.CheckConstraint(
            "mastery_level IN ('new', 'learning', 'mastered')",
            name='check_mastery_level',
        ),
    )

    # ── Indexes for performance ──────────────────────────────────────────────
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('ix_memories_user_id', 'memories', ['user_id'])
    op.create_index('ix_daily_tasks_user_date', 'daily_tasks', ['user_id', 'task_date'])
    op.create_index('ix_vocabulary_user_id', 'vocabulary_progress', ['user_id'])


def downgrade() -> None:
    op.drop_table('vocabulary_progress')
    op.drop_table('daily_tasks')
    op.drop_table('memories')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('users')
