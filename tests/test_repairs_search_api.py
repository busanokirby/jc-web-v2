import json


def test_repairs_search_api_returns_results(logged_in_client):
    client = logged_in_client
    # create a known ticket then search for it
    from app.models.repair import Device
    from app.extensions import db
    import uuid
    with client.application.app_context():
        d = Device(ticket_number=f"T-SEARCH-{uuid.uuid4().hex[:6]}", customer_id=1, device_type='phone', issue_description='search test')
        db.session.add(d)
        db.session.commit()
        ticket = d.ticket_number

    resp = client.get(f'/repairs/search/api?q={ticket}')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert isinstance(data, list)
    assert any(item.get('ticket') == ticket for item in data)


def test_repairs_search_api_needs_minimum_chars(logged_in_client):
    client = logged_in_client
    resp = client.get('/repairs/search/api?q=a')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data == []
