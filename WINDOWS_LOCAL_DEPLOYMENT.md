# 🖥️ Windows Local Network Deployment Guide

Deploy JC Icons on Windows for your local network (LAN only). Perfect for small office networks.

## System Requirements

- **Windows 10 or Windows 11** (Professional, Enterprise, or Home)
- **Python 3.8+** (download from python.org)
- **8 GB RAM minimum** (16 GB recommended)
- **20 GB free disk space**
- **Network:** Connected to local network (Ethernet or WiFi)

---

## Part 1: Initial Setup (15 minutes)

### Step 1: Install Python

1. Download from: https://www.python.org/downloads/
   - Click "Download Python 3.11.x" (or latest 3.x)

2. **Important:** Check "Add Python to PATH"
   ![python-install-checkbox]

3. Run installer and follow prompts
   - Click "Install Now"
   - Let it install to default location

4. **Verify installation** - Open PowerShell/CMD:
   ```bash
   python --version
   # Should show: Python 3.11.x
   ```

### Step 2: Navigate to Your Project

Your project is already at `F:\jc-icons-management-system-v2`

```bash
# Open PowerShell and navigate to your project
cd F:\jc-icons-management-system-v2
```

### Step 3: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it (Windows PowerShell)
venv\Scripts\Activate.ps1

# If you get an error about execution policy:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Then run the activate command again
```

### Step 4: Install Dependencies

```bash
# Make sure venv is activated (you'll see "(venv)" in prompt)
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Configure Environment

```bash
# Copy template
copy .env.example .env

# Edit the file with Python or any text editor
python -c "import secrets; print(secrets.token_hex(32))" > secret.txt
# Copy the value from secret.txt into .env as SECRET_KEY

# Edit .env
notepad .env
```

**Required values in .env:**
```
SECRET_KEY=<paste-generated-value>
FLASK_ENV=production
FLASK_DEBUG=false
ADMIN_PASSWORD=<choose-strong-password>
```

### Step 6: Initialize Database

```bash
# Create database and tables
python scripts/init_db.py init

# You'll see: "Created default admin user"
```

---

## Part 2: Find Your Network Information (5 minutes)

### Get Your Windows Machine's IP Address

**Method 1: PowerShell (Easiest)**
```bash
# Open PowerShell
ipconfig

# Look for "IPv4 Address" under "Ethernet adapter" or "Wireless LAN adapter"
# Example: 192.168.1.100
```

**Method 2: Settings**
1. Settings → Network & Internet → WiFi (or Ethernet)
2. Click your network name
3. Properties → IPv4 address

**Write this down:**
```
My IP Address: _________________
My Port: 5000

Access URL: http://<my-ip>:5000
Example: http://192.168.1.100:5000
```

### Verify Network Connectivity

```bash
# From another device on the network, test connectivity:
# (Open cmd/PowerShell on another computer)
ping 192.168.1.100

# Should see replies (if successful)
```

---

## Part 3: Windows Firewall Configuration (5 minutes)

**Important:** Configure Windows Firewall to allow the app.

### Method 1: Automatic (via Python)

When you start the app for the first time, Windows will ask:
- Click **"Allow access"** (both Private and Public networks)

### Method 2: Manual Configuration (Windows Defender Firewall)

1. Open **Windows Defender Firewall with Advanced Security**
   - Press `Win + R`
   - Type: `wf.msc`
   - Press Enter

2. Click **"Inbound Rules"** (left sidebar)

3. Click **"New Rule"** (right sidebar)

4. **New Inbound Rule Wizard:**
   - Rule Type: Select **"Port"** → Next
   - Protocol and Ports: 
     - TCP selected ✓
     - Specific local ports: `5000`
     - Click Next
   - Action: **"Allow the connection"** → Next
   - Profile: Check all three:
     - ☑ Domain
     - ☑ Private
     - ☑ Public
     - Click Next
   - Name: `JC Icons App`
   - Finish

5. **Verify the rule was added:**
   - The rule "JC Icons App" should appear in the Inbound Rules list
   - Status should show "Enabled"

