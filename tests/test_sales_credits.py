from decimal import Decimal

from app.models.repair import Device
from app.extensions import db


def test_credits_page_lists_claimed_devices(app, logged_in_client):
    client = logged_in_client
    import uuid
    with app.app_context():
        # create a device and mark as claimed_on_credit
        d = Device(ticket_number=f"T-CREDIT-LOT-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='phone', issue_description='credit test')
        d.total_cost = Decimal('200.00')
        d.balance_due = Decimal('200.00')
        d.payment_status = 'Pending'
        d.claimed_on_credit = True
        db.session.add(d)
        db.session.commit()
        ticket = d.ticket_number

    rv = client.get('/sales/credits')
    assert rv.status_code == 200
    assert ticket.encode() in rv.data
    # should show 'On credit' badge
    assert b'On credit' in rv.data


def test_sales_list_shows_credits_summary(app, logged_in_client):
    client = logged_in_client
    import uuid
    with app.app_context():
        d = Device(ticket_number=f"T-CREDIT-COUNT-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='printer', issue_description='credit count')
        d.total_cost = Decimal('75.00')
        d.balance_due = Decimal('75.00')
        d.payment_status = 'Pending'
        d.claimed_on_credit = True
        db.session.add(d)
        db.session.commit()
        device_id = d.id

    rv = client.get('/sales/list')
    assert rv.status_code == 200
    # The Credits button should show the badge with a non-zero count
    assert b'Credits' in rv.data
    assert b'bg-warning' in rv.data  # badge styling present
    # The quick process-payment button should be present for the credited repair row
    assert f"/repairs/{device_id}/payment".encode() in rv.data


def test_process_credit_from_credits_list(app, logged_in_client):
    client = logged_in_client
    import uuid
    with app.app_context():
        d = Device(ticket_number=f"T-CREDIT-PROCESS-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='phone', issue_description='process credit')
        d.total_cost = Decimal('120.00')
        d.balance_due = Decimal('120.00')
        d.payment_status = 'Pending'
        d.claimed_on_credit = True
        db.session.add(d)
        db.session.commit()
        device_id = d.id

    # Process payment via the quick-action in credits list (simulate form POST)
    rv = client.post(f'/repairs/{device_id}/payment', data={'amount': '120.00', 'payment_method': 'Cash', 'apply_as_deposit': 'no'}, follow_redirects=True)
    assert rv.status_code == 200

    with app.app_context():
        d2 = Device.query.get(device_id)
        assert d2.payment_status == 'Paid'
        assert d2.claimed_on_credit is False

    # It should no longer appear in credits list
    rv2 = client.get('/sales/credits')
    assert rv2.status_code == 200
    assert d2.ticket_number.encode() not in rv2.data


def test_pos_allows_claim_on_credit(app, logged_in_client):
    client = logged_in_client
    import json
    from app.models.inventory import Product
    from app.models.sales import Sale

    with app.app_context():
        p = Product.query.filter_by(name='Test Product').first()
        assert p is not None
        items = [{'product_id': p.id, 'qty': 1, 'price': str(p.sell_price)}]

    rv = client.post('/sales/pos', data={
        'items': json.dumps(items),
        'customer_id': '',
        'discount': '0',
        'payment_method': 'Cash',
        'claim_on_credit': 'yes'
    }, follow_redirects=True)

    assert rv.status_code == 200

    with app.app_context():
        s = Sale.query.filter_by(claimed_on_credit=True).order_by(Sale.created_at.desc()).first()
        assert s is not None
        assert s.status == 'PARTIAL'
        # balance should equal total (no immediate payment recorded)
        payments_total = sum((p.amount or 0) for p in (s.payments or []))
        assert float(s.total or 0) - payments_total == float(s.total or 0)

    # It should appear in credits list
    rv2 = client.get('/sales/credits')
    assert rv2.status_code == 200
    assert s.invoice_no.encode() in rv2.data


def test_process_credit_from_credits_list_for_sale(app, logged_in_client):
    client = logged_in_client
    import uuid
    from app.models.sales import Sale, SaleItem, SalePayment
    from app.models.inventory import Product

    with app.app_context():
        p = Product.query.filter_by(name='Test Product').first()
        s = Sale(invoice_no=f"T-SALE-CREDIT-{uuid.uuid4().hex[:6]}", customer_id=1, status='PARTIAL', subtotal=Decimal('15.00'), discount=Decimal('0.00'), tax=Decimal('0.00'), total=Decimal('15.00'), claimed_on_credit=True)
        db.session.add(s)
        db.session.flush()
        si = SaleItem(sale_id=s.id, product_id=p.id, qty=1, unit_price=Decimal('15.00'), line_total=Decimal('15.00'))
        db.session.add(si)
        db.session.commit()
        sale_id = s.id

    # Process payment via the quick-action in credits list (simulate form POST)
    rv = client.post(f'/sales/{sale_id}/payment', data={'amount': '15.00', 'payment_method': 'Cash'}, follow_redirects=True)
    assert rv.status_code == 200

    with app.app_context():
        s2 = Sale.query.get(sale_id)
        assert s2.status == 'PAID'
        assert s2.claimed_on_credit is False
        payments = s2.payments
        assert len(payments) == 1
        assert float(payments[0].amount or 0) == 15.0


def test_pos_rejects_deposit_and_claim_together(app, logged_in_client):
    client = logged_in_client
    import json
    from app.models.inventory import Product
    from app.models.sales import Sale

    with app.app_context():
        p = Product.query.filter_by(name='Test Product').first()
        assert p is not None
        items = [{'product_id': p.id, 'qty': 1, 'price': str(p.sell_price)}]

    # Attempt to submit POS with both Deposit and Claim checked
    rv = client.post('/sales/pos', data={
        'items': json.dumps(items),
        'customer_id': '',
        'discount': '0',
        'payment_method': 'Cash',
        'apply_as_deposit': 'yes',
        'claim_on_credit': 'yes'
    }, follow_redirects=True)

    assert rv.status_code == 200
    assert b'Cannot record a deposit and claim on credit at the same time' in rv.data

    # Ensure no sale was created with claimed_on_credit
    with app.app_context():
        s = Sale.query.filter_by(claimed_on_credit=True).first()
        # there should be none created by this attempt (existing fixtures unaffected)
        assert s is None or s.total != float(p.sell_price)
