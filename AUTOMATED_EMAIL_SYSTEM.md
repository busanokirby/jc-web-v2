# Automated Email Reporting System - Implementation Guide

## 🎯 Overview

This document describes the complete automated email reporting system implemented for the JC Icons Management System (v2.0.6+). The system automatically generates and sends sales and repair reports via email at scheduled times with attached Excel files.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     Automated Email Reporting System              │
└─────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
           ┌────────▼────────┐   │   ┌────────▼────────┐
           │  APScheduler    │   │   │  Admin Panel    │
           │  (Background)   │   │   │  (/admin/email) │
           └────────┬────────┘   │   └────────┬────────┘
                    │            │            │
           ┌────────▼────────────▼────────────▼────────┐
           │         Email Service Layer               │
           │  - Config Management (SMTPSettings)       │
           │  - Report Generation (ReportService)      │
           │  - Excel Export (ExcelReportService)      │
           │  - Email Sending (EmailService)           │
           └────────┬────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
  ┌─────▼────┐ ┌────▼─────┐ ┌──▼──────┐
  │ Database │ │ Excel    │ │  SMTP   │
  │  Models  │ │ Files    │ │ Server  │
  └──────────┘ └──────────┘ └─────────┘
```

### Key Modules

1. **Models** (`app/models/email_config.py`)
   - `SMTPSettings`: Stores SMTP configuration and scheduling parameters
   - `EmailReport`: Logs all email send attempts with status and data

2. **Services**
   - `report_service.py`: Generates payment-based reports using actual received amounts
   - `excel_service.py`: Creates mobile-friendly Excel files with charts and summaries
   - `email_service.py`: Handles email composition and SMTP delivery
   - `scheduler.py`: APScheduler background task runner

3. **Admin Interface** (`app/blueprints/admin/`)
   - Configure SMTP credentials securely
   - Set send frequency and time
   - Toggle reporting on/off
   - Send test emails
   - View send history and logs

## Revenue Calculation Rules

### Critical: Revenue = Money Received ONLY

The system **only includes actual payments received**, never unpaid credits:

#### Sales Included:
- ✅ Status: `PAID` or `PARTIAL`  
- ✅ Payment date within report period
- ✅ Actual `SalePayment.amount` (not `Sale.total`)
- ❌ Excluded: `claimed_on_credit = True` (released unpaid)

#### Sales Excluded:
- ❌ DRAFT or VOID status
- ❌ Unpaid/pending sales
- ❌ Credit sales not yet paid
- ❌ Voided transactions

#### Repairs Included:
- ✅ Status: `is_archived = True` (completed)
- ✅ `payment_status = "Paid"` or `deposit_paid > 0`
- ✅ Payment date within report period
- ✅ Actual `deposit_paid` amount
- ❌ Excluded: `claimed_on_credit = True` or `charge_waived = True`

#### Repairs Excluded:
- ❌ Pending repairs
- ❌ Repairs with no payment received
- ❌ Cancelled/waived repairs
- ❌ Repairs released on credit

## Database Schema

### SMTPSettings Table
```sql
CREATE TABLE smtp_settings (
    id INTEGER PRIMARY KEY,
    smtp_server VARCHAR(255) NOT NULL,      -- e.g., smtp.gmail.com
    smtp_port INTEGER DEFAULT 587,
    email_address VARCHAR(255) NOT NULL,
    email_password_encrypted BLOB,          -- Fernet encrypted
    use_tls BOOLEAN DEFAULT TRUE,
    is_enabled BOOLEAN DEFAULT FALSE,
    auto_send_time TIME DEFAULT '09:00',
    frequency VARCHAR(20) DEFAULT 'daily',  -- daily|every_3_days|weekly
    last_sent_at DATETIME,
    created_at DATETIME DEFAULT NOW,
    updated_at DATETIME DEFAULT NOW
);
```

### EmailReport Table
```sql
CREATE TABLE email_report (
    id INTEGER PRIMARY KEY,
    smtp_settings_id INTEGER FOREIGN KEY,
    report_type VARCHAR(50),                -- daily_sales|weekly_sales|etc
    recipient_email VARCHAR(255),
    subject VARCHAR(255),
    total_revenue DECIMAL(12,2),
    total_transactions INTEGER,
    total_sales_payments DECIMAL(12,2),
    total_repair_payments DECIMAL(12,2),
    status VARCHAR(20),                     -- sent|failed|pending
    error_message TEXT,
    attempted_at DATETIME,
    sent_at DATETIME,
    report_date_start DATE,
    report_date_end DATE,
    attachment_filename VARCHAR(255),
    created_at DATETIME DEFAULT NOW
);
```

## Scheduler Operation

### How It Works

1. **Initialization**: When app starts, APScheduler is initialized
   - Adds job to run every minute (at :00 second)
   - Checks if reports should be sent based on frequency/time

2. **Frequency Logic**
   - **Daily**: Sends every 1 day (checks `last_sent_at`)
   - **Every 3 Days**: Sends if ≥ 3 days since `last_sent_at`
   - **Weekly**: Sends if ≥ 7 days since `last_sent_at`

3. **Send Time Matching**
   - Current time hour matches `auto_send_time.hour`
   - Current time minute matches `auto_send_time.minute`
   - Only sends once per period (tracked via `last_sent_at`)

4. **Report Generation**
   - Calls `ReportService.get_report_period()` to get date range
   - Generates report data from sales/repair payments
   - Creates Excel file with formatted sheets
   - Sends email with HTML body + attachment

5. **Logging**
   - Records attempt in `EmailReport` table
   - Logs success/failure with error message
   - Updates `SMTPSettings.last_sent_at` on success

### Graceful Error Handling

- **Configuration Error**: Skips if SMTP not configured
- **SMTP Error**: Logs error, sends admin notification (future feature)
- **Scheduler Error**: Caught in try/except, doesn't crash app
- **Network Timeout**: Retry once after 5 minutes (configurable)

## Excel Report Format

### Summary Sheet
- Total Revenue (sum of sales + repairs)
- Total Transactions (count of payments)
- Sales Revenue (payment-based)
- Repair Revenue (payment-based)
- Payment Method Breakdown (Cash, GCash, Bank, etc.)

### Sales Sheet
Columns:
- Invoice #
- Customer Name
- Payment Method
- Amount Paid (₱)
- Payment Date

### Repairs Sheet
Columns:
- Ticket #
- Customer Name
- Device Type
- Payment Method
- Amount Paid (₱)
- Payment Date

### Formatting
- Professional color scheme (blue headers, light backgrounds)
- Currency formatting (₱)
- Date formatting (YYYY-MM-DD)
- Responsive border styling

## Email Format

### HTML Email Body (Mobile-Friendly)
- **Header**: Report title with date range
- **KPI Section**: 4-column dashboard with key metrics
- **Payment Breakdown**: Table with payment methods
- **Footer**: Timestamp and links
- **Responsive CSS**: Adapts to mobile/tablet/desktop

### Subject Line Examples
- `Daily Sales Report - February 25, 2026`
- `Weekly Sales Report - February 19 – February 25, 2026`
- `Every 3 Days Sales Report - February 23 – February 25, 2026`

### Attachments
- Excel file: `Sales_Report_YYYY_MM_DD.xlsx`
- Base64 encoded and MIME-attached

## Admin Interface

### Access
- **Route**: `/admin/email-settings`
- **Permission**: Admin only
- **Authentication**: Flask-Login required

### Features

#### Configuration Panel
- SMTP Server input
- Port selector
- Email address input
- Password input (encrypted storage)
- TLS toggle
- Frequency selector
- Send time picker (24-hour)

#### Status Display
- Enable/Disable toggle
- Last sent timestamp
- Next scheduled send time
- Email validation

#### Action Buttons
- **Save Settings**: Persist configuration
- **Send Test Email**: Immediately generate and send today's report
- **View Logs**: Access email history

### Logs Page
- **Route**: `/admin/email-logs`
- **Pagination**: 20 items per page
- **Columns**:
  - Date Sent
  - Report Type
  - Status Badge
  - Revenue
  - Transactions
  - Recipient Email
  - Details Button

### Log Details Page
- **Route**: `/admin/email-logs/<id>`
- **Shows**:
  - Full report status
  - Report period
  - Summary statistics
  - Error messages (if failed)
  - Delivery details

## Configuration

### Environment Variables

```bash
# Email encryption key (optional, uses app SECRET_KEY as fallback)
EMAIL_ENCRYPTION_KEY=<base64-encoded-32-byte-key>