---

## Part 4: Start the Application (2 minutes)

### Start the Server

```bash
# Make sure virtual environment is activated
# (You should see "(venv)" in the prompt)

venv\Scripts\Activate.ps1

# Run the application
python run.py

# You should see:
# WARNING in app.run
# Running on http://0.0.0.0:5000
# ... (server is running)
```

### Keep It Running

Leave this PowerShell window open. The application will run as long as this window is open.

**DO NOT close this window** - the app will stop.

---

## Part 5: Access the Application

### From the Same Computer

1. Open your browser (Chrome, Edge, Firefox, Safari)
2. Go to: `http://localhost:5000`
   - OR: `http://127.0.0.1:5000`
3. Login with:
   - Username: `admin`
   - Password: (whatever you set in ADMIN_PASSWORD)

### From Another Device on the Network

1. Find your computer's IP address (see Part 2)
2. On another device on the same network, open browser
3. Go to: `http://192.168.1.100:5000` (use your IP address)
4. Login with the same credentials

**Example:**
```
My Windows Computer IP: 192.168.1.100
On my phone/laptop/tablet:
  Open: http://192.168.1.100:5000
  Login!
```

---

## Part 6: Optional - Create Desktop Shortcut

### For Easy Starting Each Day

1. Create a file called `start-app.bat` in your project folder (F:\jc-icons-management-system-v2):

```batch
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python run.py
pause
```

2. Right-click on `start-app.bat` → "Send to" → Desktop (create shortcut)

3. **To start the app:** Just double-click the shortcut

---

## Part 7: Auto-Start on Computer Boot (Optional)

Run the app automatically every time your Windows computer starts!

### Setup (5 minutes)

**Step 1: Create Startup Script**

Create a file called `start-app-hidden.vbs` in your project folder (F:\jc-icons-management-system-v2):

```vbscript
' Save this as: start-app-hidden.vbs
' This runs the app silently without a visible window

Set objFSO = CreateObject("Scripting.FileSystemObject")
strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

Set objShell = CreateObject("WScript.Shell")
objShell.Run "cmd /c cd /d """ & strPath & """ && webv2\Scripts\activate.bat && python run.py", 0, False
```

**Step 2: Create Task Scheduler Task**

1. Press `Win + R`
2. Type: `taskschd.msc`
3. Press Enter (Task Scheduler opens)

4. Click **"Create Basic Task"** (right sidebar)

5. **Name and Description:**
   - Name: `JC Icons Startup`
   - Description: `Starts JC Icons app on boot`
   - Click Next

6. **Trigger:**
   - Select: **"At system startup"**
   - Click Next

7. **Action:**
   - Select: **"Start a program"**
   - Click Next

8. **Start a Program:**
   - Program/script: `cscript.exe`
   - Arguments (add in "Add arguments" field):
     ```
     "F:\jc-icons-management-system-v2\start-app-hidden.vbs"
     ```
   - Click Next

9. **Finish:**
   - Check: ☑ "Open the Properties dialog for this task when I click Finish"
   - Click Finish

10. **Additional Settings (in Properties that opened):**
    - Go to **"General"** tab
    - Check: ☑ "Run whether user is logged in or not"
    - Click "Change User or Group..."
      - Enter: `SYSTEM`
      - Click "Check Names"
      - Click OK
    - Click OK to save

### Verify It Works

