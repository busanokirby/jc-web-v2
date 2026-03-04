import sqlite3

conn = sqlite3.connect('instance/jc_icons_v2.db')
cursor = conn.cursor()

cursor.execute("UPDATE alembic_version SET version_num = '9a1b2c3d'")
conn.commit()

print("Migration marked as applied")

conn.close()
