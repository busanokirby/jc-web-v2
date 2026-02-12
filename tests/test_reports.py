def test_repairs_report_csv(logged_in_client):
    client = logged_in_client
    resp = client.get('/reports/repairs?format=csv')
    assert resp.status_code == 200
    assert 'text/csv' in resp.headers.get('Content-Type', '')
    body = resp.get_data(as_text=True)
    assert 'Status,Count,Total Cost' in body
    # Ensure our sample row exists (Received)
    assert 'Received' in body
