from decimal import Decimal
import uuid

from app.models.sales import Sale, SaleItem, SalePayment
from app.models.inventory import Product
from app.extensions import db


def test_reprocess_restores_stock_and_clears_sale(app, logged_in_client):
    client = logged_in_client
    with app.app_context():
        # prepare a product with stock
        p = Product.query.filter_by(name='Test Product').first()
        assert p is not None
        p.stock_on_hand = 5
        db.session.commit()

        # create a sale with one item and deduct stock
        sale = Sale(invoice_no=f"T-SALE-REPROC-1-{uuid.uuid4().hex[:6]}",
                    subtotal=Decimal('20.00'), discount=Decimal('0.00'),
                    tax=Decimal('0.00'), total=Decimal('20.00'), status='PAID')
        db.session.add(sale)
        db.session.flush()
        si = SaleItem(sale_id=sale.id, product_id=p.id, qty=2,
                      unit_price=Decimal('10.00'), line_total=Decimal('20.00'))
        db.session.add(si)
        # deduct stock as normally happens
        p.stock_on_hand -= 2
        db.session.add(SalePayment(sale_id=sale.id, amount=Decimal('20.00'), method='Cash'))
        db.session.commit()
        sale_id = sale.id
        original_stock = p.stock_on_hand
    
    # call reprocess endpoint
    resp = client.post(f'/sales/{sale_id}/reprocess', json={})
    assert resp.status_code == 200
    data = resp.get_json()
    # response wraps details inside 'data' key
    assert data.get('success') is True
    assert 'items_processed' in data.get('data', {}) and data['data']['items_processed'] == 1

    with app.app_context():
        # sale should be removed from DB
        assert Sale.query.get(sale_id) is None
        # stock should have been returned to its original value (5)
        p2 = Product.query.get(p.id)
        assert p2.stock_on_hand == 5


def test_reprocess_aborts_on_stock_error(app, logged_in_client, monkeypatch):
    client = logged_in_client

    with app.app_context():
        # create a simple sale same as above
        p = Product.query.filter_by(name='Test Product').first()
        p.stock_on_hand = 5
        db.session.commit()

        sale = Sale(invoice_no=f"T-SALE-REPROC-ERR-{uuid.uuid4().hex[:6]}",
                    subtotal=Decimal('10.00'), discount=Decimal('0.00'),
                    tax=Decimal('0.00'), total=Decimal('10.00'), status='PAID')
        db.session.add(sale)
        db.session.flush()
        si = SaleItem(sale_id=sale.id, product_id=p.id, qty=1,
                      unit_price=Decimal('10.00'), line_total=Decimal('10.00'))
        db.session.add(si)
        p.stock_on_hand -= 1
        db.session.commit()
        sale_id = sale.id

    # monkeypatch stock_in to throw error
    import app.services.stock as stock_module
    def fake_stock_in(product, qty, notes=""):
        raise Exception("simulated failure")
    monkeypatch.setattr(stock_module, 'stock_in', fake_stock_in)

    resp = client.post(f'/sales/{sale_id}/reprocess', json={})
    assert resp.status_code == 500
    data = resp.get_json()
    assert data['success'] is False
    assert 'simulated failure' in data['message']

    with app.app_context():
        # sale record should still exist because operation aborted
        assert Sale.query.get(sale_id) is not None
        # stock should remain reduced because restoration never happened
        # fetch value directly to avoid detached-instance issues
        from sqlalchemy import select
        result = db.session.execute(select(Product.stock_on_hand).where(Product.id == p.id)).scalar_one()
        assert result == 4
