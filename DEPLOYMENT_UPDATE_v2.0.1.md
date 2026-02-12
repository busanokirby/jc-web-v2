# JC Icons Management System - Update to v2.0.1
## Template & Security Update - Multiple Service Types + Secure Password Change

**Release Date:** February 12, 2026
**Version:** 2.0.1
**Previous Version:** 2.0.0

---

## Overview

Version 2.0.1 introduces two important updates:

### 1. Multiple Service Request Types
The Service Request form now supports **multiple service types** instead of a single selection. This allows technicians to document all services that will be performed on a device in one repair ticket.

### 2. Secure Password Change for Users
All users can now securely change their passwords with automatic strength validation. Passwords must meet security requirements including minimum length, uppercase/lowercase letters, and numbers.

### Changes Made:
- ✅ Updated add repair form to use **checkboxes** for service types (multiple selection)
- ✅ Added **8 service type options** for flexibility
- ✅ Updated print ticket template to display **all selected services**
- ✅ Backend updated to **store multiple service types** as comma-separated values
- ✅ Added **secure password change** feature for all users
- ✅ Real-time password strength validation with visual indicator
- ✅ Password requirements checklist (length, case, numbers)
- ✅ No database schema changes required

---

## What's New

### Service Types (Repairs Module)

The form now offers these service types (select all that apply):

1. **Diagnostics** - Device testing and troubleshooting
2. **Hardware Repair** - Physical component repairs
3. **Software Repair** - Software/application fixes
4. **OS Installation/Reinstallation** - Operating system setup
5. **Virus Removal** - Malware/virus removal
6. **Data Backup/Recovery** - Data management services
7. **Upgrade (RAM/SSD)** - Hardware component upgrades
8. **Maintenance/Cleaning** - Preventive maintenance

**Example:** A device might have "Diagnostics, Hardware Repair, Virus Removal" all selected in one ticket.

### Password Change (Users Module)

**Users can now access password change from:** User dropdown menu → "Change Password"

**Features:**
- Current password verification for security
- Real-time password strength indicator
- Visual requirements checklist:
  - ✓ At least 8 characters
  - ✓ At least one uppercase letter
  - ✓ At least one lowercase letter
  - ✓ At least one number (0-9)
