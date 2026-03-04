import sqlite3

conn = sqlite3.connect('instance/jc_icons.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print('Tables:', sorted(tables))

# Check specifically for department
if 'department' in tables:
    cursor.execute("PRAGMA table_info(department)")
    dept_cols = cursor.fetchall()
    print('Department columns:', [(col[1], col[2]) for col in dept_cols])
else:
    print('Department table does not exist')

conn.close()
