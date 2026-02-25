from app import create_app
from app.extensions import db
from app.models.email_config import SMTPSettings

app = create_app()
with app.app_context():
    SMTPSettings.query.delete()
    cfg = SMTPSettings(smtp_server='s', smtp_port=1, email_address='e', use_tls=False, frequency='daily')
    cfg.set_password('p')
    cfg.set_recipients([])
    cfg.is_enabled = True
    db.session.add(cfg)
    db.session.commit()
    client = app.test_client()
    rv = client.get('/admin/email-settings')
    html = rv.data.decode()
    print(html[:1000])
    print('contains warning?', 'SMTP is enabled' in html)
