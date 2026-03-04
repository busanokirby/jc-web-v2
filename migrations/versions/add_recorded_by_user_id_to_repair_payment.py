"""Add recorded_by_user_id column to repair_payment table

Revision ID: add_recorded_by_user_id_to_repair_payment
Revises: 9a1b2c3d
Create Date: 2026-03-04 16:00:00.000000

This migration adds the recorded_by_user_id column to repair_payment table
for audit trail tracking of which user recorded the payment.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_recorded_by_user_id_to_repair_payment'
down_revision = '9a1b2c3d'
branch_labels = None
depends_on = None


def upgrade():
    """Add recorded_by_user_id column to repair_payment table"""
    op.add_column('repair_payment', sa.Column('recorded_by_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_repair_payment_recorded_by_user_id',
        'repair_payment',
        'users',
        ['recorded_by_user_id'],
        ['id']
    )


def downgrade():
    """Remove recorded_by_user_id column from repair_payment table"""
    op.drop_constraint('fk_repair_payment_recorded_by_user_id', 'repair_payment', type_='foreignkey')
    op.drop_column('repair_payment', 'recorded_by_user_id')
