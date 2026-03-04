"""Add Department model and department references to Device and Sale

Revision ID: 9a1b2c3d
Revises: 3c4d5e6f7g8h
Create Date: 2026-03-04 10:00:00.000000

This migration:
1. Creates the department table
2. Adds department_id foreign key to device table
3. Adds department_id foreign key to sale table
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '9a1b2c3d'
down_revision = '3c4d5e6f7g8h'
branch_labels = None
depends_on = None


def upgrade():
    """Create department table and add foreign keys to device and sale"""
    # Create department table
    op.create_table(
        'department',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('contact_person', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['customer_id'], ['customer.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on customer_id for faster queries
    op.create_index(op.f('ix_department_customer_id'), 'department', ['customer_id'], unique=False)
    
    # Add department_id column to device table
    op.add_column('device', sa.Column('department_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_device_department_id',
        'device',
        'department',
        ['department_id'],
        ['id']
    )
    
    # Add department_id column to sale table
    op.add_column('sale', sa.Column('department_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_sale_department_id',
        'sale',
        'department',
        ['department_id'],
        ['id']
    )


def downgrade():
    """Drop department table and remove foreign keys"""
    # Remove foreign key from sale
    op.drop_constraint('fk_sale_department_id', 'sale', type_='foreignkey')
    op.drop_column('sale', 'department_id')
    
    # Remove foreign key from device
    op.drop_constraint('fk_device_department_id', 'device', type_='foreignkey')
    op.drop_column('device', 'department_id')
    
    # Drop department table
    op.drop_index(op.f('ix_department_customer_id'), table_name='department')
    op.drop_table('department')
