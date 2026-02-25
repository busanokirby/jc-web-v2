import pytest
from app.models.user import User
from app.extensions import db


def test_has_role_equivalence():
    tech = User(username='t', full_name='T', role='TECH')
    sales = User(username='s', full_name='S', role='SALES')
    assert tech.has_role('TECH')
    assert tech.has_role('SALES')   # interchangeability
    assert sales.has_role('SALES')
    assert sales.has_role('TECH')   # interchangeability


def test_tech_user_can_access_sales_routes(app):
    # create tech account and verify access to a sales-only page
    with app.app_context():
        # remove any existing user
        User.query.filter_by(username='tech_access').delete()
        u = User(username='tech_access', full_name='Tech Access', role='TECH')
        u.set_password('pw')
        db.session.add(u)
        db.session.commit()
    client = app.test_client()
    # login as tech
    rv = client.post('/auth/login', data={'username': 'tech_access', 'password': 'pw'}, follow_redirects=True)
    assert b'Welcome back' in rv.data
    # hit inventory page (SALES permission required)
    resp = client.get('/inventory/products')
    assert resp.status_code == 200


def test_sales_user_can_access_tech_routes(app):
    # sales account should be allowed to access repair pages
    with app.app_context():
        User.query.filter_by(username='sales_access').delete()
        u = User(username='sales_access', full_name='Sales Access', role='SALES')
        u.set_password('pw2')
        db.session.add(u)
        db.session.commit()
    client = app.test_client()
    rv = client.post('/auth/login', data={'username': 'sales_access', 'password': 'pw2'}, follow_redirects=True)
    assert b'Welcome back' in rv.data
    # choose a repair detail route absent device, use 404 check but should not be 403
    resp2 = client.get('/repairs/1')
    assert resp2.status_code in (200, 404)  # not forbidden
