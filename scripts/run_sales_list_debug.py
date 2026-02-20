import os
import sys
os.environ['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'test-secret')
sys.path.insert(0, r'C:\\jc-web-v2')
from app import create_app

app = create_app()
app.testing = True
with app.app_context():
    client = app.test_client()
    rv = client.post('/auth/login', data={'username':'admin','password':'admin123'}, follow_redirects=True)
    print('login status:', rv.status_code, 'welcome in response:', b'Welcome' in rv.data)
    rv2 = client.get('/sales/list')
    print('/sales/list status:', rv2.status_code)
    if rv2.status_code != 200:
        print('Response (truncated):')
        print(rv2.data.decode('utf-8', errors='ignore')[:8000])
    else:
        print('Page loaded OK')
