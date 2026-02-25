# JC Icons Management System - Migration Guide

**Version:** 2.1.0  
**Date:** February 12, 2026

---

## What's New in This Version

### ✨ New Features

1. **TECH User Customer Management**
   - TECH users can now view and manage customers they created or have repairs for
   - Access controlled by `TECH_CAN_VIEW_DETAILS` feature flag (Admin Settings)
   - Prevents TECH users from seeing all customers (privacy & security)

2. **Technician Tracking**
   - System automatically assigns the creating technician to each repair ticket
   - Manual override option if another technician handles the repair
   - Technician name displays on print tickets above "TECHNICIAN IN CHARGE"

3. **Customer Creator Tracking**
   - System tracks which user created each customer
   - Enables role-based customer visibility
   - Supports multi-technician workflow

### 🗄️ Database Changes

Three new columns added:

| Table | Column | Type | Purpose |
|-------|--------|------|---------|
| `customer` | `created_by_user_id` | INTEGER | Track customer creator |
| `device` | `created_by_user_id` | INTEGER | Track repair ticket creator |
| `device` | `technician_name_override` | VARCHAR(100) | Manual technician name override |

---

## Prerequisites

### System Requirements
- **Python:** 3.8 or higher
- **Git:** Latest version
- **Database:** SQLite (default) or compatible database

### Software to Install (on new computer)
```
Git: https://git-scm.com/download/win
Python 3.8+: https://www.python.org/downloads/
```

---

## Migration Steps

### Step 1: Backup Existing Data

**Windows PowerShell:**
```powershell
# Backup current database
Copy-Item instance\jc_icons.db instance\jc_icons.db.backup

# Backup entire project (optional)
Copy-Item . -Destination ../jc-icons-backup -Recurse
```

### Step 2: Pull Latest Changes

```powershell
cd F:\jc-icons-management-system-v2
git pull origin main
```

**Expected output:**
```
Updating abc1234..def5678
Fast-forward
 app/blueprints/customers/routes.py  |  50 ++
 app/blueprints/repairs/routes.py    |   5 ++
 app/models/customer.py              |   2 ++
 app/models/repair.py                |   3 ++
 templates/repairs/add_repairs.html  |  10 ++
 templates/repairs/print_ticket.html |   8 ++
 scripts/migrate_*.py                |  60 ++
 ...
```

### Step 3: Activate Virtual Environment

```powershell
.\web2\Scripts\Activate
```

Should see `(web2)` in prompt.

### Step 4: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 5: Run Database Migrations

**Set temporary environment variable:**
```powershell
$env:SECRET_KEY='040d2ab9d20105f4d5d72709a8cd398a43672712fc5aa1c8816508fa0dabe961'
```

**Run individual migration scripts (existing method):**

> ⚠️ **Important:**
> 
> * version 2.1.0 introduced a new `company` column on the `users` table.  If
>   you are upgrading from a release earlier than 2.1.0 you either need to run
>   the script below or simply start the application with the updated code;
>   the startup routine now applies this change automatically.
> * version 2.2.0 added a `deposit_paid_at` timestamp to `device`.  the same
>   auto‑migration runs on startup; for manual migration use
>   `python ./scripts/apply_deposit_paid_at.py`.


```powershell
python ./scripts/migrate_add_created_by_user_id.py
python ./scripts/migrate_add_technician_tracking.py
python ./scripts/migrate_add_is_archived_to_device.py
python ./scripts/migrate_add_claim_to_sale.py
python ./scripts/migrate_add_claim_and_waived_to_device.py
python ./scripts/migrate_add_technician_tracking.py
# NEW: add `company` field to users
python ./scripts/migrate_add_company_to_user.py- python ./scripts/apply_deposit_paid_at.py   # add deposit_paid_at column to device
```

**Or — run *all* migration scripts with the new runner (recommended):**

The automatic runner also includes the new `company` column migration.
```powershell
# List what will run without applying
python ./scripts/run_migrations.py --dry-run

# Run all idempotent migration scripts in scripts/ (sorted order)
python ./scripts/run_migrations.py

# Non-interactive (CI/CD or scripted) - skip confirmation
python ./scripts/run_migrations.py --yes
```

