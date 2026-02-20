from app.services.codes import generate_customer_code
from app.models.customer import Customer


def test_generate_customer_code_ignores_non_jc_prefix(app):
    """When the latest DB row doesn't have a JC-CUST- code, generator should still return next JC-CUST number."""
    with app.app_context():
        from app.extensions import db

        # ensure clean slate for the test
        db.session.query(Customer).delete()
        db.session.commit()

        # Create an existing JC-CUST-001
        c1 = Customer(customer_code='JC-CUST-001', name='First', phone='09110000001')
        db.session.add(c1)
        db.session.commit()

        # Insert a later customer with a different prefix (higher id)
        c2 = Customer(customer_code='TC-FOO-BAR', name='Later', phone='09110000002')
        db.session.add(c2)
        db.session.commit()

        # Generator should return JC-CUST-002 (not collide with existing JC-CUST-001)
        assert generate_customer_code() == 'JC-CUST-002'


def test_generate_customer_code_respects_highest_existing_number(app):
    """If non-sequential JC-CUST entries exist, generator should pick max+1."""
    with app.app_context():
        from app.extensions import db

        db.session.query(Customer).delete()
        db.session.commit()

        db.session.add_all([
            Customer(customer_code='JC-CUST-001', name='A', phone='09110000011'),
            Customer(customer_code='JC-CUST-005', name='B', phone='09110000012'),
            Customer(customer_code='OTH-XYZ', name='C', phone='09110000013')
        ])
        db.session.commit()

        # Highest JC-CUST is 005 -> next should be 006
        assert generate_customer_code() == 'JC-CUST-006'
