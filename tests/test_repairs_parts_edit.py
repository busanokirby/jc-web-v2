import json
from decimal import Decimal

from app.models.repair import Device, RepairPartUsed
from app.models.inventory import Product
from app.extensions import db


def add_part(client, device_id, product_id, qty=1, ajax=True):
    url = f'/repairs/{device_id}/parts/add'
    data = {'product_id': str(product_id), 'qty': str(qty)}
    headers = {'X-Requested-With': 'XMLHttpRequest'} if ajax else {}
    return client.post(url, data=data, headers=headers)


def delete_part(client, device_id, part_id):
    url = f'/repairs/{device_id}/parts/{part_id}/delete'
    return client.post(url, headers={'X-Requested-With': 'XMLHttpRequest'})


def update_qty(client, device_id, part_id, qty):
    url = f'/repairs/{device_id}/parts/{part_id}/update-qty'
    return client.post(url, data={'qty': str(qty)}, headers={'X-Requested-With': 'XMLHttpRequest'})


def revert_repair(client, device_id):
    url = f'/repairs/{device_id}/revert'
    return client.post(url, follow_redirects=True)


def test_remove_part_before_paid(app, logged_in_client):
    client = logged_in_client
    with app.app_context():
        # create device and pick existing product
        product = Product.query.filter_by(name='Test Product').first()
        assert product is not None
        initial_stock = product.stock_on_hand
        product_id = product.id

        import uuid
        d = Device(ticket_number=f"T-PART-1-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='phone', issue_description='parts edit test')
        db.session.add(d)
        db.session.commit()
        device_id = d.id

    # add part (AJAX)
    resp = add_part(client, device_id, product_id, qty=1, ajax=True)
    assert resp.status_code in (200, 302)
    if resp.status_code == 200:
        data = json.loads(resp.data)
        assert data['success'] is True
        part_id = int(data['part']['id'])
    else:
        # non-AJAX fallback returns a redirect; find the newly created part from DB
        with app.app_context():
            new_part = RepairPartUsed.query.filter_by(device_id=device_id).order_by(RepairPartUsed.id.desc()).first()
            assert new_part is not None
            part_id = new_part.id

    with app.app_context():
        p2 = Product.query.get(product_id)
        assert p2.stock_on_hand == initial_stock - 1

    # delete the part
    resp2 = delete_part(client, device_id, part_id)
    assert resp2.status_code == 200
    data2 = json.loads(resp2.data)
    assert data2['success'] is True

    with app.app_context():
        p3 = Product.query.get(product_id)
        assert p3.stock_on_hand == initial_stock
        assert RepairPartUsed.query.get(part_id) is None


def test_cannot_remove_part_when_paid_then_revert_allows(app, logged_in_client):
    client = logged_in_client
    with app.app_context():
        product = Product.query.filter_by(name='Test Product').first()
        import uuid
        d = Device(ticket_number=f"T-PART-2-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='laptop', issue_description='paid block test')
        db.session.add(d)
        db.session.commit()
        device_id = d.id
        product_id = product.id

    # add part
    resp = add_part(client, device_id, product_id, qty=1, ajax=True)
    assert resp.status_code in (200, 302)
    if resp.status_code == 200:
        part_id = int(json.loads(resp.data)['part']['id'])
    else:
        with app.app_context():
            new_part = RepairPartUsed.query.filter_by(device_id=device_id).order_by(RepairPartUsed.id.desc()).first()
            assert new_part is not None
            part_id = new_part.id

    with app.app_context():
        # mark repair as paid (simulate processing)
        dev = Device.query.get(device_id)
        # simulate an actual recorded payment (deposit == total) so revert must clear it
        dev.total_cost = Decimal('50.00')
        dev.deposit_paid = Decimal('50.00')
        dev.payment_status = 'Paid'
        db.session.commit()

    # deletion should be blocked
    resp_block = delete_part(client, device_id, part_id)
    assert resp_block.status_code == 400
    data_block = json.loads(resp_block.data)
    assert data_block['success'] is False

    # revert (admin) then deletion should succeed
    rv = revert_repair(client, device_id)
    assert rv.status_code == 200

    resp_ok = delete_part(client, device_id, part_id)
    assert resp_ok.status_code == 200
    data_ok = json.loads(resp_ok.data)
    assert data_ok['success'] is True


def test_edit_qty_blocked_when_paid_then_reverted_allows(app, logged_in_client):
    client = logged_in_client
    with app.app_context():
        product = Product.query.filter_by(name='Test Product').first()
        # ensure stock sufficient for expansion
        product.stock_on_hand = 2
        db.session.commit()
        product_id = product.id

        import uuid
        d = Device(ticket_number=f"T-PART-3-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='printer', issue_description='qty edit test')
        db.session.add(d)
        db.session.commit()
        device_id = d.id

    # add part qty=1
    resp = add_part(client, device_id, product_id, qty=1, ajax=True)
    assert resp.status_code in (200, 302)
    if resp.status_code == 200:
        part_id = int(json.loads(resp.data)['part']['id'])
    else:
        with app.app_context():
            new_part = RepairPartUsed.query.filter_by(device_id=device_id).order_by(RepairPartUsed.id.desc()).first()
            assert new_part is not None
            part_id = new_part.id

    with app.app_context():
        dev = Device.query.get(device_id)
        dev.total_cost = Decimal('20.00')
        dev.deposit_paid = Decimal('20.00')
        dev.payment_status = 'Paid'
        db.session.commit()

    # attempt to change qty (should be blocked)
    resp_block = update_qty(client, device_id, part_id, 2)
    assert resp_block.status_code == 400
    data_block = json.loads(resp_block.data)
    assert data_block['success'] is False

    # revert then update qty should succeed
    rv = revert_repair(client, device_id)
    assert rv.status_code == 200

    resp_ok = update_qty(client, device_id, part_id, 2)
    assert resp_ok.status_code == 200
    data_ok = json.loads(resp_ok.data)
    assert data_ok['success'] is True

    with app.app_context():
        p2 = Product.query.get(product_id)
        # stock_on_hand should have decreased by 1 for the qty increase
        assert p2.stock_on_hand == 0
        part = RepairPartUsed.query.get(part_id)
        assert part.qty == 2


def test_revert_clears_deposit_and_unlocks(app, logged_in_client):
    client = logged_in_client
    with app.app_context():
        # prepare device with an existing payment (fully paid)
        product = Product.query.filter_by(name='Test Product').first()
        # ensure product has stock for later part-add
        product.stock_on_hand = max(product.stock_on_hand or 0, 2)
        db.session.commit()
        import uuid
        d = Device(ticket_number=f"T-REVERT-1-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='phone', issue_description='revert clears deposit')
        d.total_cost = Decimal('40.00')
        d.deposit_paid = Decimal('40.00')
        d.payment_status = 'Paid'
        d.is_archived = True
        db.session.add(d)
        db.session.commit()
        device_id = d.id
        product_id = product.id

    # verify it's currently treated as paid (locked)
    rv = client.get(f'/repairs/{device_id}')
    assert rv.status_code == 200
    assert b'Locked' in rv.data or b'Paid' in rv.data

    # revert as admin
    r = revert_repair(client, device_id)
    assert r.status_code == 200

    # server-side: deposit should be cleared and status become Pending/unlocked
    with app.app_context():
        dev = Device.query.get(device_id)
        assert dev.deposit_paid == Decimal('0.00')
        assert dev.payment_status == 'Pending'
        assert dev.is_archived is False

    # UI should now allow adding parts — try adding a part
    resp = add_part(client, device_id, product_id, qty=1, ajax=True)
    assert resp.status_code in (200, 302)
    if resp.status_code == 200:
        data = json.loads(resp.data)
        assert data['success'] is True
    else:
        with app.app_context():
            new_part = RepairPartUsed.query.filter_by(device_id=device_id).order_by(RepairPartUsed.id.desc()).first()
            assert new_part is not None



def update_price(client, device_id, part_id, price):
    url = f'/repairs/{device_id}/parts/{part_id}/update-price'
    return client.post(url, data={'price': str(price)}, headers={'X-Requested-With': 'XMLHttpRequest'})


def test_edit_price_blocked_when_paid_then_reverted_allows(app, logged_in_client):
    client = logged_in_client
    with app.app_context():
        product = Product.query.filter_by(name='Test Product').first()
        # ensure stock sufficient
        product.stock_on_hand = 2
        db.session.commit()
        product_id = product.id

        import uuid
        d = Device(ticket_number=f"T-PART-4-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='camera', issue_description='price edit test')
        db.session.add(d)
        db.session.commit()
        device_id = d.id

    # add part qty=1
    resp = add_part(client, device_id, product_id, qty=1, ajax=True)
    assert resp.status_code in (200, 302)
    if resp.status_code == 200:
        part_id = int(json.loads(resp.data)['part']['id'])
    else:
        with app.app_context():
            new_part = RepairPartUsed.query.filter_by(device_id=device_id).order_by(RepairPartUsed.id.desc()).first()
            assert new_part is not None
            part_id = new_part.id

    with app.app_context():
        dev = Device.query.get(device_id)
        dev.total_cost = Decimal('10.00')
        dev.deposit_paid = Decimal('10.00')
        dev.payment_status = 'Paid'
        db.session.commit()

    # attempt to change price (should be blocked)
    resp_block = update_price(client, device_id, part_id, '20.00')
    assert resp_block.status_code == 400
    data_block = json.loads(resp_block.data)
    assert data_block['success'] is False

    # revert then update price should succeed
    rv = revert_repair(client, device_id)
    assert rv.status_code == 200

    resp_ok = update_price(client, device_id, part_id, '20.00')
    assert resp_ok.status_code == 200
    data_ok = json.loads(resp_ok.data)
    assert data_ok['success'] is True

    with app.app_context():
        part = RepairPartUsed.query.get(part_id)
        assert part.unit_price == Decimal('20.00')
        dev = Device.query.get(device_id)
        assert dev.parts_cost == Decimal('20.00')


def test_add_part_does_not_double_price(app, logged_in_client):
    """Regression test for reported bug where product price doubled when added to repairs."""
    client = logged_in_client
    with app.app_context():
        product = Product.query.filter_by(name='Test Product').first()
        assert product is not None
        import uuid
        d = Device(ticket_number=f"T-PART-DOUBLE-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='phone', issue_description='price double repro')
        db.session.add(d)
        db.session.commit()
        device_id = d.id
        product_id = product.id

    # add part qty=1
    resp = add_part(client, device_id, product_id, qty=1, ajax=True)
    assert resp.status_code in (200, 302)
    if resp.status_code == 200:
        data = json.loads(resp.data)
        assert data['success'] is True
        part_id = int(data['part']['id'])
    else:
        with app.app_context():
            new_part = RepairPartUsed.query.filter_by(device_id=device_id).order_by(RepairPartUsed.id.desc()).first()
            assert new_part is not None
            part_id = new_part.id

    with app.app_context():
        part = RepairPartUsed.query.get(part_id)
        # unit_price should equal the product's sell_price
        assert part.unit_price == product.sell_price
        # line_total should be unit_price * qty (1)
        assert part.line_total == product.sell_price
        dev = Device.query.get(device_id)
        # parts_cost must equal the single part's line_total (no doubling)
        assert dev.parts_cost == product.sell_price

    # add the same product again (qty=1) and ensure totals update correctly (should be 2x, not 4x)
    resp2 = add_part(client, device_id, product_id, qty=1, ajax=True)
    assert resp2.status_code in (200, 302)

    with app.app_context():
        dev = Device.query.get(device_id)
        # parts_cost should now equal sell_price * 2
        assert dev.parts_cost == product.sell_price * 2
