"""Apply deposit_paid_at column to `device` table using SQLAlchemy engine.

Run: python scripts/apply_deposit_paid_at.py
"""
import os
import sys

# Ensure project root is on sys.path so `app` package imports correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config import get_config
from app.extensions import db
import sqlalchemy as sa


def main():
    app = create_app(get_config())
    with app.app_context():
        engine = db.engine
        dialect = engine.dialect.name
        print(f"DB dialect detected: {dialect}")

        if dialect == 'sqlite':
            sql = 'ALTER TABLE device ADD COLUMN deposit_paid_at DATETIME'
        elif dialect in ('postgresql', 'postgres'):
            sql = 'ALTER TABLE device ADD COLUMN deposit_paid_at TIMESTAMP'
        elif dialect in ('mysql', 'mariadb'):
            sql = 'ALTER TABLE device ADD COLUMN deposit_paid_at DATETIME NULL'
        else:
            raise RuntimeError(f"Unsupported dialect: {dialect}")

        conn = engine.connect()
        try:
            print(f"Executing: {sql}")
            conn.execute(sa.text(sql))
            print('Column deposit_paid_at added successfully.')
        except Exception as e:
            print('Error adding column:', e)
        finally:
            conn.close()


if __name__ == '__main__':
    main()
