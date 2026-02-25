"""
Fixed SMTP Frequency Logic - Precise timing using total_seconds()
Location: app/services/email_service.py
"""

from datetime import datetime
from typing import Optional
from app.models.email_config import SMTPSettings
from app.services.email_service import EmailService

@staticmethod
def _should_send_based_on_frequency(smtp_config) -> bool:
    """
    Check if report should be sent based on frequency and last_sent_at.
    
    Uses total_seconds() for precise timing instead of .days truncation.
    
    Args:
        smtp_config: SMTPSettings instance
    
    Returns:
        True if enough time has passed, False otherwise
    
    Bug Fix:
        Old code used .days which truncates to integer:
        - 23.5 hours = 0 days → can send twice if server restarts
        
        New code uses total_seconds() for precise comparison:
        - 86400 seconds = 1 day (exact)
        - 259200 seconds = 3 days (exact)
        - 604800 seconds = 7 days (exact)
    """
    if not smtp_config.last_sent_at:
        # Never sent before, send now
        return True
    
    time_since_last = (datetime.utcnow() - smtp_config.last_sent_at).total_seconds()
    
    if smtp_config.frequency == 'daily':
        # 86,400 seconds = 24 hours
        return time_since_last >= 86400
    elif smtp_config.frequency == 'every_3_days':
        # 259,200 seconds = 72 hours
        return time_since_last >= 259200
    elif smtp_config.frequency == 'weekly':
        # 604,800 seconds = 168 hours = 7 days
        return time_since_last >= 604800
    
    return False


# BUT ALSO FIX: Timezone-aware scheduling
# Replace the hour/minute check:

@staticmethod
def send_automated_report(smtp_config: Optional[SMTPSettings] = None) -> bool:
    """...(docstring stays same)..."""
    
    if smtp_config is None:
        smtp_config = SMTPSettings.get_active_config()
    
    if not smtp_config or not smtp_config.is_enabled:
        return False
    
    # FIXED: Use UTC consistently
    now_utc = datetime.utcnow()
    
    # FIXED: Compare time components in UTC
    configured_hour = smtp_config.auto_send_time.hour
    configured_minute = smtp_config.auto_send_time.minute
    
    # Check if current UTC time matches scheduled time (within 1-minute window)
    # This accounts for scheduler running every 60 seconds
    if now_utc.hour != configured_hour or now_utc.minute != configured_minute:
        return False
    
    # Check if enough time has passed based on frequency
    if not EmailService._should_send_based_on_frequency(smtp_config):
        return False
    
    # ... rest of method stays same ...
    
    # The real implementation would hit the code above; add explicit return
    return False
