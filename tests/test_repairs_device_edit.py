from decimal import Decimal

from app.models.repair import Device
from app.extensions import db
from app.services.financials import recompute_repair_financials


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


def test_claim_on_credit_shows_in_sales_list(app, logged_in_client):
    """Releasing a device on credit should mark it claimed_on_credit and appear in sales list as unpaid."""
    client = logged_in_client
    import uuid
    with app.app_context():
        d = Device(ticket_number=f"T-CREDIT-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='phone', issue_description='claim on credit')
        d.total_cost = Decimal('150.00')
        d.deposit_paid = Decimal('0.00')
        d.payment_status = 'Pending'
        db.session.add(d)
        db.session.commit()
        device_id = d.id
        ticket = d.ticket_number

    # claim on credit
    resp = client.post(f'/repairs/{device_id}/claim-credit', follow_redirects=True)
    assert resp.status_code == 200
    assert b'released on credit' in resp.data.lower()

    # should appear in sales list
    rv = client.get('/sales/list')
    assert rv.status_code == 200
    assert ticket.encode() in rv.data
    # shows unpaid state
    assert b'On credit' in rv.data


def test_pulled_out_marks_free_and_paid(app, logged_in_client):
    """Setting status to Pulled out should waive charges and mark the repair as Paid (no balance)."""
    client = logged_in_client
    import uuid
    with app.app_context():
        d = Device(ticket_number=f"T-PULLED-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='printer', issue_description='pulled out test')
        d.diagnostic_fee = Decimal('50.00')
        d.repair_cost = Decimal('100.00')
        d.parts_cost = Decimal('20.00')
        recompute_repair_financials(d)
        db.session.add(d)
        db.session.commit()
        device_id = d.id

    # update status to Pulled out
    resp = client.post(f'/repairs/{device_id}/status', data={'status': 'Pulled out'}, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        d2 = Device.query.get(device_id)
        assert d2.charge_waived is True
        assert d2.total_cost == Decimal('0.00')
        assert d2.balance_due == Decimal('0.00')
        assert d2.payment_status == 'Paid'


def test_beyond_repair_behaves_like_pulled_out(app, logged_in_client):
    """Setting status to Beyond repair should be treated the same as Pulled out (waived/paid)."""
    client = logged_in_client
    import uuid
    with app.app_context():
        d = Device(ticket_number=f"T-BEYOND-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='printer', issue_description='beyond repair test')
        d.diagnostic_fee = Decimal('30.00')
        d.repair_cost = Decimal('80.00')
        d.parts_cost = Decimal('10.00')
        recompute_repair_financials(d)
        db.session.add(d)
        db.session.commit()
        device_id = d.id

    # update status to Beyond repair
    resp = client.post(f'/repairs/{device_id}/status', data={'status': 'Beyond repair'}, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        d2 = Device.query.get(device_id)
        assert d2.charge_waived is True
        assert d2.total_cost == Decimal('0.00')
        assert d2.balance_due == Decimal('0.00')
        assert d2.payment_status == 'Paid'