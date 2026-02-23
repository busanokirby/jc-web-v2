from app import create_app
from app.extensions import db
from datetime import datetime

import os

# ensure secret key for sessions
os.environ['SECRET_KEY'] = 'test'
config = {
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'WTF_CSRF_ENABLED': False,
    'SECRET_KEY': 'test'
}

app = create_app(config=config)
# dict configs don't apply via from_object so update explicitly
app.config.update(config)

with app.app_context():
    db.create_all()
    # create initial product and login user will be added automatically via create_app
    from app.models.inventory import Product
    p = Product.query.filter_by(name='Test Product').first()
    if not p:
        p = Product(name='Test Product', sku='TP-1', cost_price=10, sell_price=15, stock_on_hand=1)
        db.session.add(p)
        db.session.commit()
    client = app.test_client()
    # log in
    rv = client.post('/auth/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    print('login status', rv.status_code)
    resp = client.get('/sales/reports')
    html = resp.data.decode('utf-8')
    # write to temporary file
    with open('debug_reports.html','w', encoding='utf-8') as f:
        f.write(html)
    print('wrote debug_reports.html, length', len(html))
    print('contains daily sales report header?', 'Daily Sales Report' in html)
    print('contains no sales message?', 'No sales recorded for the selected date.' in html)