1. **Test without rebooting:**
   - In Task Scheduler, right-click your task
   - Click "Run"
   - Check if app starts (you won't see a window, but check from another device)

2. **Final test - Reboot:**
   - Save any work
   - Restart your computer
   - Wait 10 seconds after boot
   - From another device, try: `http://192.168.1.100:5000`
   - App should be accessible!

### ✅ Verify Auto-Start is Working

**Method 1: Check Task Scheduler**
```
- Open Task Scheduler
- Look for "JC Icons Startup" 
- Status should show "Ready"
```

**Method 2: Check from Another Device**
```
- After reboot, wait 15 seconds
- From your phone/tablet/laptop on same network
- Visit: http://192.168.1.100:5000
- If it loads, auto-start is working!
```

### View Running App (Secret Window)

Since the app runs hidden, here's how to see it if needed:

**Option 1: Task Manager**
1. Press `Ctrl + Shift + Esc`
2. Look for: `python.exe` (running)
3. The app is running in the background

**Option 2: Health Check**
```bash
# From PowerShell, check if running:
Invoke-WebRequest http://localhost:5000/health

# Should return: 200 OK
```

### Stop the Auto-Running App

**Method 1: Disable Task Scheduler Task**
1. Open Task Scheduler
2. Right-click "JC Icons Startup"
3. Click "Disable"
4. Restart computer (app won't start)

**Method 2: Quick Stop (from another computer)**
```bash
# From PowerShell on another device:
Invoke-WebRequest http://192.168.1.100:5000/admin/shutdown -Method POST
# (requires admin authentication)
```

**Method 3: Task Manager**
1. Press `Ctrl + Shift + Esc`
2. Find `python.exe`
3. Click "End Task"
4. App stops immediately

### Troubleshooting Auto-Start

**App doesn't start after reboot:**

1. **Check Task Scheduler:**
   - `taskschd.msc`
   - Look for "JC Icons Startup"
   - Status should say "Ready"
   - If "Disabled", right-click and enable it

2. **Check the VBS path:**
   - In Task Scheduler, edit the task
   - Arguments should point to: `"F:\jc-icons-management-system-v2\start-app-hidden.vbs"`

3. **Run with visible window (for debugging):**
   ```
   Replace vbs line:
   objShell.Run "cmd /c ...", 0, False
   
   With:
   objShell.Run "cmd /c ...", 1, False
   ```
   (Changes 0 to 1 to show window)

4. **Check Windows Event Viewer:**
   - Press `Win + R`
   - Type: `eventvwr`
   - Look for errors starting with "Schedule"

**Network access from other devices still doesn't work:**
- Verify firewall rule (Part 3) is still enabled
- Check if app is running: `netstat -ano | findstr :5000`
- Restart Windows Firewall: `netsh advfirewall reset all`

### Advanced: Running as Windows Service

For even more advanced setup, you can run as a Windows Service (app starts before anyone logs in):

```powershell
# Install NSSM (Non-Sucking Service Manager)
choco install nssm

# Create service
nssm install JCIconsService python F:\jc-icons-management-system-v2\run.py

# Start service
nssm start JCIconsService
```

This requires Chocolatey. For most setups, Task Scheduler (above) is simpler.

---

## Part 8: Create Additional Users

### Add Employees/Team Members

```bash
# While app is running, open a new PowerShell window

# Activate virtual environment in new window
cd F:\jc-icons-management-system-v2
venv\Scripts\Activate.ps1

# Create new user
python scripts/init_db.py create-user

# Follow the prompts:
# Username: john
# Full Name: John Doe
# Password: (strong password)
# Role: 2 (SALES) or 3 (TECH)
```

---

## 🔒 Security for Local Network

### ✅ What's Protected

- ✅ Login requires username/password
- ✅ Passwords are encrypted (PBKDF2-SHA256)
- ✅ Only people on your network can access
- ✅ Sessions timeout after 7 days
- ✅ Failed logins are logged
- ✅ Firewall prevents external access

### ⚠️ Limitations (It's Local!)

- ❌ No HTTPS (local network is okay)
- ❌ No external access (that's intentional)
- ⚠️ Only accessible while Windows computer is on

---

## Troubleshooting

### Port 5000 Already in Use

```bash
# Close any other apps using port 5000
# Or use a different port:

# Edit run.py:
# Change: app.run(debug=debug, host=host, port=5000)
# To: app.run(debug=debug, host=host, port=8000)

python run.py
# Now access at: http://192.168.1.100:8000
```

### Can't Access from Another Device

**Check these:**

1. **Firewall Rule Added?**
   - Open `wf.msc`
   - Look for "JC Icons App" rule
   - Should show "Enabled"

2. **Correct IP Address?**
   ```bash
   ipconfig  # Make sure you're using the right IP
   ```

3. **Server Running?**
   - PowerShell window should show "Running on http://0.0.0.0:5000"

4. **Same Network?**
   - Both devices must be on the same WiFi/network
   - Check: Settings → Network → WiFi (same network?)

5. **Try Localhost First**
   - From same computer: http://localhost:5000
   - This proves the app works

### Database Error

```bash
# Reset database (this deletes all data!)
python scripts/init_db.py reset

# Then reinitialize
python scripts/init_db.py init
```

### Virtual Environment Won't Activate

```bash
# Try this command instead:
python -m venv venv --clear
venv\Scripts\Activate.ps1

# If still failing, try Command Prompt instead of PowerShell:
cd F:\jc-icons-management-system-v2
venv\Scripts\activate.bat
python run.py
```

---

## Daily Usage

### Starting the App

```bash
# Open PowerShell
cd F:\jc-icons-management-system-v2
venv\Scripts\Activate.ps1
python run.py

# Leave running!
```

### Stopping the App

- Press `Ctrl + C` in the PowerShell window
- Or close the PowerShell window

### Accessing the App

- **Local**: http://localhost:5000
- **Network**: http://<your-IP>:5000
  - Example: http://192.168.1.100:5000

---

## 📊 Team Access Workflow

### Day 1 Setup

1. You install and run on your Windows computer
2. Share your IP address with team: `192.168.1.100`
3. Team members go to: `http://192.168.1.100:5000`
4. You create login accounts for each person

### Daily Usage

1. **Morning:** Start app on your Windows computer
   ```bash
   python run.py
   ```

2. **Team uses app:** They go to `http://192.168.1.100:5000`

3. **Evening:** Stop app (press Ctrl+C)

4. **Data is saved** in the local database on your computer

---

## Data Backup (Important!)

Your data is stored locally on your Windows computer:

### Location
```
F:\jc-icons-management-system-v2\instance\jc_icons_v2.db
```

### Weekly Backup

**Option 1: Manual Copy**
```bash
# Copy the database file to USB or cloud storage
Copy-Item `
  "F:\jc-icons-management-system-v2\instance\jc_icons_v2.db" `
  "D:\backups\jc_icons_backup_$(Get-Date -Format 'yyyy-MM-dd').db"
```

**Option 2: Automatic Backup Script**

Create `backup.ps1`:
```powershell
$source = "F:\jc-icons-management-system-v2\instance\jc_icons_v2.db"
$dest = "D:\backups\jc_icons_backup_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').db"
Copy-Item $source $dest
Write-Host "Backup created: $dest"
```

Run daily or weekly:
```bash
powershell -ExecutionPolicy Bypass -File backup.ps1
```

---

## Performance Tips

### Faster Performance

1. **Use Ethernet** instead of WiFi (if possible)
   - More stable connection
   - Faster than WiFi

2. **Close Other Apps**
   - Free up RAM
   - Better performance

3. **Keep Database Small**
   - Archive old data periodically
   - Delete old test records

### Monitor Performance

```bash
# While app is running, monitor:
# - CPU usage (Task Manager → Processes)
# - Memory usage (should be < 500 MB)
# - Network (should be idle when not using app)
```

---

## Advanced: Remote Access (VPN)

If you want to access from outside your network:

1. Set up VPN (Tailscale, Wireguard, etc.)
2. Connect to VPN from remote device
3. Access: `http://192.168.1.100:5000` (on VPN)

---

## Security Notes

### ✅ For Local Network

- Passwords are always encrypted
- Failed logins are logged
- Session timeout: 7 days
- Only accessible from your network
- Windows Firewall protects

### 🔐 Best Practices

1. ✅ Use strong admin password
2. ✅ Create individual accounts for each user
3. ✅ Regular backups (weekly minimum)
4. ✅ Keep Windows Firewall enabled
5. ✅ Update Python/packages monthly
6. ✅ Monitor security logs

---

## Common Questions

### Q: Do I need to pay for anything?
**A:** No! Python and the app are both free.

### Q: Can external users access it?
**A:** No, only devices on your local network can access.

### Q: What if my Windows computer restarts?
**A:** You need to manually start the app again, or set up auto-start (Part 7).

### Q: Can I access from my phone?
**A:** Yes! If phone is on the same WiFi network, go to `http://192.168.1.100:5000`

### Q: How many users can use it?
**A:** That depends on your computer specs. Tested with 10+ concurrent users on modern hardware.

### Q: What happens to data when I stop the app?
**A:** Nothing! Data is saved in the database. Stopping the app doesn't delete data.

### Q: Can I use SQLite forever?
**A:** Yes, for small teams it's fine. For >100 users, upgrade to PostgreSQL (see DEPLOYMENT.md).

---

## Part 9: Creating Deployment ZIP for Another Computer

Share the app with another computer? Create a clean ZIP file with only the files needed.

### Files to INCLUDE in ZIP

**Copy these folders/files (keep structure):**

```
jc-icons-management-system-v2.zip
├── app/                          ← INCLUDE (entire folder)
│   ├── __init__.py
│   ├── extensions.py
│   ├── blueprints/
│   ├── models/
│   ├── services/
│   └── (all files)
├── templates/                    ← INCLUDE (entire folder)
├── static/                       ← INCLUDE (entire folder)
├── scripts/                      ← INCLUDE (entire folder)
│   ├── init_db.py
│   └── (all scripts)
├── tests/                        ← INCLUDE (entire folder - optional)
├── run.py                        ← INCLUDE
├── config.py                     ← INCLUDE
├── wsgi.py                       ← INCLUDE
├── requirements.txt              ← INCLUDE (CRITICAL!)
├── .env.example                  ← INCLUDE (CRITICAL!)
├── .gitignore                    ← INCLUDE
├── README.md                     ← INCLUDE
├── WINDOWS_LOCAL_DEPLOYMENT.md  ← INCLUDE (this guide!)
├── SECURITY_QUICK_START.md       ← INCLUDE
├── DEPLOYMENT_CHECKLIST.md       ← INCLUDE
└── (other documentation)
```

### Files to EXCLUDE from ZIP

**Do NOT include these:**

```
❌ venv/                          (virtual environment - 500+ MB!)
❌ web2/                          (old environment - 500+ MB!)
❌ __pycache__/                   (Python cache files)
❌ .git/                          (Git history - not needed)
❌ .env                           (NEVER share! Has secrets)
❌ .env.local                     (local configuration)
❌ .env.prod                      (production config)
❌ instance/jc_icons_v2.db        (database with live data!)
❌ logs/                          (log files)
❌ *.pyc                          (compiled Python files)
❌ .vscode/                       (editor settings)
❌ .pytest_cache/                 (test cache)
❌ patches/                       (optional)
```

### Step-by-Step: Create ZIP

#### Method 1: Windows Explorer (Easiest)

1. Open your project folder: `F:\jc-icons-management-system-v2`

2. **Select files to include** - Use Ctrl+Click to multi-select:
   - ✅ `app/` folder
   - ✅ `templates/` folder
   - ✅ `static/` folder
   - ✅ `scripts/` folder
   - ✅ `tests/` folder (optional)
   - ✅ All `.md` files (README, WINDOWS_LOCAL_DEPLOYMENT, etc.)
   - ✅ `run.py`, `config.py`, `wsgi.py`
   - ✅ `requirements.txt`, `.env.example`, `.gitignore`

3. **Right-click** → "Send to" → "Compressed folder (zipped)"

4. Rename to: `jc-icons-management-system-v2.zip`

#### Method 2: PowerShell (Faster - Works on All Windows Versions)

**Option A: Simple Copy Method** (most reliable)

```powershell
# 1. Create temp folder
mkdir C:\temp-deploy

# 2. Copy only the files we need
Copy-Item 'F:\jc-icons-management-system-v2\app' -Destination 'C:\temp-deploy\app' -Recurse
Copy-Item 'F:\jc-icons-management-system-v2\templates' -Destination 'C:\temp-deploy\templates' -Recurse
Copy-Item 'F:\jc-icons-management-system-v2\static' -Destination 'C:\temp-deploy\static' -Recurse
Copy-Item 'F:\jc-icons-management-system-v2\scripts' -Destination 'C:\temp-deploy\scripts' -Recurse
Copy-Item 'F:\jc-icons-management-system-v2\tests' -Destination 'C:\temp-deploy\tests' -Recurse

# 3. Copy individual files
Copy-Item 'F:\jc-icons-management-system-v2\run.py' -Destination 'C:\temp-deploy\run.py'
Copy-Item 'F:\jc-icons-management-system-v2\config.py' -Destination 'C:\temp-deploy\config.py'
Copy-Item 'F:\jc-icons-management-system-v2\wsgi.py' -Destination 'C:\temp-deploy\wsgi.py'
Copy-Item 'F:\jc-icons-management-system-v2\requirements.txt' -Destination 'C:\temp-deploy\requirements.txt'
Copy-Item 'F:\jc-icons-management-system-v2\.env.example' -Destination 'C:\temp-deploy\.env.example'
Copy-Item 'F:\jc-icons-management-system-v2\.gitignore' -Destination 'C:\temp-deploy\.gitignore'
Copy-Item 'F:\jc-icons-management-system-v2\README.md' -Destination 'C:\temp-deploy\README.md'
Copy-Item 'F:\jc-icons-management-system-v2\WINDOWS_LOCAL_DEPLOYMENT.md' -Destination 'C:\temp-deploy\WINDOWS_LOCAL_DEPLOYMENT.md'
Copy-Item 'F:\jc-icons-management-system-v2\SECURITY_QUICK_START.md' -Destination 'C:\temp-deploy\SECURITY_QUICK_START.md'
Copy-Item 'F:\jc-icons-management-system-v2\DEPLOYMENT_CHECKLIST.md' -Destination 'C:\temp-deploy\DEPLOYMENT_CHECKLIST.md'

# 4. Create ZIP from temp folder
Compress-Archive -Path 'C:\temp-deploy\*' -DestinationPath 'C:\jc-icons-v2-deployment.zip' -Force

# 5. Clean up temp folder
Remove-Item 'C:\temp-deploy' -Recurse -Force

Write-Host "ZIP created: C:\jc-icons-v2-deployment.zip"
```

**Option B: 7-Zip Command** (if you have 7-Zip installed)

```powershell
# Install 7-Zip first (using Chocolatey):
# choco install 7zip

# Then create ZIP:
& "C:\Program Files\7-Zip\7z.exe" a -tzip 'C:\jc-icons-v2-deployment.zip' `
  'F:\jc-icons-management-system-v2\*' `
  -x!venv `
  -x!web2 `
  -x!__pycache__ `
  -x!.git `
  -x!logs `
  -x!instance `
  -x!.vscode `
  -x!.pytest_cache

Write-Host "ZIP created with 7-Zip"
```

#### Method 3: Using Git (If You Have Git)

```bash
# Create archive excluding .git and venv
git archive --format=zip --output=jc-icons-deployment.zip HEAD

# Add any files not in git (like .env.example if needed)
```

### Verify ZIP Contents

Before sharing, verify the ZIP has everything:

```powershell
# List ZIP contents
Expand-Archive -Path 'C:\jc-icons-v2-deployment.zip' -DestinationPath 'C:\temp-check' -Force
ls C:\temp-check

# Check size (should be 2-5 MB, NOT 700+ MB)
(Get-Item 'C:\jc-icons-v2-deployment.zip').Length / 1MB
```

**Correct size:** 2-5 MB  
**Wrong size:** 500+ MB = you included venv or web2!

### Files to Customize on NEW Computer

When deploying to another computer, these files need adjustment:

| File | What to Do |
|------|-----------|
| `.env` | Create new (copy from .env.example + generate new SECRET_KEY) |
| `instance/` | Will be created automatically when app starts |
| `logs/` | Will be created automatically |
| `run.py` | No change needed (uses .env values) |

---

## Deployment Checklist for Another Computer

Once someone extracts your ZIP:

### Their Setup Process

```bash
# 1. Extract ZIP to their F: drive (or wherever they want)
Expand-Archive jc-icons-v2-deployment.zip -DestinationPath F:\

# 2. Go to folder
cd F:\jc-icons-management-system-v2

# 3. Create virtual environment
python -m venv venv
venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 5. Configure
# They need to:
# - Copy .env.example → .env
# - Generate SECRET_KEY (python -c "import secrets; print(secrets.token_hex(32))")
# - Set ADMIN_PASSWORD in .env

# 6. Initialize database
python scripts/init_db.py init

# 7. Run!
python run.py
```

### Quick Validation Checklist

**For the person setting up on new computer:**

- [ ] ZIP extracted successfully
- [ ] Found `venv` folder? (should NOT be in ZIP)
- [ ] Found `.env.example`? (should be in ZIP)
- [ ] Python installed? (`python --version` shows 3.8+)
- [ ] Virtual environment created? (`venv\Scripts\Activate.ps1`)
- [ ] Dependencies installed? (`pip install -r requirements.txt`)
- [ ] `.env` file created from `.env.example`?
- [ ] SECRET_KEY generated and in `.env`?
- [ ] Database initialized? (`python scripts/init_db.py init`)
- [ ] App starts? (`python run.py` shows "Running on...")
- [ ] Firewall configured? (allow port 5000)
- [ ] Accessible from another device? (`http://<their-ip>:5000`)

---

## Size Reference

### Typical ZIP Sizes

| Scenario | Size | Includes |
|----------|------|----------|
| Small ZIP (correct) | 2-5 MB | Source code, templates, static files |
| Medium ZIP | 10-20 MB | Includes database example, some logs |
| Large ZIP (WRONG!) | 500+ MB | Includes `venv/` or `web2/` |
| Huge ZIP (WRONG!) | 1+ GB | Includes `.git/` history |

**If your ZIP is > 50 MB, something is wrong!**

---

## Sharing Tips

### Before Sharing ZIP

- [ ] Remove venv/ (`rmdir /s venv` from F:\jc-icons-management-system-v2)
- [ ] Remove web2/ (delete folder)
- [ ] Delete instance/jc_icons_v2.db (will recreate)
- [ ] Delete logs/ folder (will recreate)
- [ ] ZIP size is < 10 MB
- [ ] Test ZIP on another computer first

### How to Share

**Option 1: USB Drive**
```
USB Stick
└── jc-icons-v2-deployment.zip (copy this)
```

**Option 2: Email** (if < 25 MB)
- Attach ZIP to email
- Person downloads and extracts

**Option 3: Cloud Storage**
- Google Drive: Create link, set "Anyone with link can view"
- OneDrive: Upload, share link
- Dropbox: Create public link

**Option 4: GitHub** (if you want version control)
```bash
git push origin main
# They clone: git clone <your-repo-url>
```

### ZIP Distribution Checklist

- [ ] ZIP file name: `jc-icons-v2-deployment.zip` (clear name)
- [ ] ZIP location documented (where they should extract)
- [ ] Include this guide (WINDOWS_LOCAL_DEPLOYMENT.md in ZIP)
- [ ] Include setup instructions (email or note)
- [ ] Test extraction on test computer first
- [ ] Ask them to confirm IP address once running

---

## What NOT to Share

```
❌ Don't share .env file
❌ Don't share database with live data
❌ Don't share venv/ folder
❌ Don't share logs/ folder
❌ Don't share __pycache__/ folders
```

**If you accidentally share .env:**
- Tell them to delete it
- Tell them to generate new SECRET_KEY
- Change any passwords in .env
- Reset database on your computer

---

Last Updated: February 2026
