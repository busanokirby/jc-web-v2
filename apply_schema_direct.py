"""
Direct SQLite schema update for revocation fields
"""
import sqlite3
import os

db_path = 'instance/jc_icons_v2.db'

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Get existing columns
    cursor.execute("PRAGMA table_info(sale_item)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Current sale_item columns: {columns}")
    
    # Add revoked_at if it doesn't exist
    if 'revoked_at' not in columns:
        print("Adding revoked_at column...")
        cursor.execute('ALTER TABLE sale_item ADD COLUMN revoked_at DATETIME')
        print("✓ revoked_at added")
    else:
        print("✓ revoked_at already exists")
    
    # Add revoke_reason if it doesn't exist
    if 'revoke_reason' not in columns:
        print("Adding revoke_reason column...")
        cursor.execute('ALTER TABLE sale_item ADD COLUMN revoke_reason TEXT')
        print("✓ revoke_reason added")
    else:
        print("✓ revoke_reason already exists")
    
    # Add revoked_by if it doesn't exist
    if 'revoked_by' not in columns:
        print("Adding revoked_by column...")
        cursor.execute('ALTER TABLE sale_item ADD COLUMN revoked_by VARCHAR(100)')
        print("✓ revoked_by added")
    else:
        print("✓ revoked_by already exists")
    
    conn.commit()
    print("\n✅ Schema migration complete!")
    
    # Verify columns were added
    cursor.execute("PRAGMA table_info(sale_item)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Updated sale_item columns: {columns}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()

finally:
    conn.close()
