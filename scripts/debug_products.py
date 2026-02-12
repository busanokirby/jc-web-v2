from app import create_app

app = create_app()
with app.test_client() as c:
    rv = c.post('/auth/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    print('Login status', rv.status_code)
    r = c.get('/inventory/products')
    html = r.data.decode('utf-8')
    inv_idx = html.find('<a class="nav-link" href="/inventory/products">')
    print('Inventory nav snippet:')
    if inv_idx != -1:
        print(html[inv_idx:inv_idx+400])
    else:
        print('not found')
    print('\nFirst product row snippet:')
    p_idx = html.find('data-product-id')
    if p_idx != -1:
        print(html[p_idx:p_idx+1200])
    else:
        print('no product rows found')
