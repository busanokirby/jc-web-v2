#!/usr/bin/env python
"""
Migration script to add `company` column to `users` table.
Existing rows default to 'JC Icons'.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, inspect

def migrate():
    # Connect directly to SQLite database without creating app
    db_path = Path(__file__).parent.parent / 'instance' / 'jc_icons_v2.db'
    engine = create_engine(f'sqlite:///{db_path}')

    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('users')]

    if 'company' not in columns:
        print("Adding 'company' column to users table...")
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN company VARCHAR(100) DEFAULT 'JC Icons' NOT NULL"))
        print("  ✓ Added column company (default: 'JC Icons')")
        return True
    else:
        print("'company' already exists — skipping")
        return False


if __name__ == '__main__':
    print("Migration: add company column to user table")
    print("-" * 60)
    ok = migrate()
    if ok:
        print("\nMigration completed successfully!")
    else:
        print("\nNo changes were necessary.")
