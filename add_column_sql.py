#!/usr/bin/env python
"""Add full_payment_at column directly to device table"""
import os
import sqlite3

os.environ['SECRET_KEY'] = 'dev-secret'

from app import create_app, db

app = create_app()

with app.app_context():
    # Get database URI and extract connection
    db_file = 'instance/jc_icons_v2.db'
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    try:
        # Try to add the column
        cursor.execute('ALTER TABLE device ADD COLUMN full_payment_at DATETIME')
        conn.commit()
        print("Column 'full_payment_at' added successfully")
    except sqlite3.OperationalError as e:
        if 'already exists' in str(e) or 'duplicate' in str(e):
            print(f"Column already exists: {e}")
        else:
            print(f"Error: {e}")
    finally:
        conn.close()
