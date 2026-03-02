"""
Email Service for sending automated reports
"""
from __future__ import annotations
from datetime import datetime, date, timezone, timedelta
from typing import List, Optional
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

from app.models.email_config import SMTPSettings, EmailReport
from app.services.report_service import ReportService
from app.extensions import db

logger = logging.getLogger(__name__)

# Philippines timezone: UTC+8
PHILIPPINES_TZ = timezone(timedelta(hours=8))

def get_ph_now():
    """Get current datetime in Philippines timezone (UTC+8)"""
    return datetime.now(PHILIPPINES_TZ)

def get_ph_date():
    """Get current date in Philippines timezone (UTC+8)"""
    return get_ph_now().date()


class EmailService:
    """Service for sending email reports via SMTP"""
    
    @staticmethod
    def _prepare_email_records(report_data: dict) -> list:
        """
        Convert report data into display-friendly records for email template.
        
        Handles both:
        - Daily reports with 'all_transactions' (display format)
        - Periodic reports with 'sales_records' (export format that needs transformation)
        
        Args:
            report_data: Report dict from ReportService
            
        Returns:
            List of records with keys: customer, type, description, amount, is_partial, receipt_type, receipt_id
        """
        # Priority 1: Use all_transactions if available (daily reports with display format)
        if 'all_transactions' in report_data and report_data['all_transactions']:
            return report_data['all_transactions']
        
        # Priority 2: Transform sales_records and repair_records (export format)
        display_records = []
        
        # Transform sales records
        if 'sales_records' in report_data:
            sales = report_data.get('sales_records', [])
            for sale in sales:
                # Handle both formats: Excel export format and original format
                if 'customer_name' in sale:  # Excel export format
                    display_records.append({
                        'customer': sale.get('customer_name', 'Walk-in'),
                        'type': 'Purchase',
                        'description': sale.get('items_description', ''),
                        'amount': sale.get('amount_paid', 0),
                        'is_partial': sale.get('payment_status', '').upper() == 'PARTIAL',
                        'payment_status': sale.get('payment_status', 'PAID'),
                        'receipt_type': 'sale',
                        'receipt_id': sale.get('sale_id', 0),
                        'datetime': sale.get('payment_date', date.today())
                    })
                elif 'customer' in sale:  # Original display format
                    display_records.append(sale)
        
        # Transform repair records (if any)
        if 'repair_records' in report_data:
            repairs = report_data.get('repair_records', [])
            for repair in repairs:
                if 'customer_name' in repair:  # Excel export format
                    display_records.append({
                        'customer': repair.get('customer_name', 'Walk-in'),
                        'type': 'Repair',
                        'description': repair.get('device_type', ''),
                        'amount': repair.get('amount_paid', 0),
                        'is_partial': repair.get('payment_status', '').upper() == 'PARTIAL',
                        'payment_status': repair.get('payment_status', 'PAID'),
                        'receipt_type': 'repair',
                        'receipt_id': repair.get('device_id', 0),
                        'datetime': repair.get('payment_date', date.today())
                    })
                elif 'customer' in repair:  # Original display format
                    display_records.append(repair)
        
        return display_records
    
    @staticmethod
    def generate_html_body(report_data: dict, config: SMTPSettings) -> str:
        """
        Generate mobile-friendly HTML email body from pre-calculated report_data.

        Args:
            report_data: Report dict from ReportService (single source of truth)
            config: SMTPSettings config

        Returns:
            HTML string with formatted report
        """
        # Get report metadata
        report_date = report_data.get('report_date', get_ph_date())
        
        # Use totals from report_data (already calculated by ReportService)
        total_revenue = report_data.get('total_revenue', 0)
        total_transactions = report_data.get('total_transactions', 0)
        total_sales_payments = report_data.get('total_sales_payments', 0)
        total_repair_payments = report_data.get('total_repair_payments', 0)
        
        # Use payment breakdown from report_data (centrally computed)
        payment_breakdown = report_data.get('payment_breakdown', {})
        
        # Prepare transaction records for display
        received_records = EmailService._prepare_email_records(report_data)
        
        # Build breakdown rows for HTML
        breakdown_rows = ""
        for method, data in sorted(payment_breakdown.items()):
            breakdown_rows += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #ddd;">{method}</td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: right;">{data.get('count', 0)}</td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: right;">₱{data.get('total', 0):,.2f}</td>
            </tr>
            """
        
        # Build transaction detail rows
        detail_rows = ""
        for rec in received_records:
            dt = rec.get('datetime')
            dt_str = dt.strftime('%Y-%m-%d %I:%M %p') if hasattr(dt, 'strftime') else ''
            
            # Payment status badge
            payment_status = "Partial" if rec.get('is_partial') else "Paid"
            
            detail_rows += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #ddd;">{rec.get('customer','')}</td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd;">{rec.get('type','')}</td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd;">{rec.get('description','')}</td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: center;">{payment_status}</td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: right;">₱{rec.get('amount',0):,.2f}</td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: right; font-size: 12px;">{dt_str}</td>
            </tr>
            """
        
        detail_section = f"""
        <h2 style="color: #1b7e3d; border-bottom: 2px solid #2d8f56; padding-bottom: 10px; margin-top: 30px; margin-bottom: 15px;">Transactions</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background-color: #2d8f56; color: white;">
                    <th style="padding: 12px; text-align: left; font-weight: bold;">Customer</th>
                    <th style="padding: 12px; text-align: left; font-weight: bold;">Type</th>
                    <th style="padding: 12px; text-align: left; font-weight: bold;">Description</th>
                    <th style="padding: 12px; text-align: center; font-weight: bold;">Status</th>
                    <th style="padding: 12px; text-align: right; font-weight: bold;">Amount</th>
                    <th style="padding: 12px; text-align: right; font-weight: bold;">Date/Time</th>
                </tr>
            </thead>
            <tbody>
                {detail_rows}
            </tbody>
        </table>
        """ if received_records else ""
        
        # Stable HTML template from git
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style type="text/css">
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f9f9f9;
                }}
                .container {{
                    background-color: white;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .header {{
                    background-color: #1b7e3d;
                    color: white;
                    padding: 20px;
                    border-radius: 8px 8px 0 0;
                    text-align: center;
                    margin: -30px -30px 30px -30px;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                }}
                .period {{
                    color: #ddd;
                    font-size: 14px;
                    margin-top: 5px;
                }}
                .kpi-section {{
                    background-color: #f5f5f5;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 30px;
                }}
                .kpi-row {{
                    display: flex;
                    justify-content: space-between;
                    padding: 10px 0;
                    border-bottom: 1px solid #ddd;
                }}
                .kpi-row:last-child {{
                    border-bottom: none;
                }}
                .kpi-label {{
                    font-weight: bold;
                    color: #333;
                }}
                .kpi-value {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #1b7e3d;
                }}
                .breakdown-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 30px;
                }}
                .breakdown-table th {{
                    background-color: #2d8f56;
                    color: white;
                    padding: 12px;
                    text-align: left;
                    font-weight: bold;
                }}
                .breakdown-table td {{
                    padding: 12px;
                    border-bottom: 1px solid #ddd;
                }}
                .breakdown-table tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #999;
                    font-size: 12px;
                    border-top: 1px solid #ddd;
                    margin-top: 30px;
                }}
                @media only screen and (max-width: 600px) {{
                    body {{
                        padding: 10px;
                    }}
                    .container {{
                        padding: 15px;
                    }}
                    .header {{
                        margin: -15px -15px 20px -15px;
                        padding: 15px;
                    }}
                    .header h1 {{
                        font-size: 20px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Sales & Repair Report</h1>
                    <div class="period">{report_date.strftime('%B %d, %Y')}</div>
                </div>
                
                <div class="kpi-section">
                    <div class="kpi-row">
                        <span class="kpi-label">Total Revenue:</span>
                        <span class="kpi-value">₱{total_revenue:,.2f}</span>
                    </div>
                    <div class="kpi-row">
                        <span class="kpi-label">Total Transactions:</span>
                        <span class="kpi-value">{total_transactions}</span>
                    </div>
                    <div class="kpi-row">
                        <span class="kpi-label">Sales Revenue:</span>
                        <span class="kpi-value">₱{total_sales_payments:,.2f}</span>
                    </div>
                    <div class="kpi-row">
                        <span class="kpi-label">Repair Revenue:</span>
                        <span class="kpi-value">₱{total_repair_payments:,.2f}</span>
                    </div>
                </div>
                
                <h2 style="color: #1b7e3d; border-bottom: 2px solid #2d8f56; padding-bottom: 10px;">Payment Method Breakdown</h2>
                <table class="breakdown-table">
                    <thead>
                        <tr>
                            <th>Payment Method</th>
                            <th style="text-align: right;">Count</th>
                            <th style="text-align: right;">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {breakdown_rows}
                    </tbody>
                </table>
                
                {detail_section}
                
                <div class="footer">
                    <p><strong>Note:</strong> This report includes only received payments (Sales with PAID/PARTIAL status, Repairs with confirmed payments).</p>
                    <p>This is an automated report. Please do not reply to this email.</p>
                    <p>Generated on {get_ph_now().strftime('%B %d, %Y at %I:%M %p')} (Philippines Time - UTC+8)</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    @staticmethod
    def send_report(
        smtp_config: SMTPSettings,
        recipient_emails: list[str] | str,
        report_data: dict,
        attachment_bytes: Optional[bytes] = None,
        attachment_filename: str = ""
    ) -> tuple[bool, str]:
        """
        Send email with report to one or more recipients.
        
        Args:
            smtp_config: SMTPSettings instance
            recipient_emails: single email or list of emails
            report_data: Report data dict
            attachment_bytes: Excel file bytes (optional, not used)
            attachment_filename: Name for attachment (optional, not used)
        
        Returns:
            (success: bool, message: str)
        """
        try:
            # Validate required report_data fields
            required_keys = ['date_range', 'frequency', 'total_revenue', 'total_transactions',
                           'total_sales_payments', 'total_repair_payments']
            missing_keys = [k for k in required_keys if k not in report_data]
            if missing_keys:
                error_msg = f"Report data missing required keys: {missing_keys}"
                logger.error(f"Structural validation failed: {error_msg}")
                return False, error_msg
            
            # Normalize recipients to list
            if isinstance(recipient_emails, str):
                recipients = [recipient_emails]
            else:
                recipients = recipient_emails

            # Prepare message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = EmailService._get_subject(report_data)
            
            # Use configurable sender name (fallback to default if not set)
            sender_name = getattr(smtp_config, 'sender_name', 'JC ICONS DAILY SALES REPORT')
            msg['From'] = f"{sender_name} <{smtp_config.email_address}>"
            msg['To'] = ", ".join(recipients)
            
            # HTML body
            html_body = EmailService.generate_html_body(report_data, smtp_config)
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)

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
        # Note: auto_send_time is stored as Philippines time (UTC+8) from the admin UI
        # Compare against Philippines time to match user expectations
        now_ph = get_ph_now()
        configured_hour = smtp_config.auto_send_time.hour
        configured_minute = smtp_config.auto_send_time.minute
        
        # 1-minute tolerance window: allow sends if within 61 seconds of configured time
        # Prevents missing scheduled time due to scheduler granularity
        time_diff = abs((now_ph.hour * 60 + now_ph.minute) - (configured_hour * 60 + configured_minute))
        if time_diff > 1 and time_diff < (24 * 60 - 1):  # Not within 1-minute window on either side
            return False
        
        # Check if enough time has passed based on frequency
        if not EmailService._should_send_based_on_frequency(smtp_config):
            return False
        
        logger.info(f"Sending {smtp_config.frequency} report at {now_ph}")
        
        # Generate report
        start_date, end_date = ReportService.get_report_period(smtp_config.frequency)
        logger.info(f"Report period: {start_date} to {end_date}, frequency: {smtp_config.frequency}")
        
        # For daily reports, use build_daily_sales_context to get exact same data as web page
        if smtp_config.frequency == 'daily':
            logger.info(f"Building daily sales context for {start_date}")
            daily_ctx = ReportService.build_daily_sales_context(start_date)
            logger.info(f"Daily context built: {len(daily_ctx.get('sales_records', []))} records, total: ₱{daily_ctx.get('total_sales', 0):.2f}")
            
            # If no records, verify database for diagnostics
            if not daily_ctx.get('sales_records'):
                diag = ReportService.verify_database_payments(start_date)
                logger.warning(f"Daily report has no sales_records. Database diagnostics: {diag}")
            
            report_data = ReportService._build_daily_report_data(daily_ctx, start_date, end_date, smtp_config.frequency)
            
            # Extract received_records (filtered, display-formatted) for Excel transactions sheet
            sales_records = daily_ctx.get('sales_records', [])
            received_records = [rec for rec in sales_records if rec.get('amount', 0) > 0]
            report_data['received_records'] = received_records
        else:
            logger.info(f"Building {smtp_config.frequency} report data")
            report_data = ReportService.generate_report_data(start_date, end_date, smtp_config.frequency)
        
        logger.info(f"Report data: {report_data.get('total_transactions', 0)} transactions, ₱{report_data.get('total_revenue', 0):.2f} total")
        
        # include dates for later use
        report_data['start_date'] = start_date
        report_data['end_date'] = end_date

        # Send email without attachment
        recips = smtp_config.get_recipients()
        if not recips:
            logger.warning("No recipients configured for automated report")
            return False
        
        logger.info(f"Sending report to {len(recips)} recipients")
        success, message = EmailService.send_report(
            smtp_config,
            recips,
            report_data,
            None,  # No attachment
            ""     # No filename
        )
        
        logger.info(f"Email send attempt result: success={success}, message={message}")
        
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
            attachment_filename=None,
            report_date_start=start_date,
            report_date_end=end_date,
            status='sent' if success else 'failed',
            error_message=None if success else message
        )
        db.session.add(email_log)
        
        if success:
            smtp_config.last_sent_at = get_ph_now()
            email_log.sent_at = get_ph_now()
        
        db.session.commit()
        
        return success
    
    @staticmethod
    def _should_send_based_on_frequency(smtp_config: SMTPSettings) -> bool:
        """
        Check if report should be sent based on frequency and last_sent_at.
        
        Uses timezone-aware Philippines time for all calculations.
        Uses total_seconds() for precise timing (fixes .days truncation bug).
        .days truncates: 23.5 hours = 0 days → can send twice on server restart
        
        Returns:
            True if enough time has passed, False otherwise
        """
        if not smtp_config.last_sent_at:
            return True
        
        # Use timezone-aware Philippines time (consistent with rest of system)
        current_time_ph = get_ph_now()
        last_sent = smtp_config.last_sent_at
        
        # Ensure last_sent is aware (convert if naive)
        if last_sent.tzinfo is None:
            # Assume naive datetime is already in Philippines time
            last_sent = last_sent.replace(tzinfo=PHILIPPINES_TZ)
        
        # Use total_seconds() for precise comparison (avoids .days truncation)
        time_since_last = (current_time_ph - last_sent).total_seconds()
        
        if smtp_config.frequency == 'daily':
            # 86,400 seconds = 24 hours (precise)
            min_seconds = 86400
        elif smtp_config.frequency == 'every_3_days':
            # 259,200 seconds = 72 hours (precise)
            min_seconds = 259200
        elif smtp_config.frequency == 'weekly':
            # 604,800 seconds = 168 hours = 7 days (precise)
            min_seconds = 604800
        else:
            logger.warning(f"Unknown frequency: {smtp_config.frequency}, defaulting to daily")
            min_seconds = 86400
        
        return time_since_last >= min_seconds
