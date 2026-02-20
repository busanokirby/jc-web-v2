from decimal import Decimal
import uuid
from app.extensions import db
from app.models.inventory import Product, Category


def test_inventory_search_multi_field_and_pagination(app, logged_in_client):
    client = logged_in_client
    with app.app_context():
        # category + product fixtures
        cat = Category(name=f"Gadgets-{uuid.uuid4().hex[:6]}")
        db.session.add(cat)
        db.session.flush()

        sku = f"ALPHA-{uuid.uuid4().hex[:6]}"
        p = Product(name="Alpha Widget", sku=sku, category_id=cat.id, stock_on_hand=5, is_active=True)
        db.session.add(p)
        db.session.commit()

        # create multiple matching products to force pagination
        created = []
        for i in range(25):
            pr = Product(name=f"PaginatedX {i}", sku=f"PX-{uuid.uuid4().hex[:6]}-{i}", category_id=cat.id, stock_on_hand=1, is_active=True)
            db.session.add(pr)
            created.append(pr)
        db.session.commit()

        cat_name = cat.name

    # search by name (partial & case-insensitive)
    rv = client.get('/inventory/products?q=alpha')
    assert rv.status_code == 200
    assert b'Alpha Widget' in rv.data

    # search by SKU (case-insensitive)
    rv = client.get('/inventory/products?q=alpha-123')
    assert rv.status_code == 200
    assert b'Alpha Widget' in rv.data

    # search by category name
    rv = client.get(f'/inventory/products?q={cat_name}')
    assert rv.status_code == 200
    assert b'Alpha Widget' in rv.data

    # pagination should work with search
    rv1 = client.get('/inventory/products?q=PaginatedX')
    assert rv1.status_code == 200
    assert b'PaginatedX 0' in rv1.data

    rv2 = client.get('/inventory/products?q=PaginatedX&page=2')
    assert rv2.status_code == 200
    assert b'PaginatedX' in rv2.data
