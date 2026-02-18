from decimal import Decimal
import uuid

from app.models.sales import Sale, SaleItem, SalePayment
from app.models.inventory import Product
from app.models.repair import Device, RepairPartUsed
from app.extensions import db


def test_delete_sale_restores_stock(app, logged_in_client):
    client = logged_in_client
    with app.app_context():
        # prepare product with stock
        p = Product.query.filter_by(name='Test Product').first()
        assert p is not None
        p.stock_on_hand = 5
        db.session.commit()

        # create sale and deduct stock to simulate a completed sale
        sale = Sale(invoice_no=f"T-SALE-DEL-1-{uuid.uuid4().hex[:6]}", subtotal=Decimal('30.00'), discount=Decimal('0.00'), tax=Decimal('0.00'), total=Decimal('30.00'), status='PAID')
        db.session.add(sale)
        db.session.flush()

        si = SaleItem(sale_id=sale.id, product_id=p.id, qty=2, unit_price=Decimal('15.00'), line_total=Decimal('30.00'))
        db.session.add(si)

        # deduct stock as real sale would
        p.stock_on_hand -= 2

        db.session.add(SalePayment(sale_id=sale.id, amount=Decimal('30.00'), method='Cash'))
        db.session.commit()

        assert p.stock_on_hand == 3
        sale_id = sale.id

    # delete the sale (admin client)
    resp = client.post(f'/sales/{sale_id}/delete', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        # sale should be removed
        assert Sale.query.get(sale_id) is None
        # stock restored
        p2 = Product.query.get(p.id)
        assert p2.stock_on_hand == 5


def test_delete_sale_removes_payments_and_items(app, logged_in_client):
    client = logged_in_client
    with app.app_context():
        p = Product.query.filter_by(name='Test Product').first()
        p.stock_on_hand = 10
        db.session.commit()

        sale = Sale(invoice_no=f"T-SALE-DEL-2-{uuid.uuid4().hex[:6]}", subtotal=Decimal('15.00'), discount=Decimal('0.00'), tax=Decimal('0.00'), total=Decimal('15.00'), status='PAID')
        db.session.add(sale)
        db.session.flush()
        si = SaleItem(sale_id=sale.id, product_id=p.id, qty=1, unit_price=Decimal('15.00'), line_total=Decimal('15.00'))
        db.session.add(si)
        db.session.add(SalePayment(sale_id=sale.id, amount=Decimal('15.00'), method='Cash'))
        p.stock_on_hand -= 1
        db.session.commit()
        sale_id = sale.id

    resp = client.post(f'/sales/{sale_id}/delete', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        assert Sale.query.get(sale_id) is None
        # payments and items deleted by cascade
        assert not SalePayment.query.filter_by(sale_id=sale_id).count()
        assert not SaleItem.query.filter_by(sale_id=sale_id).count()


def test_sales_list_search_by_invoice_and_sku(app, logged_in_client):
    client = logged_in_client
    with app.app_context():
        # create a unique product and sale
        sku = f"SSK-{uuid.uuid4().hex[:8]}"
        p = Product(name='SearchProduct', sku=sku, stock_on_hand=10, is_active=True)
        db.session.add(p)
        db.session.commit()

        inv = f"SEARCH-INV-{uuid.uuid4().hex[:6]}"
        sale = Sale(invoice_no=inv, subtotal=Decimal('20.00'), discount=Decimal('0.00'), tax=Decimal('0.00'), total=Decimal('20.00'), status='PAID')
        db.session.add(sale)
        db.session.flush()
        si = SaleItem(sale_id=sale.id, product_id=p.id, qty=1, unit_price=Decimal('20.00'), line_total=Decimal('20.00'))
        db.session.add(si)
        db.session.add(SalePayment(sale_id=sale.id, amount=Decimal('20.00'), method='Cash'))
        p.stock_on_hand -= 1
        db.session.commit()
        sale_id = sale.id

    # Search by invoice
    rv = client.get(f"/sales/list?q={inv}")
    assert rv.status_code == 200
    assert inv.encode() in rv.data

    # Search by SKU
    rv2 = client.get(f"/sales/list?q={sku}")
    assert rv2.status_code == 200
    assert inv.encode() in rv2.data


def test_sales_list_search_returns_repair_ticket(app, logged_in_client):
    client = logged_in_client
    with app.app_context():
        # create a device with a part so it shows in history
        ticket = f"T-SEARCH-{uuid.uuid4().hex[:6]}"
        from app.models.customer import Customer
        c = Customer.query.filter_by(customer_code='TC-001').first()
        d = Device(ticket_number=ticket, customer_id=c.id, device_type='phone', brand='Acme', model='X', issue_description='Search test')
        db.session.add(d)
        db.session.flush()

        prod = Product.query.filter_by(name='Test Product').first()
        if not prod:
            prod = Product(name='Test Product', sku=f"TP-{uuid.uuid4().hex[:6]}", stock_on_hand=5, is_active=True)
            db.session.add(prod)
            db.session.flush()

        part = RepairPartUsed(device_id=d.id, product_id=prod.id, qty=1, unit_price=prod.sell_price, line_total=prod.sell_price)
        db.session.add(part)
        db.session.commit()
        dev_id = d.id

    rv = client.get(f"/sales/list?q={ticket}")
    assert rv.status_code == 200
    assert ticket.encode() in rv.data