**What the runner does:**
- Discovers `scripts/migrate_*.py` and executes them in sorted order.
- Passes through your environment (useful for DATABASE_URL / SECRET_KEY).
- Sets a temporary `SECRET_KEY` if not present (for scripts that call create_app()).

**Expected results (same as above):**
```
Migration: Add created_by_user_id to customer table
--------------------------------------------------
✓ Column 'created_by_user_id' added to customer table
✓ All existing customers will have NULL for created_by_user_id

Migration completed successfully!


Migration: Add technician tracking columns to device table
----------------------------------------------------------
Adding columns to device table: created_by_user_id, technician_name_override
  ✓ Added created_by_user_id
  ✓ Added technician_name_override

Migration completed successfully!
```

**CI recommendation:** add a step to run `python ./scripts/run_migrations.py --yes` before deploying the new release.

### Step 6: Restart Application

```powershell
python run.py
```

**Expected output:**
```
[2026-02-12 22:00:00,123] INFO in __init__: JC Icons Management System startup
 * Running on http://localhost:5000
```

Access at: `http://localhost:5000`

---

## Post-Migration Verification

### 1. Login & Check Admin Settings

- Login with default: **admin** / **admin123**
- Go to **Settings** (gear icon)
- Verify `TECH_CAN_VIEW_DETAILS` toggle is visible

### 2. Test TECH User Access

**Create a test repair ticket:**
1. Go to Repairs → Add Repair
2. Fill in form with:
   - Customer phone: **555-0001** (new customer)
   - Customer name: **Test Customer**
   - Device type: **Laptop**
   - Issue: **Test issue**
3. Leave **Technician in Charge** empty (auto-filled)
4. Click "Create Repair Ticket"

**Verify technician assignment:**
1. Go to Repairs → View ticket
2. Click "Print Form"
3. Check technician name appears above "TECHNICIAN IN CHARGE"

### 3. Test Feature Flag

**Disable TECH access:**
1. Admin → Settings
2. Toggle `TECH_CAN_VIEW_DETAILS` = **OFF**
3. Create TECH user (Users → Create User, role=TECH)
4. Login as TECH
5. Try accessing Customers → Should see 403 Access Denied

**Enable TECH access:**
1. Admin → Settings
2. Toggle `TECH_CAN_VIEW_DETAILS` = **ON**
3. Refresh browser as TECH user
4. Access Customers → Should show filtered customers

### 4. Verify Existing Data

**Check existing customers:**
```powershell
# Open Python shell
python

# Inside Python:
import os
os.environ['SECRET_KEY'] = 'test'
from app import create_app
from app.models.customer import Customer

app = create_app({'TESTING': True})
with app.app_context():
    count = Customer.query.count()
    for c in Customer.query.limit(3).all():
        print(f"- {c.name} (created_by_user_id: {c.created_by_user_id})")
    print(f"Total customers: {count}")
```

**Expected output:**
```
- John Doe (created_by_user_id: None)
- Jane Smith (created_by_user_id: None)
- ABC Company (created_by_user_id: None)
Total customers: 8
```

---

## Configuration Changes

### Environment Variables

If not already set, create `.env` file at project root:

```
SECRET_KEY=your-secret-key-here-change-to-random
FLASK_ENV=development
FLASK_DEBUG=False
```

### Settings to Check

In **Admin Settings** page:

| Setting | Default | Description |
|---------|---------|-------------|
| `POS_ENABLED` | true | Enable/disable POS module |
| `SALES_CAN_EDIT_INVENTORY` | true | Allow SALES to edit inventory |
| `TECH_CAN_VIEW_DETAILS` | true | Allow TECH to view customers |

---

## Troubleshooting

### Migration Fails with "no such column"

**Cause:** Old database schema  
**Solution:**
```powershell
# Check if columns exist
$env:SECRET_KEY='dev-key'
python -c "
from app import create_app
from app.extensions import db

app = create_app({'TESTING': True})
with app.app_context():
    inspector = db.inspect(db.engine)
    cols = [c['name'] for c in inspector.get_columns('customer')]
    print('Customer columns:', cols)
"
```

