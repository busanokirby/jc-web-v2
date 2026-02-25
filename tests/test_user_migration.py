import pytest
from sqlalchemy import create_engine, text

from app import initialize_database
from app.extensions import db
from app.models.user import User


def test_initialize_adds_company_column(tmp_path, tmp_path_factory, monkeypatch):
    """If the `users` table lacks the `company` column, initialize_database should
    add it automatically and not raise an OperationalError when counting users.
    """
    # build a fresh SQLite file without company column
    db_file = tmp_path / "migrate.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")

    # manually create a minimal users table omitting the `company` column
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

    # configure the app fixture to use our custom database URI
    class DummyApp:
        config = {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file.as_posix()}"}

    # monkeypatch the global current_app so that initialize_database can
    # access the engine through db.engine.  In practice create_app sets this up
    # via app.app_context(); here we push a dummy context instead.
    from flask import Flask

    app = Flask(__name__)
    app.config.update(DummyApp.config)

    with app.app_context():
        # bind our db to this app
        db.init_app(app)
        # call create_all to register the Model metadata; it won't modify the
        # existing table schema, which is what we want for the test
        db.create_all()
        # now exercise the migration logic
        initialize_database()

        cols = [row[1] for row in db.engine.execute(text("PRAGMA table_info('users')")).fetchall()]
        assert 'company' in cols, "company column should have been added"

        # and we should be able to query without error
        assert User.query.count() == 0

    def test_device_migration_adds_deposit_timestamp(self, tmp_path, tmp_path_factory):
        """initialize_database should add deposit_paid_at column if missing."""
        db_file = tmp_path / "device.db"
        engine = create_engine(f"sqlite:///{db_file.as_posix()}")

        # create minimal device table without deposit_paid_at
        with engine.begin() as conn:
            conn.execute(text(
                """
                CREATE TABLE device (
                    id INTEGER PRIMARY KEY,
                    ticket_number VARCHAR(20) NOT NULL UNIQUE,
                    customer_id INTEGER NOT NULL,
                    issue_description TEXT NOT NULL,
                    status VARCHAR(50),
                    received_date DATE,
                    is_archived BOOLEAN DEFAULT 0 NOT NULL
                )
                """
            ))

        # set up app with this database
        from flask import Flask
        app = Flask(__name__)
        app.config.update({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file.as_posix()}"})
        with app.app_context():
            db.init_app(app)
            db.create_all()
            # call initializer which should add the column
            initialize_database()
            cols = [row[1] for row in db.engine.execute(text("PRAGMA table_info('device')")).fetchall()]
            assert 'deposit_paid_at' in cols
            # running a simple query should now succeed
            from app.models.repair import Device
            assert Device.query.count() == 0
