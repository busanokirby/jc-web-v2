"""
Background Scheduler for automated email reporting
Uses APScheduler to run email checks every minute
"""
from __future__ import annotations
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.models.email_config import SMTPSettings
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def init_scheduler(app):
    """
    Initialize and start the scheduler.
    
    Should be called in app initialization (create_app or main).
    """
    if scheduler.running:
        return
    
    # Add job to check and send emails every minute
    scheduler.add_job(
        func=check_and_send_email,
        trigger=CronTrigger(second=0),  # Run every minute
        id='email_report_check',
        name='Check and send email reports',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60
    )
    
    try:
        scheduler.start()
        logger.info("Email scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


def check_and_send_email():
    """
    Executed every minute to check if email should be sent.
    This is the scheduled task function.
    """
    try:
        # Get Flask application context
        from flask import current_app
        with current_app.app_context():
            success = EmailService.send_automated_report()
            if success:
                logger.info(f"Automated email report sent at {datetime.now()}")
    except Exception as e:
        logger.error(f"Error in email check task: {e}", exc_info=True)


def stop_scheduler():
    """Stop the scheduler gracefully"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Email scheduler stopped")
