import sqlite3

conn = sqlite3.connect('instance/jc_icons_v2.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print('Tables in jc_icons_v2.db:', sorted(tables))

# Check device table
cursor.execute("PRAGMA table_info(device)")
device_cols = [row[1] for row in cursor.fetchall()]
print('device has department_id:', 'department_id' in device_cols)

# Check sale table
cursor.execute("PRAGMA table_info(sale)")
sale_cols = [row[1] for row in cursor.fetchall()]
print('sale has department_id:', 'department_id' in sale_cols)

# Check department table
if 'department' in tables:
    print('department table exists')
else:
    print('department table does NOT exist')

conn.close()