- Password confirmation field
- Prevention of password reuse (can't use same password)
- Secure password hashing with werkzeug

---

## Installation Instructions for Remote Store Computers

### Prerequisites
- Git installed on the computer
- Python 3.8+ installed
- Access to the repository


### Step 1: Backup Current System

```powershell
# Open PowerShell in the jc-icons-management-system-v2 directory
cd C:\path\to\jc-icons-management-system-v2

# Create a backup of the database
Copy-Item .\instance\app.db .\instance\app.db.backup.v2.0.0

# Create a backup of the entire project directory
Copy-Item . -Recurse -Destination "..\jc-icons-management-system-v2.backup.v2.0.0" -Force
```

### Step 2: Pull Latest Changes from Repository

```powershell
# Navigate to project directory
cd C:\path\to\jc-icons-management-system-v2

# Add/update remote if needed (only if it's a new setup)
git remote add origin <repository-url>  # Replace with actual repo URL

# Fetch latest changes
git fetch origin

# Check out the v2.0.1 tag
git checkout v2.0.1
```

### Step 3: Activate Virtual Environment

```powershell
# Activate the virtual environment
.\web2\Scripts\Activate.ps1

# Verify activation (should show (web2) in prompt)
```

### Step 4: Restart Flask Application

**Option A: If running as a service/background process**

```powershell
# Stop the current Flask application
Stop-Process -Name "python" -ErrorAction SilentlyContinue

# Remove old Python processes
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# Wait a moment
Start-Sleep -Seconds 3

# Restart the Flask app
python run.py

# Or if using the task runner
# Run the "Run Flask App" task in VS Code
```

**Option B: If using Docker**

```powershell
# Rebuild the Docker image
docker-compose down
docker-compose up --build -d
```

### Step 5: Verify Update

**Test Service Request Types (Repairs):**
1. Open the application in a web browser
2. Navigate to **Repairs → Create New Repair Ticket**
3. Scroll to **"Service Request"** section
4. Verify that **checkboxes** are displayed instead of radio buttons
5. Test selecting **multiple service types** at once
6. Create a test ticket and verify the print preview shows all selected services

**Test Password Change (Users):**
1. Click user dropdown in top-right corner
2. Verify **"Change Password"** option appears
3. Click "Change Password"
4. Verify password change form displays with:
   - Requirements checklist
   - Password strength indicator
   - Show/hide password toggles
5. Test form validations:
   - Try submitting without current password (should error)
   - Try weak password < 8 chars (should error)
   - Try password without uppercase (should error)
   - Try password without numbers (should error)
   - Try non-matching confirm password (should show error)
6. Enter valid password meeting all requirements
7. Verify success message and redirect to dashboard

### Step 6: Test Print Ticket

1. Create a test repair ticket with multiple service types selected
2. Click **"Create Repair Ticket & Print Form"**
3. In the Print Ticket page, verify:
   - All selected service types have **checkmarks (✓)**
   - Unselected services are **blank**
   - Layout is clean and printable

---

## Rollback Instructions

If you encounter any issues, follow these steps to revert to v2.0.0:

```powershell
cd C:\path\to\jc-icons-management-system-v2

# Stop the application
Stop-Process -Name python -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

# Check out the previous version
git checkout v2.0.0

# Activate virtual environment
.\web2\Scripts\Activate.ps1

# Restart the application
python run.py
```

**Database Rollback (if needed):**
```powershell
# Delete current database
Remove-Item .\instance\app.db -Force

# Restore from backup
Copy-Item .\instance\app.db.backup.v2.0.0 .\instance\app.db -Force
```

---

## Important Notes

### Database Compatibility
- ✅ **No database migrations required**
- Service types are stored as **comma-separated strings** in the existing `service_type` field
- Existing repair records remain compatible with the new format

### File Changes Summary
The following files were modified in v2.0.1:

**Repairs Module (Multiple Service Types):**
1. **`templates/repairs/add_repairs.html`**
   - Changed service selection from radio buttons → checkboxes
   - Added 8 service type options
   - Updated labels and help text

2. **`templates/repairs/print_ticket.html`**
   - Updated print template to display all selected services
   - Added logic to check multiple service types

3. **`app/blueprints/repairs/routes.py`**
   - Updated `add_repair()` function to handle multiple selections
   - Uses `request.form.getlist()` instead of `request.form.get()`
   - Joins multiple selections with commas

**Users Module (Secure Password Change):**
4. **`templates/users/change_password.html`** (NEW FILE)
   - New password change form with real-time validation
   - Password strength indicator with visual feedback
   - Requirements checklist for security
   - Show/hide password toggle buttons
   - Mobile-responsive design

5. **`app/blueprints/users/routes.py`**
   - New route: `/users/change-password` (GET/POST methods)
   - Validates current password before allowing change
   - Enforces password strength requirements
   - Prevents password reuse
   - Secure password hashing with werkzeug

6. **`templates/layouts/base.html`**
   - Added "Change Password" link in user dropdown menu
   - Added visual divider before logout button

### Data Format Example

**Service Types:**
```
Old Format (v2.0.0): "Repair"
New Format (v2.0.1): "Diagnostics, Hardware Repair, Virus Removal"
```

---

## Testing Checklist

After installation, verify these items:

**Repairs Module:**
- [ ] Web application starts without errors
- [ ] Login works normally
- [ ] Repairs section loads
- [ ] Service types appear as checkboxes (not radio buttons)
- [ ] Can select multiple service types
- [ ] Can select only one service type
- [ ] Create repair ticket without error
- [ ] Print ticket shows all selected services correctly
- [ ] Existing repair records still display properly
- [ ] Database file size is normal (no unexpected growth)

**Users Module (Password Change):**
- [ ] User dropdown menu is visible in top-right corner
- [ ] "Change Password" option appears in dropdown
- [ ] Password change form displays correctly with all fields
- [ ] Password strength indicator shows in real-time
- [ ] Requirements checklist updates as user types
- [ ] Show/hide password toggles work correctly
- [ ] Incorrect current password shows error message
- [ ] Weak password (< 8 chars) shows error
- [ ] Password without uppercase shows error
- [ ] Password without numbers shows error
- [ ] Non-matching passwords show error message
- [ ] Strong password can be submitted successfully
- [ ] User is redirected to dashboard after successful change
- [ ] New password works on next login

---

## Troubleshooting

### Issue: Service types show as radio buttons (old format)

**Solution:** Browser cache issue
```powershell
# Clear browser cache (or open in Private/Incognito mode)
# Hard refresh page (Ctrl+Shift+R or Cmd+Shift+R)
```

### Issue: Application won't start after update

**Solution:** Check error logs
```powershell
# Check for Python errors
python -m py_compile app/blueprints/repairs/routes.py

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Print ticket doesn't show selected services

**Solution:** Verify print_ticket.html was updated
```powershell
# Check file was updated
git diff v2.0.0 v2.0.1 -- templates/repairs/print_ticket.html

# If not updated, manually pull again
git checkout v2.0.1 -- templates/repairs/print_ticket.html
```

### Issue: "Change Password" link doesn't appear in user dropdown

**Solution:** Browser cache or template not updated
```powershell
# Clear browser cache
# Hard refresh page (Ctrl+Shift+R)

# Verify templates were updated
git diff v2.0.0 v2.0.1 -- templates/layouts/base.html
git checkout v2.0.1 -- templates/layouts/base.html
```

### Issue: Password change form shows error on submit

**Solution:** Check routes.py was updated correctly
```powershell
# Verify routes file includes password validation imports
git diff v2.0.0 v2.0.1 -- app/blueprints/users/routes.py

# Check for Python syntax errors
python -m py_compile app/blueprints/users/routes.py

# Restart Flask application
Stop-Process -Name python -ErrorAction SilentlyContinue
python run.py
```

### Issue: Password strength indicator not working

**Solution:** JavaScript not loaded or form not rendering correctly
```powershell
# Open browser developer console (F12)
# Check for JavaScript errors
# Clear browser cache and refresh page
# Verify change_password.html file exists
git ls-files | findstr "change_password"
```

---

## Support & Questions

If you encounter issues during the update:

1. Check the troubleshooting section above
2. Review the git log for changes: `git log --oneline v2.0.0..v2.0.1`
3. Compare current and previous versions: `git diff v2.0.0 v2.0.1`
4. Restore from backup and contact support if issues persist

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.1 | Feb 12, 2026 | Multiple service types support, template update |
| 2.0.0 | Feb 12, 2026 | Initial baseline version |

---

## Installation Time Estimate
- **Backup:** 2-3 minutes
- **Git pull & checkout:** 1-2 minutes
- **Flask restart:** 30 seconds
- **Verification:** 3-5 minutes
- **Total:** ~6-10 minutes

---

**Note:** No downtime required if using proper backup procedures. The application can be restarted immediately after git checkout.
