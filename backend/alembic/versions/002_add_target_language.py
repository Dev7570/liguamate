"""Add target_language column to users

Revision ID: 002_add_target_language
Revises: 001_initial_schema
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '002_add_target_language'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add target_language column to users table with default 'English'."""
    op.add_column(
        'users',
        sa.Column('target_language', sa.String(50), nullable=False, server_default='English')
    )


def downgrade() -> None:
    """Remove target_language column from users table."""
    op.drop_column('users', 'target_language')