# Admin password (for initialization)
ADMIN_PASSWORD=<secure-password>

# Flask environment
FLASK_ENV=production
SECRET_KEY=<your-secret-key>
```

### SMTP Provider Examples

#### Gmail
```
SMTP Server: smtp.gmail.com
Port: 587
Use TLS: ✓
Email: your-email@gmail.com
Password: [App Password - NOT regular password]
```

**Note**: Generate App Password from Google Account Security settings

#### Office 365
```
SMTP Server: smtp.office365.com
Port: 587
Use TLS: ✓
Email: your-email@company.com
Password: Your Office 365 password
```

#### SendGrid
```
SMTP Server: smtp.sendgrid.net
Port: 587
Use TLS: ✓
Email: apikey
Password: SG.xxxxx...
```

#### Custom Server
```
Contact your email provider for SMTP settings
```

## Usage Guide

### Initial Setup

1. **As Admin**, navigate to `/admin/email-settings`
2. **Enter SMTP Credentials**:
   - SMTP Server (e.g., smtp.gmail.com)
   - Port (usually 587 or 465)
   - Email address
   - App Password or Email password
   - Enable TLS
3. **Select Reporting Frequency**:
   - Daily
   - Every 3 Days
   - Weekly
4. **Set Send Time**: Time in 24-hour format (e.g., 09:00 for 9 AM)
5. **Click Save Settings**

### Testing

1. **After saving**, click **Send Test Email**
2. **Verify receipt** in configured email inbox
3. **Check Excel attachment** for proper formatting
4. **Review email layout** on mobile device

### View Reports

- Navigate to `/admin/email-logs`
- Click on any report to see details
- Check for success/failure status
- Review error messages if failed

### Disable Reporting

- Navigate to `/admin/email-settings`
- Click **Disable** button
- Reports won't be sent until re-enabled

## Security Considerations

### Password Encryption
- Passwords encrypted using Fernet (symmetric encryption)
- Uses `app.config['SECRET_KEY']` as base key
- Can specify custom key via `EMAIL_ENCRYPTION_KEY` env var
- Passwords never logged or displayed in UI

### CSRF Protection
- All admin forms include CSRF tokens
- Flask-WTF middleware validates requests

### Admin Access Control
- Routes protected with `@admin_required` decorator
- Must be logged in with ADMIN role
- Cannot be accessed by SALES, TECH, or other roles

### Secure Parameter Handling
- No sensitive data in URL parameters
- No password in email headers
- No credentials exposed in error messages

## Troubleshooting

### Email Not Sending

1. **Check SMTP Configuration**
   ```
   - Verify SMTP server address
   - Check port number
   - Confirm TLS setting
   ```

2. **Check Credentials**
   ```
   - Test in Gmail: Use App Password, not regular password
   - Test in Office 365: Use Office 365 password
   - Verify email address matches account
   ```

3. **Test Email Feature**
   ```
   - Send test email to verify connectivity
   - Check logs for error messages
   ```

4. **Check Firewall**
   ```
   - Verify port 587 or 465 not blocked
   - Check if ISP blocks SMTP
   - Try different port if blocked
   ```

### No Data in Report

1. **Check Sales/Repairs Exist**
   ```
   - Verify sales created and marked PAID/PARTIAL
   - Verify repairs completed with payment received
   ```

2. **Check Date Range**
   ```
   - For daily: checks today's payments
   - For weekly: checks last 7 days
   - For every_3_days: checks last 3 days
   ```

3. **Check Payment Status**
   ```
   - Sales must be PAID or PARTIAL (not DRAFT/VOID)
   - Repairs must be completed (is_archived=True)
   - Must have actual payment recorded
   ```

### Scheduler Not Running

1. **Check App Logs**
   ```
   - APScheduler logs to app logger
   - Check for "Email scheduler started" message
   ```

2. **Verify APScheduler Installed**
   ```
   pip list | grep APScheduler
   ```

3. **Check for Conflicts**
   ```
   - Ensure only one instance of app running
   - Check for port conflicts
   ```

## API Reference

### Services

#### ReportService.generate_report_data()
```python
from app.services.report_service import ReportService
from datetime import date

