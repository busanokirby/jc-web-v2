from decimal import Decimal

from app.models.repair import Device
from app.extensions import db


def test_completed_status_auto_archives(app, logged_in_client):
    """When a repair is marked Completed it becomes archived automatically."""
    client = logged_in_client

    import uuid
    with app.app_context():
        # create a transient repair ticket (unique ticket number)
        d = Device(ticket_number=f"T-ARCH-1-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='phone', issue_description='arch test')
        d.status = 'Repairing'
        db.session.add(d)
        db.session.commit()
        device_id = d.id

    # update status to Completed
    resp = client.post(f'/repairs/{device_id}/status', data={'status': 'Completed'}, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        d2 = Device.query.get(device_id)
        assert d2.status == 'Completed'
        assert d2.is_archived is True


def test_repairs_default_hides_archived_and_filters_work(app, logged_in_client):
    """Default /repairs page shows only active (non-archived). archived=1 or status=Completed shows them."""
    client = logged_in_client

    import uuid
    with app.app_context():
        # create an archived/completed repair
        a = Device(ticket_number=f"T-ARCH-2-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='printer', issue_description='arch test 2')
        a.status = 'Completed'
        a.is_archived = True
        db.session.add(a)

        # create an active repair
        b = Device(ticket_number=f"T-ACT-1-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='laptop', issue_description='active')
        b.status = 'Repairing'
        b.is_archived = False
        db.session.add(b)

        db.session.commit()

    # default listing should NOT include the archived ticket
    rv = client.get('/repairs/')
    assert rv.status_code == 200
    assert b'T-ARCH-2' not in rv.data
    assert b'T-ACT-1' in rv.data

    # archived toggle should show archived items
    rv2 = client.get('/repairs/?archived=1')
    assert rv2.status_code == 200
    assert b'T-ARCH-2' in rv2.data

    # explicit status=Completed should show completed tickets even without archived param
    rv3 = client.get('/repairs/?status=Completed')
    assert rv3.status_code == 200
    assert b'T-ARCH-2' in rv3.data


def test_manual_archive_for_existing_completed(app, logged_in_client):
    client = logged_in_client

    import uuid
    with app.app_context():
        d = Device(ticket_number=f"T-ARCH-MAN-1-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='phone', issue_description='manual archive test')
        d.status = 'Completed'
        d.is_archived = False
        db.session.add(d)
        db.session.commit()
        device_id = d.id

    # verify not archived
    with app.app_context():
        d2 = Device.query.get(device_id)
        assert d2.is_archived is False

    # archive via endpoint
    resp = client.post(f'/repairs/{device_id}/archive', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        d3 = Device.query.get(device_id)
        assert d3.is_archived is True

    # default listing should not show it anymore
    rv = client.get('/repairs')
    assert b'T-ARCH-MAN-1' not in rv.data


def test_cannot_archive_non_completed(app, logged_in_client):
    client = logged_in_client

    import uuid
    with app.app_context():
        d = Device(ticket_number=f"T-ARCH-MAN-2-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='phone', issue_description='cannot archive')
        d.status = 'Repairing'
        d.is_archived = False
        db.session.add(d)
        db.session.commit()
        device_id = d.id

    # attempt to archive non-completed repair
    resp = client.post(f'/repairs/{device_id}/archive', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        d2 = Device.query.get(device_id)
        assert d2.is_archived is False
