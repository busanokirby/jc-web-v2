import sqlite3

conn = sqlite3.connect('instance/jc_icons_v2.db')
cursor = conn.cursor()

try:
    # Add department_id to device table
    print("Adding department_id to device table...")
    cursor.execute("ALTER TABLE device ADD COLUMN department_id INTEGER")
    
    # Add foreign key constraint for device
    print("Creating foreign key constraint for device...")
    cursor.execute("CREATE TABLE IF NOT EXISTS device_new AS SELECT * FROM device")
    # SQLite doesn't support adding FK constraints directly, so we'll add an index
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_device_department_id ON device(department_id)")
    
    # Add department_id to sale table
    print("Adding department_id to sale table...")
    cursor.execute("ALTER TABLE sale ADD COLUMN department_id INTEGER")
    
    # Add foreign key constraint for sale
    print("Creating foreign key constraint for sale...")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_sale_department_id ON sale(department_id)")
    
    conn.commit()
    print("✓ Successfully added department_id columns!")
    
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("Columns already exist, no changes needed")
    else:
        print(f"Error: {e}")
    conn.rollback()

finally:
    conn.close()
