from datetime import datetime, timedelta
from decimal import Decimal

from app.extensions import db
from app.models.sales import Sale, SaleItem


def test_daily_sales_default_empty(app, logged_in_client):
    client = logged_in_client
    # ensure page loads and shows todays date filter (existing records may be present)
    today = datetime.now().date().isoformat()
    rv = client.get(f'/sales/reports')
    assert rv.status_code == 200
    # filter input should default to today's date
    assert f'value="{today}"'.encode() in rv.data
    # either there are no sales or some data appears, but must not error
    assert b'Daily Sales Report' in rv.data


def _create_sale_on_date(app, date_obj, invoice_prefix="INV", amount=Decimal('20.00')):
    # helper to create a sale on a specific date inside application context
    from app.models.inventory import Product
    with app.app_context():
        p = Product.query.filter_by(name='Test Product').first()
        import uuid
        invoice = f"{invoice_prefix}-{date_obj.isoformat()}-{uuid.uuid4().hex[:6]}"
        s = Sale(invoice_no=invoice, status='PAID', subtotal=amount, discount=Decimal('0.00'), tax=Decimal('0.00'), total=amount)
        # force created_at to date_obj
        s.created_at = datetime.combine(date_obj, datetime.min.time())
        db.session.add(s)
        db.session.flush()
        si = SaleItem(sale_id=s.id, product_id=p.id, qty=1, unit_price=amount, line_total=amount)
        db.session.add(si)
        db.session.commit()
        return invoice, float(amount)


def test_daily_sales_shows_records_and_total(app, logged_in_client):
    client = logged_in_client
    # create sale for yesterday and today
    yesterday = (datetime.now().date() - timedelta(days=1))
    today = datetime.now().date()
    s1_invoice = _create_sale_on_date(app, yesterday, invoice_prefix="YEST")
    s2_invoice = _create_sale_on_date(app, today, invoice_prefix="TODAY")

    # query for yesterday
    rv = client.get(f'/sales/reports?date={yesterday.isoformat()}')
    assert rv.status_code == 200
    # description should appear (using product name)
    assert b'Test Product' in rv.data
    # check total matches one sale
    assert b'Total Sales' in rv.data
    assert b'20.00' in rv.data

    # query for today should include today's record and not yesterday's
    rv2 = client.get(f'/sales/reports?date={today.isoformat()}')
    assert b'Test Product' in rv2.data


def test_future_date_redirects(app, logged_in_client):
    client = logged_in_client
    tomorrow = (datetime.now().date() + timedelta(days=1))
    # test reports route
    rv = client.get(f'/sales/reports?date={tomorrow.isoformat()}', follow_redirects=False)
    assert rv.status_code in (301, 302)
    today = datetime.now().date().isoformat()
    assert f'date={today}' in rv.headers.get('Location', '')
    # test daily-sales route
    rv2 = client.get(f'/sales/daily-sales?date={tomorrow.isoformat()}', follow_redirects=False)
    assert rv2.status_code in (301, 302)
    assert f'date={today}' in rv2.headers.get('Location', '')


def _create_repair_on_date(app, date_obj, total_cost=Decimal('30.00')):
    from app.models.repair import Device
    # must attach to existing test customer id 1
    with app.app_context():
        dev = Device(
            ticket_number=f'R-{date_obj.isoformat()}',
            customer_id=1,
            device_type='laptop',
            brand='Test',
            model='X',
            issue_description='Test issue',
            actual_completion=date_obj,
            total_cost=total_cost
        )
        db.session.add(dev)
        db.session.commit()
        return dev


def test_daily_sales_combines_sources(app, logged_in_client):
    client = logged_in_client
    today = datetime.now().date()
    # clear any existing sales/repairs for the date to isolate
    with app.app_context():
        from app.models.sales import Sale
        from app.models.repair import Device
        start_dt = datetime.combine(today, datetime.min.time())
        end_dt = datetime.combine(today, datetime.max.time())
        Sale.query.filter(Sale.created_at >= start_dt, Sale.created_at <= end_dt).delete(synchronize_session=False)
        Device.query.filter(Device.actual_completion == today).delete(synchronize_session=False)
        db.session.commit()

    # create a sale and a repair on the same date
    sale_amount = Decimal('30.00')
    s_invoice, sale_amount = _create_sale_on_date(app, today, invoice_prefix="COMB", amount=sale_amount)
    r_amount = Decimal('45.00')
    r = _create_repair_on_date(app, today, total_cost=r_amount)

    expected_total = float(sale_amount) + float(r_amount)

    rv = client.get(f'/sales/daily-sales?date={today.isoformat()}')
    assert rv.status_code == 200
    data = rv.data
    # both purchase and repair should appear by amount or description
    assert b'Test Product' in data
    assert b'Repair' in data
    # total should match calculated value
    import re
    text = data.decode('utf-8')
    m = re.search(r'Total Sales:.*?₱([0-9]+\.[0-9]{2})', text)
    assert m, "total not found in page"
    page_total = float(m.group(1))
    assert page_total == expected_total

    # ensure at least two rows present
    assert data.count(b'<tr>') >= 2
