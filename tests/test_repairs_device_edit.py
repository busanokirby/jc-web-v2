from decimal import Decimal

from app.models.repair import Device
from app.extensions import db


def test_edit_device_details_allowed(app, logged_in_client):
    client = logged_in_client
    import uuid
    with app.app_context():
        d = Device(ticket_number=f"T-EDIT-1-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='phone', issue_description='initial issue')
        d.brand = 'OldBrand'
        d.model = 'OldModel'
        db.session.add(d)
        db.session.commit()
        device_id = d.id

    # submit updated device details
    resp = client.post(f'/repairs/{device_id}/update-details', data={
        'device_type': 'laptop',
        'brand': 'NewBrand',
        'model': 'NewModel',
        'serial_number': 'SN123',
        'issue_description': 'corrected issue',
        'device_age': '2 years',
        'accessories': 'Charger'
    }, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        d2 = Device.query.get(device_id)
        assert d2.device_type == 'laptop'
        assert d2.brand == 'NewBrand'
        assert d2.model == 'NewModel'
        assert d2.serial_number == 'SN123'
        assert d2.issue_description == 'corrected issue'


def test_edit_device_details_blocked_when_paid_then_revert_allows(app, logged_in_client):
    client = logged_in_client
    import uuid
    with app.app_context():
        d = Device(ticket_number=f"T-EDIT-2-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='printer', issue_description='typo here')
        d.brand = 'BrandX'
        d.model = 'ModelX'
        d.total_cost = Decimal('30.00')
        d.deposit_paid = Decimal('30.00')
        d.payment_status = 'Paid'
        db.session.add(d)
        db.session.commit()
        device_id = d.id

    # attempt to edit while Paid => should be blocked (no change)
    resp = client.post(f'/repairs/{device_id}/update-details', data={
        'device_type': 'printer',
        'brand': 'BrandY',
        'model': 'ModelY',
        'issue_description': 'fixed'
    }, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        d2 = Device.query.get(device_id)
        assert d2.brand == 'BrandX'  # unchanged
        assert d2.model == 'ModelX'

    # revert repair to make it editable
    rv = client.post(f'/repairs/{device_id}/revert', follow_redirects=True)
    assert rv.status_code == 200

    # now update should succeed
    resp2 = client.post(f'/repairs/{device_id}/update-details', data={
        'device_type': 'printer',
        'brand': 'BrandY',
        'model': 'ModelY',
        'issue_description': 'fixed'
    }, follow_redirects=True)
    assert resp2.status_code == 200

    with app.app_context():
        d3 = Device.query.get(device_id)
        assert d3.brand == 'BrandY'
        assert d3.model == 'ModelY'
        assert d3.issue_description == 'fixed'