### "Can't find foreign key" Error

**Cause:** Foreign key mismatch  
**Solution:**
1. Backup database
2. Delete `instance/jc_icons.db`
3. Restart app (recreates schema)
4. Re-import data if needed

### TECH User Can't See Customers

**Check:**
1. Admin → Settings → `TECH_CAN_VIEW_DETAILS` = ON
2. TECH user has `role = 'TECH'` in database
3. Customer has `created_by_user_id` OR device has `customer_id` linked

**Debug:**
```powershell
$env:SECRET_KEY='dev-key'
python -c "
from app import create_app
from app.models.user import User
from app.models.settings import Setting
from app.services.feature_flags import is_tech_can_view_details

app = create_app({'TESTING': True})
with app.app_context():
    tech = User.query.filter_by(role='TECH').first()
    flag = is_tech_can_view_details()
    print(f'TECH user exists: {tech is not None}')
    print(f'TECH_CAN_VIEW_DETAILS flag: {flag}')
"
```

### Print Ticket Shows Blank Technician

**Cause:** Device has no `created_by_user_id` and no `technician_name_override`  
**Solution:**
1. Edit repair ticket
2. Update status to re-save
3. Print again

---

## Rollback Instructions

If you need to revert to previous version:

### Step 1: Restore Database Backup
```powershell
Copy-Item instance\jc_icons.db instance\jc_icons.db.new
Copy-Item instance\jc_icons.db.backup instance\jc_icons.db
```

### Step 2: Check Out Previous Version
```powershell
git log --oneline | head -5  # Find previous commit
git checkout <previous-commit-hash>
```

### Step 3: Restart Application
```powershell
python run.py
```

---

## Migration on New Computer

To set up latest version on a new Windows computer:

### Quick Start
```powershell
# 1. Clone repository
git clone https://github.com/user/jc-icons-management-system-v2.git
cd jc-icons-management-system-v2

# 2. Create and activate virtual environment
python -m venv web2
.\web2\Scripts\Activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment
$env:SECRET_KEY='dev-key-migration'

# 5. Run migrations
python ./scripts/migrate_add_created_by_user_id.py
python ./scripts/migrate_add_technician_tracking.py

# 6. Start app
python run.py
```

Access: `http://localhost:5000`  
Login: **admin** / **admin123**

---

## After Migration - Best Practices

### For Administrators

1. **Review Settings:**
   - Go to Admin Settings
   - Check all feature flags are set correctly
   - Document any custom configurations

2. **Create TECH Users:**
   - Users → Create User
   - Set role = TECH
   - TECH users see only their customers

3. **Monitor Access:**
   - Verify TECH users can access customers
   - Check print tickets show correct technician

### For TECH Users

1. **First Steps:**
   - Create a test repair ticket
   - Verify name appears as technician
   - Print and verify ticket format

2. **Day-to-Day:**
   - Add repairs creates customers automatically
   - View customers via Customers menu
   - Edit customer info as needed
   - Override technician if another tech handles repair

---

## Support & Issues

### Common Questions

**Q: Where are my existing customers?**  
A: All existing customers are preserved. They have `created_by_user_id = NULL`, meaning they're visible to ADMIN and SALES but only to TECH if a repair exists.

**Q: Can I disable TECH customer access?**  
A: Yes. In Admin Settings, toggle `TECH_CAN_VIEW_DETAILS` = OFF.

**Q: What happens if I delete a customer?**  
A: Only ADMIN can delete. Operation cascades to delete repairs.

**Q: How do I change who the technician is?**  
A: Edit the repair and update status. Delete and recreate if needed (preserves customer).

### Getting Help

1. Check this guide for troubleshooting section
2. Review logs in browser console
3. Check database directly if needed
4. Contact development team with error details

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 2.1.0 | 2026-02-12 | TECH customer management, technician tracking |
| 2.0.0 | Previous | Previous stable release |

---

**End of Migration Guide**
