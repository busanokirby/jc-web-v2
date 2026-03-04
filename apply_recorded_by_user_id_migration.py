"""Apply migration to add recorded_by_user_id column"""
import sys
import os
sys.path.insert(0, '/jc-web-v2')

# Set required environment variables
os.environ.setdefault('SECRET_KEY', 'dev-secret-key-for-migration')
os.environ.setdefault('DATABASE_URL', 'sqlite:///instance/jc_icons.db')

from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Check if column already exists
    inspector = db.inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('repair_payment')]
    
    if 'recorded_by_user_id' in columns:
        print("✓ Column 'recorded_by_user_id' already exists in repair_payment table")
    else:
        print("Adding 'recorded_by_user_id' column to repair_payment table...")
        try:
            # Add the column (SQLite doesn't support adding foreign key constraints directly)
            db.session.execute(text("""
                ALTER TABLE repair_payment 
                ADD COLUMN recorded_by_user_id INTEGER
            """))
            
            db.session.commit()
            print("✓ Successfully added 'recorded_by_user_id' column to repair_payment table")
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error: {e}")
            sys.exit(1)
