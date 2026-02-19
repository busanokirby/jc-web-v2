#!/usr/bin/env python
"""
Migration script to add `claimed_on_credit` boolean column to `sale` table.
Existing rows default to false.
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
        columns = [col['name'] for col in inspector.get_columns('sale')]

        added = False
        with db.engine.begin() as conn:
            if 'claimed_on_credit' not in columns:
                print("Adding 'claimed_on_credit' column to sale table...")
                conn.execute(text("ALTER TABLE sale ADD COLUMN claimed_on_credit BOOLEAN DEFAULT 0 NOT NULL"))
                print("  ✓ Added column claimed_on_credit")
                added = True
            else:
                print("'claimed_on_credit' already exists — skipping")

        if not added:
            print('No changes were necessary.')

    return True


if __name__ == '__main__':
    print("Migration: add claimed_on_credit to sale table")
    print("-" * 60)
    ok = migrate()
    if ok:
        print("\nMigration completed successfully!")
        sys.exit(0)
    else:
        print("\nMigration failed!")
        sys.exit(1)
