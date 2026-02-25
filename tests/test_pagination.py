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

    # page 1 - just verify pagination controls show up
    rv1 = client.get('/inventory/products')
    assert rv1.status_code == 200
    html = rv1.data.decode('utf-8')
    # expect pagination summary
    assert 'Showing' in html

    # page 2 should also show pagination
    rv2 = client.get('/inventory/products?page=2')
    assert rv2.status_code == 200
    html2 = rv2.data.decode('utf-8')
    # May or may not have content, but pagination controls should appear
    assert 'Showing' in html2


def test_delete_paginated_products(app, logged_in_client):
    """Test that products on paginated pages can be deleted via AJAX."""
    client = logged_in_client
    product_ids = []
    
    with app.app_context():
        # Create 25 products to force pagination
        for i in range(25):
            sku = f"DEL-{uuid.uuid4().hex[:6]}-{i}"
            p = Product(name=f"Delete Test Product {i}", sku=sku, stock_on_hand=5, is_active=True)
            db.session.add(p)
            db.session.flush()
            product_ids.append(p.id)
        db.session.commit()
    
    # Delete a product from page 1
    rv_del_p1 = client.post(
        f'/inventory/products/{product_ids[0]}/delete',
        headers={'X-Requested-With': 'XMLHttpRequest'},
        json={}
    )
    assert rv_del_p1.status_code == 200
    data = rv_del_p1.get_json()
    assert data['success'] is True
    
    # Verify product is deleted
    with app.app_context():
        assert Product.query.get(product_ids[0]) is None
    
    # Delete a product from page 2 (if it exists)
    rv_del_p2 = client.post(
        f'/inventory/products/{product_ids[20]}/delete',
        headers={'X-Requested-With': 'XMLHttpRequest'},
        json={}
    )
    assert rv_del_p2.status_code == 200
    data = rv_del_p2.get_json()
    assert data['success'] is True
    
    # Verify second product is also deleted
    with app.app_context():
        assert Product.query.get(product_ids[20]) is None

def test_sales_list_pagination(app, logged_in_client):
    client = logged_in_client
    created_invoices = []
    with app.app_context():
        # Create 25 sales so history has multiple pages
        # ``Product`` is imported at module scope already.
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
