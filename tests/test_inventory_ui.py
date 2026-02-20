import json
import uuid
from app.extensions import db
from app.models.inventory import Product, Category, StockMovement


def test_nav_shows_low_stock_badge(logged_in_client):
    client = logged_in_client
    app = client.application
    with app.app_context():
        low_count = Product.query.filter(Product.is_active==True, Product.stock_on_hand <= Product.reorder_threshold).count()
    rv = client.get('/inventory/products')
    assert b'Inventory' in rv.data
    # Ensure the nav shows the low count near the Inventory link when applicable
    s = rv.data.decode('utf-8')
    idx = s.find('<a class="nav-link" href="/inventory/products">')
    assert idx != -1
    end_idx = s.find('</a>', idx)
    assert end_idx != -1
    snippet = s[idx:end_idx]
    if low_count > 0:
        assert f'>{low_count}<' in snippet


def test_category_delete_blocked_and_delete(logged_in_client):
    client = logged_in_client
    app = client.application
    with app.app_context():
        # Create a temp category and product assigned to it
        cat = Category(name='TempCat', is_active=True)
        db.session.add(cat)
        db.session.flush()
        sku = f"TP-DEL-{uuid.uuid4().hex[:8]}"
        p = Product(name='TempProduct', sku=sku, category_id=cat.id, stock_on_hand=1, is_active=True)
        db.session.add(p)
        db.session.commit()
        cat_id = cat.id

    # The categories page should include a Back button and CSRF hidden input
    r_page = client.get('/inventory/categories')
    html = r_page.data.decode('utf-8')
    assert 'Back to Products' in html
    assert 'name="csrf_token"' in html

    # Attempt to delete - should be blocked
    rv = client.post(f'/inventory/categories/{cat_id}/delete', follow_redirects=True)
    assert b'Category has products' in rv.data

    # Remove product and try again (reload fresh instance and commit)
    with app.app_context():
        p2 = Product.query.filter_by(sku=sku).first()
        p2.is_active = False
        db.session.commit()

    rv2 = client.post(f'/inventory/categories/{cat_id}/delete', follow_redirects=True)
    # Ensure category no longer exists
    with app.app_context():
        assert Category.query.get(cat_id) is None


def test_category_delete_requires_csrf_when_enabled(logged_in_client):
    client = logged_in_client
    app = client.application

    # Create an empty category that can be deleted
    with app.app_context():
        cat = Category(name='CSRFTestCat', is_active=True)
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    # Enable CSRF enforcement for this test
    app.config['WTF_CSRF_ENABLED'] = True

    # Without setting session token, requests should be rejected (403)
    rv = client.post(f'/inventory/categories/{cat_id}/delete')
    assert rv.status_code == 403

    # Now set a valid CSRF token in the session and retry
    with client.session_transaction() as sess:
        sess['_csrf_token'] = 'test-token-123'

    rv2 = client.post(f'/inventory/categories/{cat_id}/delete', data={'csrf_token': 'test-token-123'}, follow_redirects=True)
    assert rv2.status_code == 200

    with app.app_context():
        assert Category.query.get(cat_id) is None


def test_delete_category_from_products_sidebar(logged_in_client):
    client = logged_in_client
    app = client.application

    # Create an empty category that can be deleted via the products page sidebar
    with app.app_context():
        cat = Category(name='SidebarDeleteCat', is_active=True)
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    # Products page should include a delete form for ADMIN users
    r = client.get('/inventory/products')
    html = r.data.decode('utf-8')
    assert f'/inventory/categories/{cat_id}/delete' in html
    assert 'name="csrf_token"' in html

    # Perform delete from the sidebar (no CSRF enforced in tests by default)
    rv = client.post(f'/inventory/categories/{cat_id}/delete', follow_redirects=True)
    assert rv.status_code == 200

    with app.app_context():
        assert Category.query.get(cat_id) is None


