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

    The job function needs access to the Flask application context.  APScheduler
    runs jobs in a background thread where ``current_app`` is not available,
    therefore we capture the app instance here and pass it as an argument.
    """
    if scheduler.running:
        return

    # Add job to check and send emails every minute, providing ``app`` as an
    # argument so the job can establish an application context safely.
    scheduler.add_job(
        func=check_and_send_email,
        args=[app],
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


def check_and_send_email(app):
    """
    Executed every minute by the scheduler to check and send the automated
    report.

    ``app`` is passed by ``init_scheduler`` so that the function can enter a
    proper Flask application context.  Attempting to read ``current_app``
    directly in a scheduler thread raises ``RuntimeError`` (see error logs),
    hence the explicit argument.
    """
    try:
        with app.app_context():
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
