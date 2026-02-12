#!/usr/bin/env python
"""
Migration script to add created_by_user_id and technician_name_override columns to device table
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.extensions import db
from sqlalchemy import text


def migrate():
    """Add created_by_user_id and technician_name_override columns to device table"""
    app = create_app()
    
    with app.app_context():
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('device')]
        
        columns_to_add = []
        if 'created_by_user_id' not in columns:
            columns_to_add.append('created_by_user_id')
        if 'technician_name_override' not in columns:
            columns_to_add.append('technician_name_override')
        
        if not columns_to_add:
            print("✓ All columns already exist in device table")
            return True
        
        print(f"Adding columns to device table: {', '.join(columns_to_add)}")
        try:
            with db.engine.begin() as conn:
                for col in columns_to_add:
                    if col == 'created_by_user_id':
                        conn.execute(text(
                            "ALTER TABLE device ADD COLUMN created_by_user_id INTEGER"
                        ))
                        print(f"  ✓ Added {col}")
                    elif col == 'technician_name_override':
                        conn.execute(text(
                            "ALTER TABLE device ADD COLUMN technician_name_override VARCHAR(100)"
                        ))
                        print(f"  ✓ Added {col}")
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    return True


if __name__ == "__main__":
    print("Migration: Add technician tracking columns to device table")
    print("-" * 60)
    
    if migrate():
        print("\nMigration completed successfully!")
        sys.exit(0)
    else:
        print("\nMigration failed!")
        sys.exit(1)