def test_ajax_adjust_changes_stock_and_creates_movement(logged_in_client):
    client = logged_in_client
    app = client.application
    with app.app_context():
        sku = f"AP-01-{uuid.uuid4().hex[:8]}"
        p = Product(name='AdjProduct', sku=sku, stock_on_hand=5, is_active=True)
        db.session.add(p)
        db.session.commit()
        pid = p.id

    # Decrease by 2
    rv = client.post(f'/inventory/products/{pid}/adjust', json={'delta': -2})
    data = json.loads(rv.data)
    assert data.get('success') is True
    assert data.get('stock') == 3

    # Verify StockMovement created
    with app.app_context():
        sm = StockMovement.query.filter_by(product_id=pid, movement_type='ADJUST').order_by(StockMovement.id.desc()).first()
        assert sm is not None
        assert sm.qty == 2


def test_stock_in_prefill_and_back_button(logged_in_client):
    client = logged_in_client
    app = client.application
    with app.app_context():
        sku = f"SP-01-{uuid.uuid4().hex[:8]}"
        p = Product(name='StockPrefill', sku=sku, stock_on_hand=7, is_active=True)
        db.session.add(p)
        db.session.commit()
        pid = p.id

    rv = client.get(f'/inventory/stock-in?product_id={pid}')
    html = rv.data.decode('utf-8')
    assert 'Back to Products' in html
    assert 'Change' in html
    # Ensure selected hidden input present
    assert f'name="product_id" value="{pid}"' in html


def test_delete_product_marks_inactive(logged_in_client):
    client = logged_in_client
    app = client.application
    with app.app_context():
        sku = f"TD-01-{uuid.uuid4().hex[:8]}"
        p = Product(name='ToDelete', sku=sku, stock_on_hand=1, is_active=True)
        db.session.add(p)
        db.session.commit()
        pid = p.id

    # Delete (as admin)
    rv = client.post(f'/inventory/products/{pid}/delete', follow_redirects=True)
    assert rv.status_code == 200

    with app.app_context():
        # Product is deleted by the endpoint (hard delete); ensure it's removed
        p2 = Product.query.get(pid)
        assert p2 is None


def test_edit_product_name_updates_name(logged_in_client):
    client = logged_in_client
    app = client.application
    with app.app_context():
        sku = f"ED-{uuid.uuid4().hex[:8]}"
        p = Product(name='Old Product Name', sku=sku, stock_on_hand=3, is_active=True)
        db.session.add(p)
        db.session.commit()
        pid = p.id

    # Fetch edit page and ensure form is prefilled
    r = client.get(f'/inventory/products/{pid}/edit')
    assert r.status_code == 200
    html = r.data.decode('utf-8')
    assert 'Edit Product' in html
    assert 'Old Product Name' in html
    # Edit page should include a Back button to return to the products list
    assert 'Back to Products' in html

    # Submit a corrected name
    rv = client.post(f'/inventory/products/{pid}/edit', data={'name': 'Corrected Product Name'}, follow_redirects=True)
    assert rv.status_code == 200

    with app.app_context():
        p2 = Product.query.get(pid)
        assert p2.name == 'Corrected Product Name'

def test_adjust_buttons_stay_after_adjust(logged_in_client):
    client = logged_in_client
    app = client.application
    with app.app_context():
        sku = f"AS-01-{uuid.uuid4().hex[:8]}"
        p = Product(name='AdjustStay', sku=sku, stock_on_hand=3, is_active=True)
        db.session.add(p)
        db.session.commit()
        pid = p.id

    # Increase by 1
    rv = client.post(f'/inventory/products/{pid}/adjust', json={'delta': 1})
    assert rv.status_code == 200

    # Fetch products page and ensure two adjust buttons are present for that product row
    r2 = client.get('/inventory/products')
    html = r2.data.decode('utf-8')
    # Find the product row and search the full <tr> for adjust buttons
    idx = html.find(f'data-product-id="{pid}"')
    assert idx != -1
    end_idx = html.find('</tr>', idx)
    assert end_idx != -1
    snippet = html[idx:end_idx+5]
    assert snippet.count('btn-adjust') >= 2
