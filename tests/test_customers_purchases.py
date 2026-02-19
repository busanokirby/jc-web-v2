from decimal import Decimal

from app.extensions import db
from app.models.sales import Sale, SaleItem


def test_customer_detail_shows_sales_records(app, logged_in_client):
    client = logged_in_client
    import uuid
    from app.models.inventory import Product

    with app.app_context():
        p = Product.query.filter_by(name='Test Product').first()
        # create a sale tied to the test customer (customer_id from fixture)
        s = Sale(invoice_no=f"INV-{uuid.uuid4().hex[:6]}", customer_id=1, status='PAID', subtotal=Decimal('15.00'), discount=Decimal('0.00'), tax=Decimal('0.00'), total=Decimal('15.00'))
        db.session.add(s)
        db.session.flush()
        si = SaleItem(sale_id=s.id, product_id=p.id, qty=1, unit_price=Decimal('15.00'), line_total=Decimal('15.00'))
        db.session.add(si)
        db.session.commit()
        invoice = s.invoice_no

    rv = client.get('/customers/1')
    assert rv.status_code == 200
    assert invoice.encode() in rv.data
    # total should be shown (formatted) — currency filter does not include symbol here
    assert b'15.00' in rv.data
