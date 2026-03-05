from app import create_app
from app.extensions import db
import tempfile

with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
    uri = f'sqlite:///{tmp.name}'
    print('using db', uri)
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': uri})
    with app.app_context():
        db.create_all()
        cols = db.session.execute("PRAGMA table_info('repair_payment')").fetchall()
        print('columns:', cols)
