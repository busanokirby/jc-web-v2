from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid
from app.extensions import db
from app.models.sales import Sale, SaleItem, SalePayment
from app.models.inventory import Product
from app.models.repair import Device, RepairPartUsed
from app.models.customer import Customer


def test_sales_search_text_filters_dates_and_status(app, logged_in_client):
    client = logged_in_client
    with app.app_context():
        # Ensure a product exists
        p = Product.query.filter_by(name='Test Product').first()
        if not p:
            p = Product(name='Test Product', sku=f"TP-{uuid.uuid4().hex[:6]}", stock_on_hand=5, is_active=True)
            db.session.add(p)
            db.session.commit()

        # Create a sale with a unique invoice and product
        inv = f"SEARCH-INV-{uuid.uuid4().hex[:6]}"
        cust = Customer.query.first()
        # ensure there is at least one customer in fixtures
        if not cust:
            from app.models.customer import Customer as _C
            cust = _C(name='Search Cust', phone='555-1234', customer_code=f"C-{uuid.uuid4().hex[:6]}")
            db.session.add(cust)
            db.session.flush()

        sale = Sale(invoice_no=inv, customer_id=cust.id, subtotal=Decimal('20.00'), discount=Decimal('0.00'), tax=Decimal('0.00'), total=Decimal('20.00'), status='PAID')
        db.session.add(sale)
        db.session.flush()
        si = SaleItem(sale_id=sale.id, product_id=p.id, qty=1, unit_price=Decimal('20.00'), line_total=Decimal('20.00'))
        db.session.add(si)
        db.session.add(SalePayment(sale_id=sale.id, amount=Decimal('20.00'), method='Cash'))
        db.session.commit()

        # Create a repair/device with a ticket and service type
        ticket = f"T-SEARCH-{uuid.uuid4().hex[:6]}"
        cust = Customer.query.first()
        d = Device(ticket_number=ticket, customer_id=cust.id if cust else 1, device_type='phone', brand='Acme', model='X', issue_description='Search test')
        d.total_cost = Decimal('150.00')
        d.balance_due = Decimal('150.00')
        d.payment_status = 'Pending'
        d.service_type = 'Screen Replacement'
        # set created_at to yesterday to allow date filtering
        d.created_at = datetime.utcnow() - timedelta(days=1)
        db.session.add(d)
        db.session.flush()
        part = RepairPartUsed(device_id=d.id, product_id=p.id, qty=1, unit_price=p.sell_price, line_total=p.sell_price)
        db.session.add(part)
        db.session.commit()

        # Create many sales to test pagination
        recent_sales = []
        for i in range(25):
            s = Sale(invoice_no=f"PG-SALE-{uuid.uuid4().hex[:6]}-{i}", customer_id=1, status='PAID', subtotal=Decimal('10.00'), discount=Decimal('0.00'), tax=Decimal('0.00'), total=Decimal('10.00'))
            db.session.add(s)
            db.session.flush()
            si2 = SaleItem(sale_id=s.id, product_id=p.id, qty=1, unit_price=Decimal('10.00'), line_total=Decimal('10.00'))
            db.session.add(si2)
            recent_sales.append(s)
        db.session.commit()

    # Search by invoice
    rv = client.get(f"/sales/list?q={inv}")
    assert rv.status_code == 200
    assert inv.encode() in rv.data

    # Search by customer name should return the sale
    rv = client.get(f"/sales/list?q={cust.name}")
    assert rv.status_code == 200
    assert inv.encode() in rv.data

    # Search by product name should return the sale(s)
    rv = client.get(f"/sales/list?q=Test+Product")
    assert rv.status_code == 200
    assert b'SEARCH-INV' in rv.data or b'PG-SALE' in rv.data

    # Search returns repair ticket
    rv = client.get(f"/sales/list?q={ticket}")
    assert rv.status_code == 200
    assert ticket.encode() in rv.data

    # Status filter (only paid)
    rv = client.get('/sales/list?status=PAID')
    assert rv.status_code == 200
    # the PAID recent sales should appear
    assert b'PG-SALE' in rv.data
    # ticket (Pending) should not be present in PAID-only results
    assert ticket.encode() not in rv.data

    # Date filter: only include items from yesterday (ticket created yesterday)
    date_from = (datetime.utcnow() - timedelta(days=1)).date().isoformat()
    date_to = (datetime.utcnow() - timedelta(days=1)).date().isoformat()
    rv = client.get(f'/sales/list?date_from={date_from}&date_to={date_to}')
    assert rv.status_code == 200
    # ticket should appear because its created_at was set to yesterday
    assert ticket.encode() in rv.data

    # Pagination with search (page 2)
    rv1 = client.get('/sales/list')
    assert rv1.status_code == 200
    rv2 = client.get('/sales/list?page=2')
    assert rv2.status_code == 200
    assert b'PG-SALE' in rv2.data
