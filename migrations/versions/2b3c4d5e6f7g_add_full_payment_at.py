"""add full_payment_at to device

Revision ID: 2b3c4d5e6f7g
Revises: 1a2b3c4d5e6f
Create Date: 2026-02-26 15:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2b3c4d5e6f7g'
down_revision = '1a2b3c4d5e6f'
branch_labels = None
depends_on = None


def upgrade():
    """Add full_payment_at column to device table"""
    op.add_column('device', sa.Column('full_payment_at', sa.DateTime(), nullable=True))


def downgrade():
    """Remove full_payment_at column from device table"""
    op.drop_column('device', 'full_payment_at')
