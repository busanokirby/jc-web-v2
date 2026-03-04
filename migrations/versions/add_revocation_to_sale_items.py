"""Add revocation tracking to sale items

Revision ID: add_revocation_to_sale_items
Revises: 3c4d5e6f7g8h
Create Date: 2026-03-04 15:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_revocation_to_sale_items'
down_revision = '3c4d5e6f7g8h'
branch_labels = None
depends_on = None


def upgrade():
    """Add revocation tracking columns to sale_item table"""
    op.add_column('sale_item', sa.Column('revoked_at', sa.DateTime(), nullable=True))
    op.add_column('sale_item', sa.Column('revoke_reason', sa.Text(), nullable=True))
    op.add_column('sale_item', sa.Column('revoked_by', sa.String(100), nullable=True))


def downgrade():
    """Remove revocation tracking columns from sale_item table"""
    op.drop_column('sale_item', 'revoked_by')
    op.drop_column('sale_item', 'revoke_reason')
    op.drop_column('sale_item', 'revoked_at')
