from app import create_app
from app.extensions import db
from datetime import datetime

config = {
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'WTF_CSRF_ENABLED': False,
    'SECRET_KEY': 'test'
}

app = create_app(config=config)
app.config.update(config)

with app.app_context():
    db.create_all()
    # ensure customer exists
    from app.models.customer import Customer
    c = Customer.query.filter_by(customer_code='TC-001').first()
    if not c:
        c = Customer(customer_code='TC-001', name='Test Customer', phone='555')
        db.session.add(c)
        db.session.commit()
    # ensure product
    from app.models.inventory import Product
    p = Product.query.filter_by(name='Test Product').first()
    if not p:
        p = Product(name='Test Product', sku='TP-001', cost_price=10, sell_price=15, stock_on_hand=1)
        db.session.add(p)
        db.session.commit()
    # create sale today
    from app.models.sales import Sale, SaleItem
    today = datetime.now().date()
    import uuid
    s = Sale(invoice_no=f"TEST-{uuid.uuid4().hex[:4]}", status='PAID', subtotal=15, discount=0, tax=0, total=15)
    s.created_at = datetime.combine(today, datetime.min.time())
    db.session.add(s); db.session.flush()
    si = SaleItem(sale_id=s.id, product_id=p.id, qty=1, unit_price=15, line_total=15)
    db.session.add(si); db.session.commit()
    # create repair
    from app.models.repair import Device
    d = Device(ticket_number='R-1', customer_id=c.id, device_type='laptop', brand='A', model='B', issue_description='foo', actual_completion=today, total_cost=20)
    db.session.add(d); db.session.commit()
    client = app.test_client()
    # use session cookie manually? can't login easily maybe skip auth by manipulating session
    # Instead use test login circumvent by injecting into session
    with client.session_transaction() as sess:
        sess['_user_id'] = '1'
    resp = client.get(f'/sales/daily-sales?date={today.isoformat()}')
    html = resp.data.decode('utf-8')
    with open('debug_daily.html','w', encoding='utf-8') as f:
        f.write(html)
    print('daily page saved, length', len(html))
