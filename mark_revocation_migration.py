"""
Mark the revocation migration as applied in alembic_version table
"""
import sqlite3

db_path = 'instance/jc_icons_v2.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check current version
    cursor.execute("SELECT version_num FROM alembic_version")
    current = cursor.fetchone()
    print(f"Current alembic version: {current[0] if current else 'None'}")
    
    # Update to the new migration version
    cursor.execute("UPDATE alembic_version SET version_num = 'add_revocation_to_sale_items'")
    conn.commit()
    
    # Verify
    cursor.execute("SELECT version_num FROM alembic_version")
    updated = cursor.fetchone()
    print(f"Updated alembic version: {updated[0]}")
    print("✅ Migration marked as applied in alembic_version")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()

finally:
    conn.close()
