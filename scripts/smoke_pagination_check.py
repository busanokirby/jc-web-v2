import sys
sys.path.insert(0, r'C:\jc-web-v2')
import os
from app import create_app
# Ensure SECRET_KEY present for create_app (used in test/dev runs)
os.environ.setdefault('SECRET_KEY', 'dev-secret')
app = create_app()
app.testing = True
with app.app_context():
    client = app.test_client()
    client.post('/auth/login', data={'username':'admin','password':'admin123'}, follow_redirects=True)
    for url in ['/inventory/products', '/inventory/products?page=2', '/inventory/movements', '/sales/list', '/customers', '/users', '/customers/1']:
        rv = client.get(url)
        print(url, rv.status_code, 'len', len(rv.data))
        if rv.status_code != 200:
            print(rv.data.decode('utf-8', errors='ignore')[:2000])
