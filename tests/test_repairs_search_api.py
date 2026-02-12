import json


def test_repairs_search_api_returns_results(logged_in_client):
    client = logged_in_client
    resp = client.get('/repairs/search/api?q=T-1')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert isinstance(data, list)
    assert any(item.get('ticket') == 'T-100' for item in data)


def test_repairs_search_api_needs_minimum_chars(logged_in_client):
    client = logged_in_client
    resp = client.get('/repairs/search/api?q=a')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data == []
