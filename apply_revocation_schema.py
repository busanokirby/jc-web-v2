"""
Manual schema migration script for revocation fields.
Run this if the alembic migration didn't apply correctly.
"""
import os
import sys

# Set environment for config
os.environ.setdefault('FLASK_ENV', 'development')

from app import create_app, db
from sqlalchemy import inspect, text

def apply_revocation_schema():
    """Manually add revocation columns to sale_item table if they don't exist"""
    try:
        app = create_app()
    except ValueError as e:
        print(f"Config error (expected): {e}")
        # Try with minimal config
        from flask import Flask
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/jc_icons.db'
        from app.extensions import db as ext_db
        ext_db.init_app(app)
        db_instance = ext_db
    else:
        db_instance = db
    
    with app.app_context():
        try:
            # Get database inspector
            inspector = inspect(db_instance.engine)
            
            # Check if columns already exist
            columns = [col['name'] for col in inspector.get_columns('sale_item')]
            print(f"Current sale_item columns: {columns}")
            
            # Add revocation columns if they don't exist
            with db_instance.engine.connect() as conn:
                if 'revoked_at' not in columns:
                    print("Adding revoked_at column...")
                    conn.execute(text('ALTER TABLE sale_item ADD COLUMN revoked_at DATETIME'))
                    print("✓ revoked_at added")
                else:
                    print("✓ revoked_at already exists")
                
                if 'revoke_reason' not in columns:
                    print("Adding revoke_reason column...")
                    conn.execute(text('ALTER TABLE sale_item ADD COLUMN revoke_reason TEXT'))
                    print("✓ revoke_reason added")
                else:
                    print("✓ revoke_reason already exists")
                
                if 'revoked_by' not in columns:
                    print("Adding revoked_by column...")
                    conn.execute(text('ALTER TABLE sale_item ADD COLUMN revoked_by VARCHAR(100)'))
                    print("✓ revoked_by added")
                else:
                    print("✓ revoked_by already exists")
                
                conn.commit()
            
            print("\n✅ Schema migration complete!")
            
            # Verify columns were added
            inspector = inspect(db_instance.engine)
            columns = [col['name'] for col in inspector.get_columns('sale_item')]
            print(f"Updated sale_item columns: {columns}")
            
        except Exception as e:
            print(f"Error applying schema: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    apply_revocation_schema()
