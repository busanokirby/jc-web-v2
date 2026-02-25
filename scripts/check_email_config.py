import sys
sys.path.insert(0, '.')
from pathlib import Path
from datetime import datetime

# Load .env
if Path('.env').exists():
    from dotenv import load_dotenv
    load_dotenv()

from app import create_app
from app.models.email_config import SMTPSettings

app = create_app()
with app.app_context():
    config = SMTPSettings.get_active_config()
    
    print("=" * 60)
    print("EMAIL SCHEDULER DEBUG")
    print("=" * 60)
    
    if not config:
        print("\nNO EMAIL CONFIG - Go to Admin Panel to configure")
        sys.exit(1)
    
    print(f"\nEnabled: {config.is_enabled}")
    print(f"SMTP: {config.smtp_server}:{config.smtp_port}")
    print(f"Send Time (Local): {config.auto_send_time}")
    print(f"Frequency: {config.frequency}")
    print(f"Recipients: {config.get_recipients()}")
    print(f"Last Sent: {config.last_sent_at}")
    
    now_utc = datetime.utcnow()
    now_local = datetime.now()
    
    print(f"\nCurrent UTC Time: {now_utc.strftime('%H:%M:%S')}")
    print(f"Current Local Time: {now_local.strftime('%H:%M:%S')}")
    
    tz_diff = (now_utc.hour - now_local.hour) % 24
    print(f"Timezone: UTC is {tz_diff} hours ahead of local")
    
    print(f"\nScheduled Time: {config.auto_send_time.strftime('%H:%M')} (Local)")
    match = now_utc.hour == config.auto_send_time.hour and now_utc.minute == config.auto_send_time.minute
    print(f"Time Match (UTC): {now_utc.hour:02d}:{now_utc.minute:02d} == {config.auto_send_time.hour:02d}:{config.auto_send_time.minute:02d}? {match}")
