# Email Reporting System - Quick Start

## 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

Done! APScheduler and openpyxl are already in requirements.txt

### 2. Start the Application
```bash
python run.py
```

The email scheduler starts automatically in the background.

### 3. Login as Admin
- Navigate to: `http://localhost:5000`
- Username: `admin`
- Password: Check your `.env` file or use `admin123` (default)

### 4. Configure Email Settings
- Go to: **Admin** → **Email Settings** (or `/admin/email-settings`)
- Fill in SMTP configuration:
  - **SMTP Server**: `smtp.gmail.com` (for Gmail)
  - **Port**: `587`
  - **Email Address**: your-email@gmail.com
  - **Password**: [Google App Password](https://myaccount.google.com/apppasswords)
  - **TLS**: Enable (✓)
  - **Frequency**: Daily
  - **Send Time**: 09:00 (9 AM)
- Click **Save Settings**

### 5. Send Test Email
- Click **Send Test Email** button
- Check your inbox for the report
- Verify Excel attachment is included

### 6. Monitor Email Logs
- Go to: **Admin** → **Email Logs** (or `/admin/email-logs`)
- View all sent reports with dates and status

## What Gets Sent?

### Email Contains:
✅ **Summary**: Total revenue, transactions, payment breakdown
✅ **HTML Body**: Mobile-friendly, colorful dashboard
✅ **Excel File**: Detailed sales and repair records
✅ **Payment Methods**: Breakdown by Cash, GCash, Bank Transfer, etc.

### Data Included:
- ✅ Sales marked PAID or PARTIAL
- ✅ Repairs completed with payment received
- ✅ Actual amounts paid (not credit totals)
- ❌ Unpaid sales/repairs not included
- ❌ Voided or cancelled transactions excluded

## Troubleshooting

### Email Not Sending?
1. Check SMTP credentials (especially Gmail App Password)
2. Verify port is correct (587 for TLS)
3. Send test email to see error message
4. Check `/admin/email-logs` for error details

### No Data in Report?
1. Verify sales and repairs exist in system
2. Check sales are marked as PAID/PARTIAL
3. Check repairs are completed and paid
4. Verify payment date matches report period

### Enable/Disable Reporting
- Go to `/admin/email-settings`
- Click Enable/Disable toggle button
- Reports won't send until enabled

## Configuration Examples

### Gmail (Recommended)
```
SMTP Server: smtp.gmail.com  
Port: 587
TLS: ✓ Enabled
Password: Use App Password
(Generate at https://myaccount.google.com/apppasswords)
```

### Office 365
```
SMTP Server: smtp.office365.com
Port: 587  
TLS: ✓ Enabled
Password: Office 365 password
```

### SendGrid
```
SMTP Server: smtp.sendgrid.net
Port: 587
TLS: ✓ Enabled
Email: apikey
Password: SG.your_key_here...
```

## Report Frequency

- **Daily**: Sends every day at specified time
- **Every 3 Days**: Sends every 3rd day at specified time
- **Weekly**: Sends every 7 days at specified time

Change frequency anytime in email settings.

## What's Included?

### Features (Already Built)
- ✅ Secure SMTP configuration storage
- ✅ Password encryption
- ✅ Background scheduler
- ✅ Excel report generation
- ✅ Mobile-friendly email HTML
- ✅ Payment-based revenue calculation
- ✅ Admin configuration panel
- ✅ Email send logs & history
- ✅ Error tracking and messages

### Admin Interface
- ✅ `/admin/email-settings` - Configure and test
- ✅ `/admin/email-logs` - View send history
- ✅ `/admin/email-logs/<id>` - View detailed log

## API Endpoints

### Admin Routes (Protected)
```
GET  /admin/email-settings        - Configuration page
POST /admin/email-settings        - Save config or test
GET  /admin/email-logs            - View all logs
GET  /admin/email-logs/<id>       - View log details
GET  /admin/email-test-data       - JSON test data
```

## Revenue Calculation

**Key Rule**: Revenue = Money Actually Received Only

### Included
- Sales with PAID or PARTIAL status
- With SalePayment records within date period
- Repairs completed with deposit or full payment
- Using actual payment amounts (not sale totals)

### Excluded
- Pending/draft sales
- Voided transactions
- Unpaid/credit sales
- Cancelled repairs
- Waived charges

## Questions?

See [AUTOMATED_EMAIL_SYSTEM.md](AUTOMATED_EMAIL_SYSTEM.md) for detailed documentation.

---

**Last Updated**: February 25, 2026
