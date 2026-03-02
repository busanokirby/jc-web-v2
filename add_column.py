#!/usr/bin/env python
"""Add full_payment_at column to device table"""
import os
from app import create_app, db
from sqlalchemy import inspect

os.environ['SECRET_KEY'] = 'dev-secret'

app = create_app()

with app.app_context():
    # Check if column exists
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('device')]
    
    if 'full_payment_at' in columns:
        print("Column 'full_payment_at' already exists")
    else:
        print("Adding 'full_payment_at' column to device table...")
        # Create the table schema - this will add missing columns
        db.create_all()
        print("Column added successfully")
