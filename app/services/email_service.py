"""
Email Service for sending automated reports
"""
from __future__ import annotations
from datetime import datetime, date
from typing import List, Optional
import smtplib
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
                    background-color: #203864;
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
                    color: #666;
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
                    color: #203864;
                }}
                .breakdown-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 30px;
                }}
                .breakdown-table th {{
                    background-color: #4472C4;
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
                .button {{
                    display: inline-block;
                    padding: 10px 20px;
                    margin-top: 20px;
                    background-color: #4472C4;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    text-align: center;
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
                    .kpi-row {{
                        flex-direction: column;
                    }}
                    .kpi-value {{
                        margin-top: 5px;
                    }}
                    .breakdown-table th,
                    .breakdown-table td {{
                        padding: 8px;
                        font-size: 12px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Sales & Repair Report</h1>
                    <div class="period">{report_data['date_range']}</div>
                </div>
                
                <div class="kpi-section">
                    <div class="kpi-row">
                        <span class="kpi-label">Total Revenue:</span>
                        <span class="kpi-value">₱{report_data['total_revenue']:,.2f}</span>
                    </div>
                    <div class="kpi-row">
                        <span class="kpi-label">Total Transactions:</span>
                        <span class="kpi-value">{report_data['total_transactions']}</span>
                    </div>
                    <div class="kpi-row">
                        <span class="kpi-label">Sales Revenue:</span>
                        <span class="kpi-value">₱{report_data['total_sales_payments']:,.2f}</span>
                    </div>
                    <div class="kpi-row">
                        <span class="kpi-label">Repair Revenue:</span>
                        <span class="kpi-value">₱{report_data['total_repair_payments']:,.2f}</span>
                    </div>
                </div>
                
                <h2 style="color: #203864; border-bottom: 2px solid #4472C4; padding-bottom: 10px;">Payment Method Breakdown</h2>
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
                
                <p style="font-size: 12px; color: #999;">
                    <strong>Note:</strong> This report includes only received payments (Sales with PAID/PARTIAL status, Repairs with confirmed payments). 
                    The Excel attachment contains detailed transaction records for both sales and repairs.
                </p>
                
                <div class="footer">
                    <p>This is an automated report. Please do not reply to this email.</p>
                    <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    @staticmethod
    def send_report(
        smtp_config: SMTPSettings,
        recipient_email: str,
        report_data: dict,
        attachment_bytes: bytes,
        attachment_filename: str
    ) -> tuple[bool, str]:
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
            # Prepare message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = EmailService._get_subject(report_data)
            msg['From'] = smtp_config.email_address
            msg['To'] = recipient_email
            
            # HTML body
            html_body = EmailService.generate_html_body(report_data, smtp_config)
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Excel attachment
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(attachment_bytes)
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', 'attachment', filename=attachment_filename)
            msg.attach(attachment)
            
            # Send via SMTP
            with smtplib.SMTP(smtp_config.smtp_server, smtp_config.smtp_port) as server:
                if smtp_config.use_tls:
                    server.starttls()
                
                password = smtp_config.get_password()
                server.login(smtp_config.email_address, password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True, "Email sent successfully"
        
        except Exception as e:
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
    def send_automated_report(smtp_config: SMTPSettings = None) -> bool:
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
        now = datetime.now()
        if now.time().hour != smtp_config.auto_send_time.hour or \
           now.time().minute != smtp_config.auto_send_time.minute:
            return False
        
        # Check if enough time has passed based on frequency
        if not EmailService._should_send_based_on_frequency(smtp_config):
            return False
        
        # Generate report
        start_date, end_date = ReportService.get_report_period(smtp_config.frequency)
        report_data = ReportService.generate_report_data(start_date, end_date, smtp_config.frequency)
        
        # Generate Excel
        excel_bytes = ExcelReportService.create_report(report_data)
        excel_filename = ExcelReportService.generate_filename(start_date, end_date)
        
        # Send email
        success, message = EmailService.send_report(
            smtp_config,
            smtp_config.email_address,
            report_data,
            excel_bytes,
            excel_filename
        )
        
        # Log in database
        email_log = EmailReport(
            smtp_settings_id=smtp_config.id,
            recipient_email=smtp_config.email_address,
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
        
        Returns:
            True if enough time has passed, False otherwise
        """
        if not smtp_config.last_sent_at:
            # Never sent before, send now
            return True
        
        days_since_last = (datetime.utcnow() - smtp_config.last_sent_at).days
        
        if smtp_config.frequency == 'daily':
            return days_since_last >= 1
        elif smtp_config.frequency == 'every_3_days':
            return days_since_last >= 3
        elif smtp_config.frequency == 'weekly':
            return days_since_last >= 7
        
        return False
