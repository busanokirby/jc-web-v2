from pathlib import Path
from sqlalchemy import create_engine, text
from app import create_app, initialize_database
from app.extensions import db
import shutil

base = Path('C:/Users/JCi/AppData/Local/Temp/testdb')
shutil.rmtree(base, ignore_errors=True)
base.mkdir(parents=True)
db_file = base / 'migrate.db'
engine = create_engine(f"sqlite:///{db_file.as_posix()}")
with engine.begin() as conn:
    conn.execute(text(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            role VARCHAR(20) NOT NULL,
            is_active BOOLEAN DEFAULT 1 NOT NULL,
            created_at DATETIME,
            updated_at DATETIME
        )
        """
    ))

app = create_app({'SQLALCHEMY_DATABASE_URI': f"sqlite:///{db_file.as_posix()}",
                  'WTF_CSRF_ENABLED': False,
                  'SECRET_KEY': 'foo'})

with app.app_context():
    db.init_app(app)
    db.create_all()
    cols_before = [r[1] for r in db.engine.execute(text("PRAGMA table_info('users')")).fetchall()]
    print('before init cols', cols_before)
    initialize_database()
    cols_after = [r[1] for r in db.engine.execute(text("PRAGMA table_info('users')")).fetchall()]
    print('after init cols', cols_after)
