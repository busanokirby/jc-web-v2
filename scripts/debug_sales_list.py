from app import create_app

app = create_app()
app.testing = True
with app.app_context():
    client = app.test_client()
    rv = client.post('/auth/login', data={'username':'admin','password':'admin123'}, follow_redirects=True)
    print('Login status:', rv.status_code)
    print('Login contains welcome:', b'Welcome' in rv.data)
    rv2 = client.get('/sales/list')
    print('/sales/list status:', rv2.status_code)
    if rv2.status_code != 200:
        print('Response length:', len(rv2.data))
        print(rv2.data.decode('utf-8', errors='ignore'))
    else:
        print('Page loaded OK')
