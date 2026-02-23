import uuid
from decimal import Decimal

from app.models.repair import Device
from app.models.inventory import Product
from app.models.sales import Sale, SaleItem
from app.extensions import db


def test_print_ticket_and_receipt_show_client_and_authorized_rep(app, logged_in_client):
    client = logged_in_client
    with app.app_context():
        # Use existing device from fixtures
        dev = Device.query.filter_by(ticket_number='T-100').first()
        assert dev is not None
        device_id = dev.id
        # Ensure owner display_name is available
        assert dev.owner is not None
        display_name = dev.owner.display_name

    # Print ticket
    rv = client.get(f'/repairs/{device_id}/print')
    assert rv.status_code == 200
    body = rv.data.decode('utf-8')
    # Client name should appear and not be blank
    assert display_name in body
    # Authorized Representative must always show "Judith Balaba"
    assert 'Judith Balaba' in body

    # Receipt should include RELEASED BY and the current logged-in user as the releaser
    rv2 = client.get(f'/repairs/{device_id}/receipt')
    assert rv2.status_code == 200
    body2 = rv2.data.decode('utf-8')
    assert 'RELEASED BY' in body2
    # current test login uses the default admin user
    from app.models.user import User
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        assert admin is not None
        assert admin.full_name in body2


def test_invoice_includes_released_by_and_authorized_rep(app, logged_in_client):
    client = logged_in_client
    with app.app_context():
        product = Product.query.filter_by(name='Test Product').first()
        assert product is not None

        # Create a sale to render invoice
        sale = Sale(invoice_no=f"TEST-INV-{uuid.uuid4().hex[:6]}", customer_id=1)
        si = SaleItem(sale=sale, product_id=product.id, qty=1, unit_price=product.sell_price, line_total=product.sell_price)
        sale.subtotal = product.sell_price
        sale.total = product.sell_price
        db.session.add(sale)
        db.session.commit()
        sale_id = sale.id

    rv = client.get(f'/sales/{sale_id}/invoice')
    assert rv.status_code == 200
    body = rv.data.decode('utf-8')
    assert 'RELEASED BY' in body
    from app.models.user import User
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        assert admin is not None
        assert admin.full_name in body


def test_can_override_technician_name_from_print(app, logged_in_client):
    """Ensure the print ticket UI can set/clear a technician override and the print reflects it."""
    client = logged_in_client
    with app.app_context():
        dev = Device.query.filter_by(ticket_number='T-100').first()
        assert dev is not None
        device_id = dev.id

        # ensure no override initially
        dev.technician_name_override = None
        db.session.commit()

    # default printed name should be created_by_user.full_name OR fallback
    rv = client.get(f'/repairs/{device_id}/print')
    assert rv.status_code == 200
    body = rv.data.decode('utf-8')
    # new attributes should be present for fallback and update endpoint
    assert 'data-fallback-name' in body
    # body tag should include update-url so script can read it
    assert 'data-update-url' in body
    assert 'data-redirect-url' in body

    # Now set an override via the new endpoint
    resp = client.post(f'/repairs/{device_id}/technician-name', data={'technician_name': 'Ana Tech'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['technician_name'] == 'Ana Tech'

    # print view should now show the overridden name
    rv2 = client.get(f'/repairs/{device_id}/print')
    assert rv2.status_code == 200
    body2 = rv2.data.decode('utf-8')
    assert 'Ana Tech' in body2
    # fallback data attribute should still exist
    assert 'data-fallback-name' in body2

    # Clearing the override should revert to fallback
    resp2 = client.post(f'/repairs/{device_id}/technician-name', data={'technician_name': ''})
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert data2['success'] is True

    rv3 = client.get(f'/repairs/{device_id}/print')
    assert rv3.status_code == 200
    body3 = rv3.data.decode('utf-8')
    # fallback must appear (either created_by_user.full_name or 'Judith Balaba')
    assert 'Judith Balaba' in body3 or dev.created_by_user.full_name in body3
    # data attribute persisted after clearing override
    assert 'data-fallback-name' in body3