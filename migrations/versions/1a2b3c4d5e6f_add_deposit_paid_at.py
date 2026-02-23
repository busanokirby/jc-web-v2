"""add deposit_paid_at to device

Revision ID: 1a2b3c4d5e6f
Revises: None
Create Date: 2026-02-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add deposit_paid_at column to device table"""
    op.add_column('device', sa.Column('deposit_paid_at', sa.DateTime(), nullable=True))


def downgrade():
    """Remove deposit_paid_at column from device table"""
    op.drop_column('device', 'deposit_paid_at')
