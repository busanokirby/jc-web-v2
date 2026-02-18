#!/usr/bin/env python
"""
Migration script to add `is_archived` boolean column to `device` table and
mark existing Completed repairs as archived.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.extensions import db
from sqlalchemy import text


def migrate():
    app = create_app()

    with app.app_context():
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('device')]

        if 'is_archived' in columns:
            print("✓ 'is_archived' column already exists on device table")
            return True

        print("Adding 'is_archived' column to device table...")
        try:
            with db.engine.begin() as conn:
                # Add boolean column with default FALSE and NOT NULL for safety
                conn.execute(text("ALTER TABLE device ADD COLUMN is_archived BOOLEAN DEFAULT 0 NOT NULL"))
                print("  ✓ Added column is_archived")

                # Mark existing Completed repairs as archived so they "move" to archive on upgrade
                updated = conn.execute(text("UPDATE device SET is_archived = 1 WHERE status = 'Completed'"))
                print(f"  ✓ Marked existing Completed repairs as archived ({updated.rowcount} rows affected)")
        except Exception as e:
            print(f"Error while adding is_archived column: {e}")
            return False

    return True


if __name__ == '__main__':
    print("Migration: add is_archived to device table and archive existing Completed repairs")
    print("-" * 60)
    ok = migrate()
    if ok:
        print("\nMigration completed successfully!")
        sys.exit(0)
    else:
        print("\nMigration failed!")
        sys.exit(1)
