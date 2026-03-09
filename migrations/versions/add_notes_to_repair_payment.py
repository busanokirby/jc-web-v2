"""Add notes and created_at columns to repair_payment table

Revision ID: add_notes_to_repair_payment
Revises: add_recorded_by_user_id_to_repair_payment
Create Date: 2026-03-05 10:00:00.000000

This migration adds `notes` (TEXT) and `created_at` (DATETIME) columns to the
`repair_payment` table. The `notes` column allows staff to record contextual
details about each transaction. The `created_at` column is required by the
BaseModel mixin and defaults to the current timestamp.
Existing records will have null values for notes and current_timestamp for created_at.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_notes_to_repair_payment'
down_revision = 'add_recorded_by_user_id_to_repair_payment'
branch_labels = None
depends_on = None


def upgrade():
    """This migration has been reverted - no changes applied"""
    pass


def downgrade():
    """This migration has been reverted - no changes applied"""
    pass