# Generate report for date range
report_data = ReportService.generate_report_data(
    start_date=date(2026, 2, 25),
    end_date=date(2026, 2, 25),
    frequency='daily'
)

# Returns: {
#     'date_range': 'February 25, 2026',
#     'frequency': 'daily',
#     'total_revenue': 15000.00,
#     'total_transactions': 25,
#     'total_sales_payments': 10000.00,
#     'total_repair_payments': 5000.00,
#     'payment_breakdown': {...},
#     'sales_records': [...],
#     'repair_records': [...]
# }
```

#### ExcelReportService.create_report()
```python
from app.services.excel_service import ExcelReportService

# Create Excel bytes from report data
excel_bytes = ExcelReportService.create_report(report_data)

# Save to file
with open('report.xlsx', 'wb') as f:
    f.write(excel_bytes)
```

#### EmailService.send_report()
```python
from app.services.email_service import EmailService
from app.models.email_config import SMTPSettings

config = SMTPSettings.get_active_config()
success, message = EmailService.send_report(
    smtp_config=config,
    recipient_email='admin@company.com',
    report_data=report_data,
    attachment_bytes=excel_bytes,
    attachment_filename='Sales_Report_2026_02_25.xlsx'
)

# Returns: (True, "Email sent successfully") or (False, "Error message")
```

## Future Enhancements

### Planned Features
1. **Multiple Recipients**: Send to multiple email addresses
2. **Email Templates**: Customizable HTML templates
3. **Report Scheduling UI**: Advanced cron-like scheduling
4. **Email Retry Logic**: Exponential backoff for failures
5. **Admin Alerts**: Dashboard notifications for failed sends
6. **Report Customization**: Select which metrics to include
7. **Attachment Options**: PDF, CSV, or Excel format selection
8. **Timezone Support**: Configure sends for different timezones
9. **Webhook Integration**: Send report data to external systems
10. **Performance Optimization**: Cache report data between sends

## Version Information

- **System**: JC Icons Management System v2.0.6+
- **Framework**: Flask 3.0.0
- **ORM**: SQLAlchemy 2.0.23
- **Scheduler**: APScheduler 3.10.4
- **Excel Engine**: openpyxl 3.11.0
- **Encryption**: cryptography 41.0.7

## Support & Documentation

For issues or questions:
1. Check troubleshooting section above
2. Review admin logs at `/admin/email-logs`
3. Check application logs in `logs/app.log`
4. Examine detailed error messages in `EmailReport.error_message`

---

**Last Updated**: February 25, 2026
**System Version**: 2.0.6
