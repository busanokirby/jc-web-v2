# JC Icons Management System - Installation & Update Guide

**Last Updated:** February 13, 2026  
**Version:** 2.1.0

---

## 📋 Table of Contents

1. [New Computer Setup](#new-computer-setup)
2. [Update Existing System](#update-existing-system)
3. [When Do I Need Migrations](#when-do-i-need-migrations)
4. [Troubleshooting](#troubleshooting)

---

# 🆕 New Computer Setup

## Prerequisites

Install these first:
- **Python 3.8+**: https://www.python.org/downloads/
- **Git**: https://git-scm.com/download/win

## Step-by-Step Installation

### Step 1: Clone Repository

```powershell
# Open PowerShell and run:
git clone https://github.com/user/jc-icons-management-system-v2.git
cd jc-icons-management-system-v2
```

### Step 2: Create Virtual Environment

```powershell
python -m venv web2
```

### Step 3: Activate Environment

```powershell
.\web2\Scripts\Activate
```

You should see `(web2)` in your prompt.

### Step 4: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 5: Set Environment Variable

```powershell
$env:SECRET_KEY='dev-key-migration'
```

### Step 6: Run Migrations (Best Practice)

Even though not technically required on fresh install, run these for consistency:

```powershell
python ./scripts/migrate_add_created_by_user_id.py
python ./scripts/migrate_add_technician_tracking.py
```

**Expected output:**
```
✓ Column 'created_by_user_id' added to customer table
✓ Added created_by_user_id
✓ Added technician_name_override

Migration completed successfully!
```

### Step 7: Start Application

```powershell
python run.py
```

**Expected output:**
```
[2026-02-13 15:30:00,123] INFO in __init__: JC Icons Management System startup
 * Running on http://localhost:5000
```

### Step 8: Access Application

Open browser: `http://localhost:5000`

**Default credentials:**
- Username: `admin`
- Password: `admin123`

---

# 🔄 Update Existing System

## Before You Start

**⚠️ CRITICAL: Backup your data first!**

```powershell
# Backup your database
Copy-Item instance\jc_icons.db instance\jc_icons.db.backup
```

## Update Steps

### Step 1: Navigate to Project

```powershell
cd F:\jc-icons-management-system-v2
```

### Step 2: Activate Environment

```powershell
.\web2\Scripts\Activate
```

### Step 3: Pull Latest Code

```powershell
git pull origin main
```

**Example output:**
```
Updating abc1234..def5678
Fast-forward
 app/blueprints/customers/routes.py  |  50 ++
 scripts/migrate_*.py                |  120 ++
 ...
```

### Step 4: Install/Update Dependencies

```powershell
pip install -r requirements.txt
```

### Step 5: Set Environment Variable

```powershell
$env:SECRET_KEY='dev-key-migration'
```

### Step 6: Run Migrations

**Migration 1 - Customer Creator Tracking:**
```powershell
python ./scripts/migrate_add_created_by_user_id.py
```

**Expected output:**
```
Migration: Add created_by_user_id to customer table
✓ Column 'created_by_user_id' added to customer table
Migration completed successfully!
```

**Migration 2 - Technician Tracking:**
```powershell
python ./scripts/migrate_add_technician_tracking.py
```

**Expected output:**
```
Migration: Add technician tracking columns to device table
  ✓ Added created_by_user_id
  ✓ Added technician_name_override
Migration completed successfully!
```

### Step 7: Restart Application

```powershell
python run.py
```

### Step 8: Verify Update

Go to Admin → Settings and verify:
- ✅ `TECH_CAN_VIEW_DETAILS` toggle exists
- ✅ Feature flags visible

---

# ❓ When Do I Need Migrations?

## Migration Decision Tree

```
Do you have existing data?
├─ YES (Updating old system)
│  └─ RUN MIGRATIONS
│     └─ Updates existing tables safely
│     └─ Preserves all your data
│
└─ NO (Fresh installation)
   └─ MIGRATIONS NOT REQUIRED
      └─ But safe to run anyway
      └─ Recommended for consistency
```

---

## Detailed Scenarios

### Scenario 1: Fresh Install on New Computer
**Migration needed?** ❌ NO (technically)  
**Should you run them?** ✅ YES (best practice)

```powershell
# Database is brand new
# SQLAlchemy creates tables with all new columns
# But run migrations anyway for safety
python ./scripts/migrate_add_created_by_user_id.py
python ./scripts/migrate_add_technician_tracking.py
```

### Scenario 2: Update Existing System
**Migration needed?** ✅ YES (required)  
**Why?** Existing tables need new columns

```powershell
# MUST run migrations
# Database already has data
# Need to add new columns without losing data
git pull origin main
python ./scripts/migrate_add_created_by_user_id.py
python ./scripts/migrate_add_technician_tracking.py
```

### Scenario 3: Clone on New Computer in 1 Year
**Migration needed?** ❌ NO  
**Why?** New database includes all features

```powershell
# Fresh clone years later
# Latest code has new features built-in
# Database created with all columns from start
# Migrations can be skipped (but safe to run)
```

---

## What Each Migration Does

### migrate_add_created_by_user_id.py

```sql
ALTER TABLE customer ADD COLUMN created_by_user_id INTEGER;
ALTER TABLE device ADD COLUMN created_by_user_id INTEGER;
```

**Purpose:**
- Tracks which user created each customer
- Tracks which user created each repair ticket
- Enables role-based access control for TECH users

**Data Impact:**
- ✅ Existing data preserved
- ✅ New column has NULL values (safe)
- ✅ Can be populated going forward

### migrate_add_technician_tracking.py

```sql
ALTER TABLE device ADD COLUMN technician_name_override VARCHAR(100);
```

**Purpose:**
- Allows manual override of technician name
- Enables multi-tech workflow
- Displays on print tickets

**Data Impact:**
- ✅ Existing data preserved
- ✅ New column starts empty
- ✅ Populated on new repairs

---

# 🔧 Troubleshooting

## Migration Shows "Column Already Exists"

**This is fine!** It means:
- ✅ Migration detected column exists
- ✅ Skipped adding it (no error)
- ✅ Your system is already updated

**No action needed.**

## "Can't find foreign key" Error

**Cause:** Foreign key mismatch  
**Solution:**

```powershell
# Backup first
Copy-Item instance\jc_icons.db instance\jc_icons.db.backup

# Delete old database
Remove-Item instance\jc_icons.db

# Restart app (creates fresh database)
python run.py
```

## Python Not Found

**Solution:**
1. Install Python: https://www.python.org/downloads/
2. Check "Add Python to PATH" during installation
3. Restart PowerShell
4. Verify: `python --version`

## Virtual Environment Won't Activate

**Try:**
```powershell
# Use full path
& ".\web2\Scripts\Activate.ps1"

# Or use older method
. .\web2\Scripts\activate
```

## "no such column" Error When Running App

**Cause:** Old database schema  
**Solution:**

```powershell
# Option 1: Run migrations
$env:SECRET_KEY='dev-key-migration'
python ./scripts/migrate_add_created_by_user_id.py
python ./scripts/migrate_add_technician_tracking.py

# Option 2: Delete and recreate database
Remove-Item instance\jc_icons.db
python run.py
```

## Port 5000 Already in Use

**Solution:**
```powershell
# Use different port
$env:FLASK_PORT=5001
python run.py
```

Then access: `http://localhost:5001`

---

## Verify Installation Complete

Run this to confirm all updates:

```powershell
$env:SECRET_KEY='test'
python -c "
from app import create_app
from app.extensions import db

app = create_app({'TESTING': True})
with app.app_context():
    inspector = db.inspect(db.engine)
    
    customer_cols = [c['name'] for c in inspector.get_columns('customer')]
    device_cols = [c['name'] for c in inspector.get_columns('device')]
    
    checks = {
        'created_by_user_id in customer': 'created_by_user_id' in customer_cols,
        'created_by_user_id in device': 'created_by_user_id' in device_cols,
        'technician_name_override': 'technician_name_override' in device_cols,
    }
    
    for check, result in checks.items():
        print(f'✓ {check}: {result}')
    
    all_good = all(checks.values())
    print(f'\nAll checks passed: {all_good}')
"
```

**Expected output:**
```
✓ created_by_user_id in customer: True
✓ created_by_user_id in device: True
✓ technician_name_override: True

All checks passed: True
```

---

## Need Help?

1. ✅ Check this guide for your scenario
2. ✅ Review troubleshooting section
3. ✅ Check error messages carefully
4. ✅ Review MIGRATION_GUIDE.md for detailed info
5. ✅ Check application logs

---

# 📌 Quick Reference

## New Computer
```
git clone <url>
cd jc-icons-management-system-v2
python -m venv web2
.\web2\Scripts\Activate
pip install -r requirements.txt
$env:SECRET_KEY='dev-key-migration'
python ./scripts/migrate_add_created_by_user_id.py
python ./scripts/migrate_add_technician_tracking.py
python run.py
```

## Existing System Update
```
git pull origin main
pip install -r requirements.txt
$env:SECRET_KEY='dev-key-migration'
python ./scripts/migrate_add_created_by_user_id.py
python ./scripts/migrate_add_technician_tracking.py
python run.py
```

## Verify Installation
```
$env:SECRET_KEY='test'
python -c "from app import create_app; app = create_app({'TESTING': True}); print('✅ System ready!')"
```

---

**End of Installation & Update Guide**
