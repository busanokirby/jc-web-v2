import sqlite3

conn = sqlite3.connect('instance/jc_icons.db')
cursor = conn.cursor()

# Check device table
cursor.execute("PRAGMA table_info(device)")
device_cols = [row[1] for row in cursor.fetchall()]
print('device has department_id:', 'department_id' in device_cols)

# Check sale table
cursor.execute("PRAGMA table_info(sale)")
sale_cols = [row[1] for row in cursor.fetchall()]
print('sale has department_id:', 'department_id' in sale_cols)

# Check department table
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='department'")
print('department table exists:', cursor.fetchone() is not None)

conn.close()
