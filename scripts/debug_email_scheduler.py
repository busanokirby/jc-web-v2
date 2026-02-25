"""
Debug script to diagnose email scheduler issues
Run this to see what the scheduler sees
"""
from datetime import datetime
from app import create_app
from app.models.email_config import SMTPSettings
from app.extensions import db

app = create_app()

with app.app_context():
    config = SMTPSettings.get_active_config()
    
    print("=" * 60)
    print("EMAIL SCHEDULER DEBUG")
    print("=" * 60)
    
    if not config:
        print("\n❌ NO EMAIL CONFIG FOUND")
        print("   Action: Go to Admin Panel > Email Settings to configure")
        exit(1)
    
    print("\n✓ Email Configuration Found:")
    print(f"  SMTP Server: {config.smtp_server}:{config.smtp_port}")
    print(f"  Email Address: {config.email_address}")
    print(f"  Is Enabled: {config.is_enabled}")
    print(f"  Frequency: {config.frequency}")
    print(f"  Send Time (Local): {config.auto_send_time.strftime('%H:%M')}")
    
    if not config.is_enabled:
        print("\n❌ EMAIL IS DISABLED")
        print("   Action: Go to Admin Panel > Email Settings > Enable")
        exit(1)
    
    recipients = config.get_recipients()
    if not recipients:
        print("\n❌ NO RECIPIENTS CONFIGURED")
        print("   Action: Add email addresses in Admin Panel > Email Settings")
        exit(1)
    
    print(f"  Recipients: {', '.join(recipients)}")
    print(f"  Last Sent: {config.last_sent_at or 'Never'}")
    
    # Check current time vs scheduled time
    print("\n" + "=" * 60)
    print("TIME MISMATCH CHECK (CRITICAL)")
    print("=" * 60)
    
    now_utc = datetime.utcnow()
    now_local = datetime.now()
    scheduled_time = config.auto_send_time
    
    print(f"\nServer Time (UTC):   {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Server Time (Local): {now_local.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Scheduled Time:      {scheduled_time.strftime('%H:%M')} (as configured)")
    
    # Time comparison
    hour_match = now_utc.hour == scheduled_time.hour
    minute_match = now_utc.minute == scheduled_time.minute
    
    print(f"\nHour Match (UTC):    {now_utc.hour:02d} == {scheduled_time.hour:02d}? {hour_match}")
    print(f"Minute Match (UTC):  {now_utc.minute:02d} == {scheduled_time.minute:02d}? {minute_match}")
    
    if not (hour_match and minute_match):
        print("\n⚠️  TIMEZONE ISSUE DETECTED!")
        print(f"   The scheduler uses UTC time, but you set {scheduled_time.strftime('%H:%M')} local time")
        print(f"   UTC is {(now_utc.hour - now_local.hour) % 24} hours ahead/behind your local time")
        print(f"\n   SOLUTION: Calculate UTC equivalent:")
        
        utc_hour = (scheduled_time.hour - (now_utc.hour - now_local.hour)) % 24
        print(f"   Your {scheduled_time.strftime('%H:%M')} local = {utc_hour:02d}:{scheduled_time.minute:02d} UTC")
        print(f"   Update to {utc_hour:02d}:{scheduled_time.minute:02d} in Email Settings")
    else:
        print("\n✓ Times match! Next check: Frequency eligibility...")
        
        # Check frequency
        from app.services.email_service import EmailService
        should_send = EmailService._should_send_based_on_frequency(config)
        
        print(f"\nFrequency: {config.frequency}")
        print(f"Last Sent: {config.last_sent_at or 'Never sent'}")
        print(f"Should Send Now: {should_send}")
        
        if not should_send and config.last_sent_at:
            time_since = datetime.utcnow() - config.last_sent_at
            print(f"Time Since Last: {time_since.total_seconds() / 3600:.1f} hours")
            
            if config.frequency == 'daily':
                required = 24
            elif config.frequency == 'every_3_days':
                required = 72
            elif config.frequency == 'weekly':
                required = 168
            else:
                required = 24
            
            print(f"Required Interval: {required} hours")
            print(f"Action: Wait {required - time_since.total_seconds()/3600:.1f} more hours or reset last_sent_at")
    
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("""
1. Fix any issues above (enable, add recipients, set UTC time)
2. The scheduler checks every minute at :00 seconds
3. Check application logs for "Email scheduler" messages
4. Send a test email from Admin Panel to verify SMTP works
5. Wait for the scheduled time to pass and check logs again
    """)
