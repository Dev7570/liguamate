"""Add missing columns and tables (companion, xp, flashcards, test_results)

Revision ID: 003_missing_cols_tables
Revises: 002_add_target_language
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic
revision = '003_missing_cols_tables'
down_revision = '002_add_target_language'
branch_labels = None
depends_on = None


def _column_exists(table_name, column_name):
    """Check if a column already exists in a table."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def _table_exists(table_name):
    """Check if a table already exists."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # ── Add missing columns to users ──────────────────────────────────────
    if not _column_exists('users', 'companion'):
        op.add_column(
            'users',
            sa.Column('companion', sa.String(20), nullable=False, server_default='mira')
        )

    if not _column_exists('users', 'xp'):
        op.add_column(
            'users',
            sa.Column('xp', sa.Integer, nullable=False, server_default='0')
        )

    # ── Create flashcard_decks table ──────────────────────────────────────
    if not _table_exists('flashcard_decks'):
        op.create_table(
            'flashcard_decks',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('language', sa.String(50), server_default='English'),
            sa.Column('description', sa.Text, nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # ── Create flashcards table ───────────────────────────────────────────
    if not _table_exists('flashcards'):
        op.create_table(
            'flashcards',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('deck_id', sa.String(36), sa.ForeignKey('flashcard_decks.id'), nullable=False),
            sa.Column('front', sa.Text, nullable=False),
            sa.Column('back', sa.Text, nullable=False),
            sa.Column('phonetic', sa.String(100), nullable=True),
            sa.Column('example', sa.Text, nullable=True),
            sa.Column('times_reviewed', sa.Integer, server_default='0'),
            sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('next_review_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('interval', sa.Integer, server_default='1'),
            sa.Column('ease_factor', sa.Float, server_default='2.5'),
            sa.Column('is_mastered', sa.Boolean, server_default='false'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # ── Create test_results table ─────────────────────────────────────────
    if not _table_exists('test_results'):
        op.create_table(
            'test_results',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('test_type', sa.String(20), nullable=False),
            sa.Column('part', sa.String(20), nullable=False),
            sa.Column('band_score', sa.Float, nullable=False),
            sa.Column('fluency', sa.Float, server_default='0.0'),
            sa.Column('lexical', sa.Float, server_default='0.0'),
            sa.Column('grammar', sa.Float, server_default='0.0'),
            sa.Column('pronunciation', sa.Float, server_default='0.0'),
            sa.Column('transcript', sa.Text, nullable=True),
            sa.Column('feedback', sa.Text, nullable=True),
            sa.Column('prompt_used', sa.Text, nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table('test_results')
    op.drop_table('flashcards')
    op.drop_table('flashcard_decks')
    op.drop_column('users', 'xp')
    op.drop_column('users', 'companion')
