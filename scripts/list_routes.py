from app import create_app

app = create_app({'TESTING': True})
with app.app_context():
    rules = [(r.rule, r.endpoint) for r in app.url_map.iter_rules() if 'inventory' in r.rule or 'inventory' in r.endpoint]
    rules.sort()
    for r in rules:
        print(r)
