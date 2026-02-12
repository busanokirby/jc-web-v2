import csv


def test_low_stock_page_and_csv(logged_in_client):
    client = logged_in_client
    resp = client.get('/inventory/low-stock')
    assert resp.status_code == 200
    assert b'Low Stock' in resp.data

    resp_csv = client.get('/inventory/low-stock?format=csv')
    assert resp_csv.status_code == 200
    assert 'text/csv' in resp_csv.headers.get('Content-Type', '')
    text = resp_csv.get_data(as_text=True)
    assert 'SKU,Name,Stock,Threshold,Reorder To,Reorder Qty' in text


def test_adjust_stock_and_movement(logged_in_client):
    client = logged_in_client
    # Get product id
    resp = client.get('/inventory/products')
    assert resp.status_code == 200
    # Find Test Product id by simple string search
    data = resp.get_data(as_text=True)
    assert 'Test Product' in data

    # Use adjust endpoint to add 5 units
    from app.models.inventory import Product, StockMovement
    from app.extensions import db
    # Query DB within app context
    with client.application.app_context():
        p = Product.query.filter_by(name='Test Product').first()
        assert p is not None
        initial = p.stock_on_hand

    resp_post = client.post('/inventory/adjust', data={'product_id': p.id, 'delta': '5', 'notes': 'Test add'}, follow_redirects=True)
    assert resp_post.status_code == 200

    with client.application.app_context():
        p = Product.query.get(p.id)
        assert p.stock_on_hand == initial + 5

        # Check movement exists
        mv = StockMovement.query.filter_by(product_id=p.id, movement_type='ADJUST').order_by(StockMovement.id.desc()).first()
        assert mv is not None
        assert mv.qty == 5


def test_movements_page(logged_in_client):
    client = logged_in_client
    resp = client.get('/inventory/movements')
    assert resp.status_code == 200
    assert b'Stock Movements' in resp.data
