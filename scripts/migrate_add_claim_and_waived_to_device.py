#!/usr/bin/env python
"""
Migration script to add `claimed_on_credit` and `charge_waived` boolean columns to `device` table.
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
        columns = [col['name'] for col in inspector.get_columns('device')]

        added = False
        with db.engine.begin() as conn:
            if 'claimed_on_credit' not in columns:
                print("Adding 'claimed_on_credit' column to device table...")
                conn.execute(text("ALTER TABLE device ADD COLUMN claimed_on_credit BOOLEAN DEFAULT 0 NOT NULL"))
                print("  ✓ Added column claimed_on_credit")
                added = True
            else:
                print("'claimed_on_credit' already exists — skipping")

            if 'charge_waived' not in columns:
                print("Adding 'charge_waived' column to device table...")
                conn.execute(text("ALTER TABLE device ADD COLUMN charge_waived BOOLEAN DEFAULT 0 NOT NULL"))
                print("  ✓ Added column charge_waived")
                added = True
            else:
                print("'charge_waived' already exists — skipping")

        if not added:
            print('No changes were necessary.')

    return True


if __name__ == '__main__':
    print("Migration: add claimed_on_credit and charge_waived to device table")
    print("-" * 60)
    ok = migrate()
    if ok:
        print("\nMigration completed successfully!")
        sys.exit(0)
    else:
        print("\nMigration failed!")
        sys.exit(1)
