from app.models.user import User
from app.models.settings import Setting
from app.models.customer import Customer


def make_tech_user(app, username='tech1', password='techpass'):
    with app.app_context():
        u = User.query.filter_by(username=username).first()
        if not u:
            u = User(username=username, full_name=f'Tech User {username}', role='TECH')
            u.set_password(password)
            from app.extensions import db
            db.session.add(u)
            db.session.commit()
    return u


def login(client, username, password):
    return client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)


def test_tech_cannot_view_customers_when_flag_off(app, client):
    """TECH blocked from customers list when feature flag is OFF"""
    make_tech_user(app)
    with app.app_context():
        Setting.set_value('TECH_CAN_VIEW_DETAILS', 'false')

    rv = login(client, 'tech1', 'techpass')
    assert rv.status_code == 200

    res = client.get('/customers')
    assert res.status_code == 403
    assert b'Access Denied' in res.data


def test_tech_can_view_customers_list_when_flag_on(app, client):
    """TECH can see customers list when feature flag is ON"""
    make_tech_user(app)
    with app.app_context():
        Setting.set_value('TECH_CAN_VIEW_DETAILS', 'true')

    rv = login(client, 'tech1', 'techpass')
    assert rv.status_code == 200

    res = client.get('/customers')
    assert res.status_code == 200
    assert b'Customers' in res.data


def test_tech_only_sees_own_customers(app, client):
    """TECH user only sees customers they created"""
    tech1 = make_tech_user(app, 'tech1')
    tech2 = make_tech_user(app, 'tech2')
    
    with app.app_context():
        Setting.set_value('TECH_CAN_VIEW_DETAILS', 'true')
        from app.extensions import db
        
        # Create customers created by tech1 and tech2
        c1 = Customer(customer_code='TC-001', name='Tech1 Customer', phone='555-0001', created_by_user_id=tech1.id)
        c2 = Customer(customer_code='TC-002', name='Tech2 Customer', phone='555-0002', created_by_user_id=tech2.id)
        db.session.add_all([c1, c2])
        db.session.commit()

    # Tech1 logs in
    login(client, 'tech1', 'techpass')
    res = client.get('/customers')
    assert res.status_code == 200
    assert b'Tech1 Customer' in res.data
    assert b'Tech2 Customer' not in res.data


def test_tech_cannot_view_other_tech_customer_detail(app, client):
    """TECH cannot view detail of customer created by another TECH"""
    tech1 = make_tech_user(app, 'tech1')
    tech2 = make_tech_user(app, 'tech2')
    
    with app.app_context():
        from app.extensions import db
        Setting.set_value('TECH_CAN_VIEW_DETAILS', 'true')
        
        # Create customer by tech2
        c = Customer(customer_code='TC-001', name='Tech2 Customer', phone='555-0001', created_by_user_id=tech2.id)
        db.session.add(c)
        db.session.commit()
        customer_id = c.id

    # Tech1 logs in and tries to access tech2's customer
    login(client, 'tech1', 'techpass')
    res = client.get(f'/customers/{customer_id}')
    assert res.status_code == 403
    assert b'Access Denied' in res.data


def test_admin_sees_all_customers(app, client):
    """ADMIN user can see all customers"""
    make_tech_user(app)
    
    with app.app_context():
        Setting.set_value('TECH_CAN_VIEW_DETAILS', 'true')
        from app.extensions import db
        
        # Create customers by tech1 and admin
        tech = User.query.filter_by(username='tech1').first()
        admin = User.query.filter_by(role='ADMIN').first()
        
        c1 = Customer(customer_code='TC-001', name='Tech Customer', phone='555-0001', created_by_user_id=tech.id)
        c2 = Customer(customer_code='TC-002', name='Admin Customer', phone='555-0002', created_by_user_id=admin.id)
        db.session.add_all([c1, c2])
        db.session.commit()

    # Admin logs in
    login(client, 'admin', 'admin123')
    res = client.get('/customers')
    assert res.status_code == 200
    assert b'Tech Customer' in res.data
    assert b'Admin Customer' in res.data
