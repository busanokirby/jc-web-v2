import pytest
from datetime import time
from app.models.email_config import SMTPSettings
from app.services.email_service import EmailService
from app.extensions import db


def test_email_settings_page_requires_admin(logged_in_client, app):
    # logged_in_client is already admin – ensure it can access
    rv = logged_in_client.get('/admin/email-settings')
    assert rv.status_code == 200
    assert b"SMTP Configuration" in rv.data
    # recipient field should be present
    assert b"Recipient Email" in rv.data

    # use a fresh anonymous client for permission check; the fixture
    # ``client`` used earlier is the same object as ``logged_in_client`` once
    # the latter logs in, so we can't rely on it here.
    with app.test_client() as anon:
        rv2 = anon.get('/admin/email-settings', follow_redirects=True)
        # login form should be shown
        assert b'name="username"' in rv2.data or b"Login" in rv2.data
        # ensure configuration UI itself isn't present
        assert b"SMTP Configuration" not in rv2.data


def test_save_and_toggle_email_settings(logged_in_client, app):
    client = logged_in_client

    # start with no config
    with app.app_context():
        SMTPSettings.query.delete()
        db.session.commit()

    # submit initial settings including recipients
    data = {
        'action': 'save',
        'smtp_server': 'smtp.test.com',
        'smtp_port': '2525',
        'email_address': 'me@test.com',
        'use_tls': 'on',
        'frequency': 'weekly',
        'auto_send_time': '08:30',
        'email_password': 'secret123',
        'recipient_emails': 'foo@a.com, bar@b.org'
    }
    rv = client.post('/admin/email-settings', data=data, follow_redirects=True)
    assert b"Email settings updated successfully" in rv.data

    # verify in database
    with app.app_context():
        cfg = SMTPSettings.query.first()
        assert cfg is not None
        assert cfg.smtp_server == 'smtp.test.com'
        assert cfg.smtp_port == 2525
        assert cfg.email_address == 'me@test.com'
        assert cfg.use_tls is True
        assert cfg.frequency == 'weekly'
        assert cfg.auto_send_time == time(8, 30)
        assert cfg.get_password() == 'secret123'
        assert cfg.get_recipients() == ['foo@a.com', 'bar@b.org']
        # default enabled flag is False
        assert cfg.is_enabled is False

    # toggle enable
    rv = client.post('/admin/email-settings', data={'action': 'toggle'}, follow_redirects=True)
    assert b"Email reporting enabled" in rv.data
    with app.app_context():
        cfg = SMTPSettings.query.first()
        assert cfg is not None
        assert cfg.is_enabled is True

    # clear recipients and save again (simulate admin removing them)
    data2 = {
        'action': 'save',
        'smtp_server': 'smtp.test.com',
        'smtp_port': '2525',
        'email_address': 'me@test.com',
        'use_tls': 'on',
        'frequency': 'weekly',
        'auto_send_time': '08:30',
        'recipient_emails': ''
    }
    # save again with no recipients (ignore flash)
    rv = client.post('/admin/email-settings', data=data2, follow_redirects=True)

    # now toggle enable again; the follow_redirects response should include our warning alert
    rv = client.post('/admin/email-settings', data={'action': 'toggle'}, follow_redirects=True)
    assert b"Email reporting enabled" in rv.data
    assert b"no recipient email" in rv.data.lower()

    # toggle disable
    rv = client.post('/admin/email-settings', data={'action': 'toggle'}, follow_redirects=True)
    assert b"Email reporting disabled" in rv.data
    with app.app_context():
        cfg = SMTPSettings.query.first()
        assert cfg is not None
        assert cfg.is_enabled is False


def test_dashboard_contains_email_link(logged_in_client):
    """Admin dashboard should include a card linking to email settings."""
    rv = logged_in_client.get('/')
    assert b"Email" in rv.data
    assert b"/admin/email-settings" in rv.data

def test_invalid_recipients_are_rejected(logged_in_client):
    """Entering badly formatted recipient addresses should flash an error."""
    client = logged_in_client
    data = {
        'action': 'save',
        'smtp_server': 'smtp.test.com',
        'smtp_port': '2525',
        'email_address': 'me@test.com',
        'use_tls': 'on',
        'frequency': 'daily',
        'auto_send_time': '08:30',
        'recipient_emails': 'good@a.com, bad-email, also@ok.com'
    }
    rv = client.post('/admin/email-settings', data=data, follow_redirects=True)
    assert b"invalid format" in rv.data.lower()


def test_sending_forbidden_without_recipients(monkeypatch, logged_in_client, app):
    """Attempting a test email when no recipients exist should warn."""
    client = logged_in_client
    with app.app_context():
        SMTPSettings.query.delete()
        cfg = SMTPSettings(smtp_server='s', smtp_port=1, email_address='e', use_tls=False, frequency='daily')
        cfg.set_password('p')
        db.session.add(cfg)
        db.session.commit()
    # attempt test action should warn about missing recipients
    rv = client.post('/admin/email-settings', data={'action': 'test'}, follow_redirects=True)
    assert b"no recipient" in rv.data.lower()


def test_automated_send_skips_without_recipients(app):
    """EmailService.send_automated_report should return False if no recipients set."""
    with app.app_context():
        SMTPSettings.query.delete()
        cfg = SMTPSettings(smtp_server='s', email_address='e', use_tls=True, frequency='daily')
        cfg.set_password('p')
        db.session.add(cfg)
        db.session.commit()
        assert EmailService.send_automated_report(cfg) is False


def test_test_email_action(monkeypatch, logged_in_client, app):
    client = logged_in_client
    # prepare a config to test against
    with app.app_context():
        SMTPSettings.query.delete()
        cfg = SMTPSettings(
            smtp_server='smtp.xyz',
            smtp_port=587,
            email_address='user@xyz.com',
            use_tls=True,
            frequency='daily',
            auto_send_time=time(9, 0),
        )
        cfg.set_password('pw')
        cfg.set_recipients(['one@x.com', 'two@y.org'])
        db.session.add(cfg)
        db.session.commit()

    # monkeypatch send_report to avoid real SMTP and observe parameters
    called = {}
    def fake_send_report(config, recipients, report_data, attachment_bytes, filename):
        called['args'] = (config, tuple(recipients))
        called['report_data'] = report_data
        called['attachment'] = (attachment_bytes, filename)
        return True, "ok"
    monkeypatch.setattr(EmailService, 'send_report', fake_send_report)

    # perform test action
    rv = client.post('/admin/email-settings', data={'action': 'test'}, follow_redirects=True)
    assert b"Test email sent successfully" in rv.data
    assert called
    assert called['args'][0].email_address == 'user@xyz.com'
    assert called['args'][1] == ('one@x.com', 'two@y.org')
    # daily frequency should omit attachment
    assert called['attachment'][0] is None
    assert called['attachment'][1] == ''
    # report_data should include frequency and date_range
    assert called['report_data']['frequency'] == 'daily'
    assert 'date_range' in called['report_data']

