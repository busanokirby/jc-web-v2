# Quick Update Script for Remote Store Computers
## v2.0.1 Batch Deployment

Save this file as `UPDATE_v2.0.1.ps1` and run on each store computer.

```powershell
# ============================================================
# JC Icons Management System - v2.0.1 Update Script
# Multiple Service Request Types Support
# ============================================================

Write-Host "======================================" -ForegroundColor Green
Write-Host "JC Icons System Update to v2.0.1" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""

$ProjectPath = "C:\path\to\jc-icons-management-system-v2"  # ← UPDATE THIS PATH
$BackupPath = $ProjectPath + ".backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# ============================================================
# STEP 1: Backup Current System
# ============================================================
Write-Host "[1/5] Creating backup..." -ForegroundColor Cyan

if (Test-Path $ProjectPath) {
    try {
        Copy-Item -Path "$ProjectPath\instance\app.db" `
                  -Destination "$ProjectPath\instance\app.db.backup.v2.0.0" `
                  -Force -ErrorAction Stop
        Write-Host "✓ Database backed up" -ForegroundColor Green
        
        Copy-Item -Path $ProjectPath `
                  -Destination $BackupPath `
                  -Recurse -Force `
                  -Exclude @("web2", ".git", "__pycache__", ".pytest_cache")
        Write-Host "✓ Project backed up to: $BackupPath" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Backup failed: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✗ Project path not found: $ProjectPath" -ForegroundColor Red
    exit 1
}

# ============================================================
# STEP 2: Stop Flask Application
# ============================================================
Write-Host ""
Write-Host "[2/5] Stopping Flask application..." -ForegroundColor Cyan

try {
    # Stop any Python processes
    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host "✓ Flask application stopped" -ForegroundColor Green
    Start-Sleep -Seconds 3
}
catch {
    Write-Host "⚠ Could not stop Flask (may not be running)" -ForegroundColor Yellow
}

# ============================================================
# STEP 3: Update Code from Git
# ============================================================
Write-Host ""
Write-Host "[3/5] Updating code from Git repository..." -ForegroundColor Cyan

try {
    Push-Location $ProjectPath
    
    # Fetch latest changes
    git fetch origin
    Write-Host "✓ Fetched latest changes" -ForegroundColor Green
    
    # Checkout v2.0.1 tag
    git checkout v2.0.1
    Write-Host "✓ Checked out v2.0.1" -ForegroundColor Green
    
    # Verify checkout
    $CurrentTag = git describe --tags --exact-match 2>$null
    Write-Host "✓ Current version: $CurrentTag" -ForegroundColor Green
    
    Pop-Location
}
catch {
    Write-Host "✗ Git update failed: $_" -ForegroundColor Red
    Write-Host "Attempting rollback..." -ForegroundColor Yellow
    try {
        Copy-Item -Path $BackupPath -Destination $ProjectPath -Recurse -Force
        Write-Host "✓ Restored from backup" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Rollback failed! Manual intervention required." -ForegroundColor Red
    }
    exit 1
}

# ============================================================
# STEP 4: Start Flask Application
# ============================================================
Write-Host ""
Write-Host "[4/5] Starting Flask application..." -ForegroundColor Cyan

try {
    Push-Location $ProjectPath
    
    # Activate virtual environment and start Flask
    $ActivateScript = ".\web2\Scripts\Activate.ps1"
    
    if (Test-Path $ActivateScript) {
        & $ActivateScript
        
        # Start Flask in background
        Start-Process python -ArgumentList "run.py" -NoNewWindow
        Write-Host "✓ Flask application started" -ForegroundColor Green
        
        Start-Sleep -Seconds 5
    } else {
        Write-Host "✗ Virtual environment not found at: $ActivateScript" -ForegroundColor Red
        exit 1
    }
    
    Pop-Location
}
catch {
    Write-Host "✗ Failed to start Flask: $_" -ForegroundColor Red
    exit 1
}

# ============================================================
# STEP 5: Verification
# ============================================================
Write-Host ""
Write-Host "[5/5] Verifying installation..." -ForegroundColor Cyan

$maxRetries = 5
$retry = 0
$appRunning = $false

while ($retry -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000" -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            $appRunning = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 2
        $retry++
    }
}

if ($appRunning) {
    Write-Host "✓ Application is running at http://localhost:5000" -ForegroundColor Green
}
else {
    Write-Host "⚠ Could not verify application (may still be starting)" -ForegroundColor Yellow
}

# ============================================================
# Summary
# ============================================================
Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "Update Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "Version: v2.0.1" -ForegroundColor Cyan
Write-Host "Changes:" -ForegroundColor Cyan
Write-Host "  • Multiple service types support" -ForegroundColor Cyan
Write-Host "  • Updated repair forms and templates" -ForegroundColor Cyan
Write-Host "  • No database migration needed" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Open browser and go to http://localhost:5000" -ForegroundColor Cyan
Write-Host "  2. Login to the system" -ForegroundColor Cyan
Write-Host "  3. Go to Repairs → Create New Repair Ticket" -ForegroundColor Cyan
Write-Host "  4. Verify service types are now checkboxes (multiple selection)" -ForegroundColor Cyan
Write-Host "  5. Create a test ticket and verify print preview" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backup Info:" -ForegroundColor Cyan
Write-Host "  DB Backup:      $ProjectPath\instance\app.db.backup.v2.0.0" -ForegroundColor Cyan
Write-Host "  Full Backup:    $BackupPath" -ForegroundColor Cyan
Write-Host ""

# Optional: Open browser
Write-Host "Opening application in browser..." -ForegroundColor Cyan
Start-Sleep -Seconds 3
Start-Process "http://localhost:5000"

Write-Host "✓ Done!" -ForegroundColor Green
```

---

## Usage Instructions

### For Single Computer:

1. Edit the script to set correct path:
   ```powershell
   $ProjectPath = "C:\path\to\jc-icons-management-system-v2"
   ```

2. Run the script:
   ```powershell
   powershell -ExecutionPolicy Bypass -File UPDATE_v2.0.1.ps1
   ```

### For Multiple Computers:

#### Option A: USB/Network Drive Distribution
1. Copy `UPDATE_v2.0.1.ps1` to USB or network location
2. Run on each computer following "For Single Computer" steps

#### Option B: Remote Execution
```powershell
# From main office computer
$computers = @("STORE-PC-01", "STORE-PC-02", "STORE-PC-03")
$scriptPath = "\\network\share\UPDATE_v2.0.1.ps1"

foreach ($computer in $computers) {
    Write-Host "Updating $computer..."
    Invoke-Command -ComputerName $computer -FilePath $scriptPath
}
```

---

## Pre-Update Checklist

Before running the update script:

- [ ] Backup database manually
- [ ] Current application is running
- [ ] Close any active repair tickets/forms
- [ ] Internet connection is stable
- [ ] Administrator access on the computer
- [ ] Sufficient disk space (at least 500MB free)

---

## Troubleshooting

### Script won't run
```powershell
# If ExecutionPolicy blocks script
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser
```

### Can't find project path
```powershell
# Find the correct path
Get-Item "C:\Program Files*\jc-icons*" -Recurse -ErrorAction SilentlyContinue
```

### Flask won't start
```powershell
# Check for port conflicts
netstat -ano | findstr :5000

# Try manual start
cd C:\path\to\jc-icons-management-system-v2
.\web2\Scripts\Activate.ps1
python run.py
```

---

## Support Information

**Update Duration:** 5-10 minutes per computer
**Downtime:** Less than 1 minute
**Rollback:** Automatic backup created (see script output)

Contact support if issues persist after update.
