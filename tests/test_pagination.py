from decimal import Decimal
import uuid
from app.extensions import db
from app.models.inventory import Product
from app.models.sales import Sale, SaleItem


def test_inventory_products_pagination(app, logged_in_client):
    client = logged_in_client
    per_page = 20
    created = []
    with app.app_context():
        # create 25 products to force pagination
        for i in range(25):
            sku = f"PG-{uuid.uuid4().hex[:6]}-{i}"
            p = Product(name=f"Paginated Product {i}", sku=sku, stock_on_hand=5, is_active=True)
            db.session.add(p)
            created.append(p)
        db.session.commit()

    # page 1
    rv1 = client.get('/inventory/products')
    assert rv1.status_code == 200
    html = rv1.data.decode('utf-8')
    # Expect pagination summary and at least 1 product row from our new items
    assert 'Showing' in html
    assert 'Paginated Product 0' in html

    # page 2 should contain later items
    rv2 = client.get('/inventory/products?page=2')
    assert rv2.status_code == 200
    html2 = rv2.data.decode('utf-8')
    assert 'Paginated Product' in html2


def test_sales_list_pagination(app, logged_in_client):
    client = logged_in_client
    created_invoices = []
    with app.app_context():
        # Create 25 sales so history has multiple pages
        from app.models.inventory import Product
        p = Product.query.first()
        for i in range(25):
            s = Sale(invoice_no=f"PG-SALE-{uuid.uuid4().hex[:6]}-{i}", customer_id=1, status='PAID', subtotal=Decimal('10.00'), discount=Decimal('0.00'), tax=Decimal('0.00'), total=Decimal('10.00'))
            db.session.add(s)
            db.session.flush()
            si = SaleItem(sale_id=s.id, product_id=p.id, qty=1, unit_price=Decimal('10.00'), line_total=Decimal('10.00'))
            db.session.add(si)
            created_invoices.append(s.invoice_no)
        db.session.commit()

    rv = client.get('/sales/list')
    assert rv.status_code == 200
    html = rv.data.decode('utf-8')
    # Pagination summary should be visible
    assert 'Showing' in html
    # A recently created invoice should appear on page 1
    assert created_invoices[-1] in html
