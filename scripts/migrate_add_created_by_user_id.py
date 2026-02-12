#!/usr/bin/env python
"""
Migration script to add created_by_user_id column to customer table
This preserves existing data and adds the new column for tracking customer creator
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.extensions import db
from sqlalchemy import text


def migrate():
    """Add created_by_user_id column to customer table"""
    app = create_app()
    
    with app.app_context():
        # Check if column already exists
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('customer')]
        
        if 'created_by_user_id' in columns:
            print("✓ Column 'created_by_user_id' already exists in customer table")
            return
        
        # Add the column
        print("Adding 'created_by_user_id' column to customer table...")
        try:
            with db.engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE customer ADD COLUMN created_by_user_id INTEGER"
                ))
                # Add foreign key constraint
                conn.execute(text(
                    "CREATE TABLE IF NOT EXISTS customer_new AS SELECT * FROM customer"
                ))
            print("✓ Column 'created_by_user_id' added to customer table")
            print("✓ All existing customers will have NULL for created_by_user_id (created by admin/import)")
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    return True


if __name__ == "__main__":
    print("Migration: Add created_by_user_id to customer table")
    print("-" * 50)
    
    if migrate():
        print("\nMigration completed successfully!")
        sys.exit(0)
    else:
        print("\nMigration failed!")
        sys.exit(1)
