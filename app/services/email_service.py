"""
Email Service for sending automated reports
"""
from __future__ import annotations
from datetime import datetime, date
from typing import List, Optional
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging

from app.models.email_config import SMTPSettings, EmailReport
from app.services.report_service import ReportService
from app.services.excel_service import ExcelReportService
from app.extensions import db

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email reports via SMTP"""
    
    @staticmethod
    def generate_html_body(report_data: dict, config: SMTPSettings) -> str:
        """
        Generate mobile-friendly HTML email body.
        
        Args:
            report_data: Report dict from ReportService
            config: SMTPSettings config
        
        Returns:
            HTML string
        """
        breakdown_rows = ""
        for method, data in sorted(report_data.get('payment_breakdown', {}).items()):
            breakdown_rows += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #ddd;">{method}</td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: right;">{data.get('count', 0)}</td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: right;">₱{data.get('total', 0):,.2f}</td>
            </tr>
            """

        # For daily frequency we include the full transaction list inline
        detail_section = ""
        if report_data.get('frequency') == 'daily':
            # try to pull the same context as the web page
            try:
                start = report_data.get('start_date')
                from app.services.report_service import ReportService
                daily_ctx = ReportService.build_daily_sales_context(start)
                if daily_ctx.get('sales_records'):
                    detail_rows = ""
                    for rec in daily_ctx['sales_records']:
                        dt = rec.get('datetime')
                        dt_str = dt.strftime('%Y-%m-%d %I:%M %p') if hasattr(dt, 'strftime') else ''
                        detail_rows += f"""
                        <tr>
                            <td style=\"padding: 12px; border-bottom: 1px solid #ddd;\">{rec.get('customer','')}</td>
                            <td style=\"padding: 12px; border-bottom: 1px solid #ddd;\">{rec.get('type','')}</td>
                            <td style=\"padding: 12px; border-bottom: 1px solid #ddd;\">{rec.get('description','')}</td>
                            <td style=\"padding: 12px; border-bottom: 1px solid #ddd; text-align: right;\">₱{rec.get('amount',0):,.2f}</td>
                            <td style=\"padding: 12px; border-bottom: 1px solid #ddd; text-align: right;\">{dt_str}</td>
                        </tr>
                        """
                    detail_section = f"""
                    <h2 style="color: #1b7e3d; border-bottom: 2px solid #2d8f56; padding-bottom: 10px;">Transactions</h2>
                    <table class=\"breakdown-table\">
                        <thead>
                            <tr>
                                <th>Customer</th>
                                <th>Type</th>
                                <th>Description</th>
                                <th style=\"text-align: right;\">Amount</th>
                                <th style=\"text-align: right;\">Date/Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {detail_rows}
                        </tbody>
                    </table>
                    """
            except Exception:
                # if anything goes wrong, just omit the detail section
                detail_section = ""

        note = """
                    <p style="font-size: 12px; color: #999;">
                        <strong>Note:</strong> This report includes only received payments (Sales with PAID/PARTIAL status, Repairs with confirmed payments).
                        "The Excel attachment contains detailed transaction records for both sales and repairs."}
                    </p>
                    """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sales & Repair Report</title>
        </head>

        <body style="margin:0; padding:0; background-color:#f4f6f9; font-family: Arial, Helvetica, sans-serif;">

        <!-- OUTER WRAPPER -->
        <table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f4f6f9">
        <tr>
            <td align="center" style="padding:20px 10px;">

            <!-- EMAIL CONTAINER (600px) -->
            <table width="600" cellpadding="0" cellspacing="0" border="0" bgcolor="#ffffff" style="max-width:600px; width:100%; border-radius:8px; overflow:hidden;">

                <!-- HEADER -->
                <tr>
                <td align="center" bgcolor="#0f766e" style="padding:30px 20px; color:#ffffff;">
                    <h1 style="margin:0; font-size:22px; font-weight:bold;">
                    Sales & Repair Report
                    </h1>
                    <p style="margin:8px 0 0 0; font-size:14px; opacity:0.9;">
                    {report_data['date_range']}
                    </p>
                </td>
                </tr>

                <!-- BODY CONTENT -->
                <tr>
                <td style="padding:30px 20px;">

                    <!-- KPI SECTION -->
                    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:25px;">
                    
                    <tr>
                        <td style="padding:10px 0; border-bottom:1px solid #e5e7eb;">
                        <strong style="color:#374151;">Total Revenue</strong>
                        <span style="float:right; color:#059669; font-weight:bold;">
                            ₱{report_data['total_revenue']:,.2f}
                        </span>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding:10px 0; border-bottom:1px solid #e5e7eb;">
                        <strong style="color:#374151;">Total Transactions</strong>
                        <span style="float:right; color:#111827; font-weight:bold;">
                            {report_data['total_transactions']}
                        </span>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding:10px 0; border-bottom:1px solid #e5e7eb;">
                        <strong style="color:#374151;">Sales Revenue</strong>
                        <span style="float:right; color:#059669; font-weight:bold;">
                            ₱{report_data['total_sales_payments']:,.2f}
                        </span>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding:10px 0;">
                        <strong style="color:#374151;">Repair Revenue</strong>
                        <span style="float:right; color:#059669; font-weight:bold;">
                            ₱{report_data['total_repair_payments']:,.2f}
                        </span>
                        </td>
                    </tr>

                    </table>

                    <!-- SECTION TITLE -->
                    <h2 style="font-size:16px; margin:0 0 10px 0; color:#111827; border-bottom:2px solid #e5e7eb; padding-bottom:6px;">
                     Sales Payment Method Breakdown
                    </h2>

                    <!-- TABLE -->
                    
                    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse; font-size:14px;">
                    
                    <tr bgcolor="#f3f4f6">
                        <th align="left" style="padding:10px; border:1px solid #e5e7eb;">Payment Method</th>
                        <th align="right" style="padding:10px; border:1px solid #e5e7eb;">Count</th>
                        <th align="right" style="padding:10px; border:1px solid #e5e7eb;">Total</th>
                    </tr>

                    {breakdown_rows}

                    </table>

                    <!-- OPTIONAL NOTE -->
                    <div style="margin-top:20px;">
                    {note}
                    </div>

                    <!-- OPTIONAL DETAIL SECTION -->
                    <div style="margin-top:20px;">
                    {detail_section}
                    </div>

                </td>
                </tr>

                <!-- FOOTER -->
                <tr>
                <td bgcolor="#f9fafb" align="center" style="padding:20px; font-size:12px; color:#6b7280; border-top:1px solid #e5e7eb;">
                    <p style="margin:0 0 5px 0;">
                    This is an automated report. Please do not reply.
                    </p>
                    <p style="margin:0;">
                    Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                    </p>
                </td>
                </tr>

            </table>
            <!-- END CONTAINER -->

            </td>
        </tr>
        </table>

        </body>
        </html>
        """
        return html
    
    @staticmethod
    def send_report(
        smtp_config: SMTPSettings,
        recipient_emails: list[str] | str,
        report_data: dict,
        attachment_bytes: Optional[bytes],
        attachment_filename: str
    ) -> tuple[bool, str]:
        """
        Send email with report attachment to one or more recipients.
        
        Args:
            smtp_config: SMTPSettings instance
            recipient_emails: single email or list of emails
            report_data: Report data dict
            attachment_bytes: Excel file bytes
            attachment_filename: Name for attachment
        
        Returns:
            (success: bool, message: str)
        """
        """
        Send email with report attachment.
        
        Args:
            smtp_config: SMTPSettings instance
            recipient_email: Email address to send to
            report_data: Report data dict
            attachment_bytes: Excel file bytes
            attachment_filename: Name for attachment
        
        Returns:
            (success: bool, message: str)
        """
        try:
            # Normalize recipients to list
            if isinstance(recipient_emails, str):
                recipients = [recipient_emails]
            else:
                recipients = recipient_emails

            # Prepare message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = EmailService._get_subject(report_data)
            msg['From'] = f"JC ICONS DAILY SALES REPORT <{smtp_config.email_address}>"
            msg['To'] = ", ".join(recipients)
            
            # HTML body
            html_body = EmailService.generate_html_body(report_data, smtp_config)
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Attach file when provided (some frequencies, e.g. daily, use inline details only)
            if attachment_bytes:
                attachment = MIMEBase('application', 'octet-stream')
                attachment.set_payload(attachment_bytes)
                encoders.encode_base64(attachment)
                attachment.add_header('Content-Disposition', 'attachment', filename=attachment_filename or 'report.xlsx')
                msg.attach(attachment)

            # Send via SMTP
            with smtplib.SMTP(smtp_config.smtp_server, smtp_config.smtp_port) as server:
                if smtp_config.use_tls:
                    server.starttls()

                password = smtp_config.get_password()
                server.login(smtp_config.email_address, password)
                server.send_message(msg, from_addr=smtp_config.email_address, to_addrs=recipients)
            
            logger.info(f"Email sent successfully to {recipients}")
            return True, "Email sent successfully"
        
        except Exception as e:
            # give a clearer hint on DNS failures
            if isinstance(e, (socket.gaierror,)):
                error_msg = (
                    f"Failed to send email: could not resolve SMTP host '{smtp_config.smtp_server}'. "
                    "Please verify the server address and network connectivity."
                )
            else:
                error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    @staticmethod
    def _get_subject(report_data: dict) -> str:
        """Generate email subject based on frequency and date"""
        freq = report_data.get('frequency', 'daily')
        date_range = report_data.get('date_range', 'Report')
        
        freq_text = freq.replace('_', ' ').title()
        return f"{freq_text} Sales Report - {date_range}"
    
    @staticmethod
    def send_automated_report(smtp_config: Optional[SMTPSettings] = None) -> bool:
        """
        Check if report should be sent and send it.
        
        This is called by the scheduler every minute.
        
        Args:
            smtp_config: SMTPSettings (default: get active config)
        
        Returns:
            True if report was sent, False otherwise
        """
        if smtp_config is None:
            smtp_config = SMTPSettings.get_active_config()
        
        if not smtp_config or not smtp_config.is_enabled:
            return False
        
        # Check if current time matches scheduled time
        # Note: auto_send_time is stored as local time from the admin UI
        # Compare against local time, not UTC, to match user expectations
        now_local = datetime.now()
        configured_hour = smtp_config.auto_send_time.hour
        configured_minute = smtp_config.auto_send_time.minute
        # scheduler runs every minute so a strict hour/minute comparison is sufficient
        if now_local.hour != configured_hour or now_local.minute != configured_minute:
            return False
        
        # Check if enough time has passed based on frequency
        if not EmailService._should_send_based_on_frequency(smtp_config):
            return False
        
        # Generate report
        start_date, end_date = ReportService.get_report_period(smtp_config.frequency)
        report_data = ReportService.generate_report_data(start_date, end_date, smtp_config.frequency)
        # include dates for later use (HTML detail section)
        report_data['start_date'] = start_date
        report_data['end_date'] = end_date

        # Generate Excel only if not daily (daily report will embed details inline)
        if smtp_config.frequency == 'daily':
            excel_bytes = None
            excel_filename = ''
        else:
            excel_bytes = ExcelReportService.create_report(report_data)
            excel_filename = ExcelReportService.generate_filename(start_date, end_date)
        
        # Send email
        recips = smtp_config.get_recipients()
        if not recips:
            # nothing to send
            return False
        success, message = EmailService.send_report(
            smtp_config,
            recips,
            report_data,
            excel_bytes,
            excel_filename
        )
        
        # Log in database (comma-separated recipients)
        email_log = EmailReport(
            smtp_settings_id=smtp_config.id,
            recipient_email=",".join(recips),
            subject=EmailService._get_subject(report_data),
            total_revenue=report_data['total_revenue'],
            total_transactions=report_data['total_transactions'],
            total_sales_payments=report_data['total_sales_payments'],
            total_repair_payments=report_data['total_repair_payments'],
            report_type=f"{smtp_config.frequency}_sales",
            attachment_filename=excel_filename,
            report_date_start=start_date,
            report_date_end=end_date,
            status='sent' if success else 'failed',
            error_message=None if success else message
        )
        db.session.add(email_log)
        
        if success:
            smtp_config.last_sent_at = datetime.utcnow()
            email_log.sent_at = datetime.utcnow()
        
        db.session.commit()
        
        return success
    
    @staticmethod
    def _should_send_based_on_frequency(smtp_config: SMTPSettings) -> bool:
        """
        Check if report should be sent based on frequency and last_sent_at.
        
        Uses total_seconds() for precise timing (fixes .days truncation bug).
        .days truncates: 23.5 hours = 0 days → can send twice on server restart
        
        Returns:
            True if enough time has passed, False otherwise
        """
        if not smtp_config.last_sent_at:
            # Never sent before, send now
            return True
        
        # Use total_seconds() for precise comparison
        time_since_last = (datetime.utcnow() - smtp_config.last_sent_at).total_seconds()
        
        if smtp_config.frequency == 'daily':
            # 86,400 seconds = 24 hours (precise)
            return time_since_last >= 86400
        elif smtp_config.frequency == 'every_3_days':
            # 259,200 seconds = 72 hours (precise)
            return time_since_last >= 259200
        elif smtp_config.frequency == 'weekly':
            # 604,800 seconds = 168 hours = 7 days (precise)
            return time_since_last >= 604800
        
        return False
