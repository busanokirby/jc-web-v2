"""add notes column to sale table

Revision ID: 3c4d5e6f7g8h
Revises: None
Create Date: 2026-03-02 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3c4d5e6f7g8h'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add notes column to sale table"""
    op.add_column('sale', sa.Column('notes', sa.Text(), nullable=True))


def downgrade():
    """Remove notes column from sale table"""
    op.drop_column('sale', 'notes')
