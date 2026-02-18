import os
import tempfile
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.customer import Customer
from app.models.repair import Device


@pytest.fixture(scope='session')
def temp_db(tmp_path_factory):
    d = tmp_path_factory.mktemp('data')
    db_file = d / 'test_jc_icons.db'
    return f'sqlite:///{db_file.as_posix()}'


@pytest.fixture()
def app(temp_db):
    config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': temp_db,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret'
    }
    # Ensure SECRET_KEY is present (Config requires it)
    import os
    os.environ['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'test-secret')

    app = create_app(config=config)
    # apply mapping config (create_app expects a config object/string; support dict in tests)
    app.config.update(config)

    # Create tables and a test dataset
    with app.app_context():
        db.create_all()
        # Use default admin created by initialize_database() in the app factory
        # Create a customer and a device for tests (avoid duplicates if already present)
        c = Customer.query.filter_by(customer_code='TC-001').first()
        if not c:
            c = Customer(customer_code='TC-001', name='Test Customer', phone='555-0001')
            db.session.add(c)
            db.session.flush()
        d = Device.query.filter_by(ticket_number='T-100').first()
        if not d:
            d = Device(ticket_number='T-100', customer_id=c.id, device_type='laptop', brand='ACME', model='Pro', issue_description='Test issue')
            d.total_cost = 100.00
            db.session.add(d)

        # Create a sample product with low stock and reorder settings for inventory tests
        from app.models.inventory import Product
        p = Product.query.filter_by(name='Test Product').first()
        if not p:
            p = Product(name='Test Product', sku='TP-001', cost_price=10.00, sell_price=15.00, stock_on_hand=2, reorder_threshold=5, reorder_to=20)
            db.session.add(p)

        db.session.commit()

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def logged_in_client(client):
    # Log in as admin
    rv = client.post('/auth/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    assert b'Welcome back' in rv.data
    return client