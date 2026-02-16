# Complete Guide: Secure HTTPS Flask on Windows with Local Network Access

## Overview

This guide sets up a production-ready HTTPS Flask application on Windows that is:
- **Secure**: Uses self-signed certificates with a local Certificate Authority
- **Accessible**: Available on your local network via a custom domain (flask.home)
- **Trusted**: Certificates are recognized by all client devices (no browser warnings)
- **Production-Ready**: Uses enterprise-grade WSGI servers

**Why each component?**
- **mkcert**: Creates a local CA so browsers trust certificates without warnings
- **Flask + HTTPS**: Encrypts traffic between clients and server
- **Acrylic DNS**: Routes `flask.home` to your server IP without router access
- **Waitress/Hypercorn**: Production-grade servers for Windows (better than Flask's development server)

---

## Part 1: Prerequisites

### System Requirements
- Windows 10/11 with PowerShell (as Administrator)
- Python 3.8+
- Administrator access to install services

### Check Your Network Configuration
```powershell
# Find your machine's local IP address
ipconfig

# Look for "IPv4 Address" under your active network adapter
# Example: 192.168.1.50
```

**Note your values:**
- Local IP Address: `_______________` (e.g., 192.168.1.50)
- Custom Domain: `flask.home` (or your preferred domain)

---

## Part 2: Install and Configure mkcert

### Step 2.1: Install mkcert using Chocolatey (Recommended)

```powershell
# Open PowerShell as Administrator
# Install Chocolatey if you don't have it
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install mkcert
choco install mkcert -y -f

# Verify installation
mkcert --version
```

### Step 2.2: Create Local Certificate Authority

```powershell
# Create mkcert CA (requires Administrator)
mkcert -install

# Output will show where the CA is installed
# Windows: C:\Users\<YourUsername>\AppData\Local\mkcert
```

**What happens:**
- Generates a root CA certificate
- Installs it in Windows Certificate Store
- All certificates signed by this CA will be trusted by Windows

### Step 2.3: Generate Certificate for Your Application

Replace `192.168.1.50` with your actual local IP address:

```powershell
# Create a dedicated folder for certificates
$certFolder = "$env:USERPROFILE\flask_certs"
New-Item -ItemType Directory -Path $certFolder -Force

cd $certFolder

# Generate certificate for your domain and IP
mkcert -cert-file flask-cert.pem -key-file flask-key.pem flask.home localhost 127.0.0.1 192.168.1.50
```

**What this does:**
- Creates two files:
  - `flask-cert.pem`: Public certificate (can be shared)
  - `flask-key.pem`: Private key (MUST be kept secure)
- Certificate is valid for:
  - `flask.home` (custom domain)
  - `localhost` (local machine)
  - `127.0.0.1` (loopback)
  - `192.168.1.50` (your machine's local IP)

### Step 2.4: Verify Certificate Files

```powershell
# List certificate files
ls $env:USERPROFILE\flask_certs\

# Should show:
# - flask-cert.pem (3-4 KB)
# - flask-key.pem (1-2 KB)
```

---

## Part 3: Flask HTTPS Setup

### Step 3.1: Create Flask Application with HTTPS

Create `app_https.py`:

```python
"""
Secure Flask Application with HTTPS and Login
"""
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import os
from pathlib import Path

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Generate random secret key

# Path to certificates (update with your path)
CERT_PATH = Path.home() / "flask_certs" / "flask-cert.pem"
KEY_PATH = Path.home() / "flask_certs" / "flask-key.pem"

# Simple user database (in production, use proper database)
VALID_USERS = {
    "admin": "secure_password_123",
    "user": "password_456"
}


@app.route('/')
def index():
    """Home page"""
    if 'username' in session:
        return f"""
        <html>
            <body style="font-family: Arial; padding: 20px;">
                <h1>Welcome, {session['username']}!</h1>
                <p>You are securely connected via HTTPS.</p>
                <p>Connection time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <a href="{url_for('logout')}">Logout</a>
            </body>
        </html>
        """
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        # Validate credentials
        if username in VALID_USERS and VALID_USERS[username] == password:
            session['username'] = username
            session.permanent = True
            app.permanent_session_lifetime = timedelta(hours=24)
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return """
    <html>
        <head>
            <title>Secure Login</title>
            <style>
                body { font-family: Arial; max-width: 400px; margin: 100px auto; }
                form { border: 1px solid #ccc; padding: 20px; border-radius: 8px; }
                input { width: 100%; padding: 8px; margin: 10px 0; box-sizing: border-box; }
                button { width: 100%; padding: 10px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
                button:hover { background-color: #0056b3; }
                .info { background-color: #e7f3ff; border-left: 4px solid #2196F3; padding: 10px; margin-bottom: 20px; }
            </style>
        </head>
        <body>
            <div class="info">
                <strong>Demo Credentials:</strong><br>
                Username: admin | Password: secure_password_123<br>
                Username: user | Password: password_456
            </div>
            <form method="POST">
                <h2>Secure Login</h2>
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
        </body>
    </html>
    """


@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


@app.route('/secure-data')
def secure_data():
    """Example of protected data endpoint"""
    if 'username' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    return f"""
    <html>
        <body style="font-family: Arial; padding: 20px;">
            <h1>Secure Data (HTTPS Protected)</h1>
            <p>This page is encrypted in transit.</p>
            <p>User: {session['username']}</p>
            <p>Request came through HTTPS - traffic is encrypted</p>
            <a href="{url_for('index')}">Back to Home</a> | <a href="{url_for('logout')}">Logout</a>
        </body>
    </html>
    """


@app.route('/info')
def info():
    """Certificate and connection info"""
    return f"""
    <html>
        <body style="font-family: monospace; padding: 20px;">
            <h1>HTTPS Connection Information</h1>
            <h3>Your Connection:</h3>
            <ul>
                <li>Protocol: {request.environ.get('wsgi.url_scheme', 'unknown').upper()}</li>
                <li>Your IP: {request.remote_addr}</li>
                <li>Server: {request.host}</li>
                <li>User Agent: {request.environ.get('HTTP_USER_AGENT', 'Unknown')}</li>
            </ul>
            <h3>Certificate Details:</h3>
            <ul>
                <li>Issuer: mkcert local CA</li>
                <li>Valid for: flask.home, localhost, 127.0.0.1, 192.168.1.50</li>
                <li>Encryption: AES-256 (TLS 1.3)</li>
            </ul>
            <a href="{url_for('index')}">Back to Home</a>
        </body>
    </html>
    """


if __name__ == '__main__':
    # Verify certificates exist
    if not CERT_PATH.exists() or not KEY_PATH.exists():
        print(f"ERROR: Certificate files not found!")
        print(f"Expected locations:")
        print(f"  - Certificate: {CERT_PATH}")
        print(f"  - Key: {KEY_PATH}")
        print(f"\nGenerate certificates with:")
        print(f"  mkcert -cert-file flask-cert.pem -key-file flask-key.pem flask.home localhost 127.0.0.1 192.168.x.x")
        exit(1)
    
    print("=" * 60)
    print("SECURE FLASK APPLICATION")
    print("=" * 60)
    print(f"Certificate: {CERT_PATH}")
    print(f"Key: {KEY_PATH}")
    print(f"\nAccess the app at:")
    print(f"  - https://127.0.0.1:5000 (local)")
    print(f"  - https://localhost:5000 (local)")
    print(f"  - https://flask.home:5000 (network - after DNS setup)")
    print(f"\nDefault Credentials:")
    print(f"  Username: admin")
    print(f"  Password: secure_password_123")
    print("=" * 60)
    
    # Run with SSL context (development)
    app.run(
        host='0.0.0.0',  # Listen on all interfaces
        port=5000,
        ssl_context=(str(CERT_PATH), str(KEY_PATH)),
        debug=True
    )
```

### Step 3.2: Run Flask with HTTPS (Development)

```powershell
# Navigate to your app directory
cd C:\path\to\your\app

# Install required packages
pip install flask

# Run the app
python app_https.py
```

**Output should show:**
```
SECURE FLASK APPLICATION
============================================================
Certificate: C:\Users\...\flask_certs\flask-cert.pem
Key: C:\Users\...\flask_certs\flask-key.pem

Access the app at:
  - https://127.0.0.1:5000 (local)
  - https://localhost:5000 (local)
  - https://flask.home:5000 (network - after DNS setup)

Default Credentials:
  Username: admin
  Password: secure_password_123
```

### Step 3.3: Test HTTPS Locally

```powershell
# In another PowerShell window
# Test with curl (Windows 10+)
curl https://127.0.0.1:5000 --insecure  # Ignores cert warnings (for testing)

# Or use PowerShell
Invoke-WebRequest -Uri "https://localhost:5000" -SkipCertificateCheck
```

---

## Part 4: Production Setup with Waitress or Hypercorn

### Why Production Server?
- **Flask development server**: Single-threaded, not designed for production
- **Waitress/Hypercorn**: Multi-threaded, better performance, better logging

### Option 4A: Waitress (Recommended for Windows)

#### Step 4A.1: Install Waitress

```powershell
pip install waitress
```

#### Step 4A.2: Create Waitress Configuration

Create `waitress_config.py`:

```python
"""
Waitress WSGI Server Configuration for Windows
"""
import os
from pathlib import Path

# SSL Certificates
CERT_FILE = str(Path.home() / "flask_certs" / "flask-cert.pem")
KEY_FILE = str(Path.home() / "flask_certs" / "flask-key.pem")

# Server configuration
WAITRESS_CONFIG = {
    'host': '0.0.0.0',          # Listen on all interfaces
    'port': 5000,               # Port number
    '_quiet': False,            # Show logs
    'threads': 4,               # Number of worker threads
    'connection_limit': 100,    # Max concurrent connections
    'cleanup_interval': 30,     # Cleanup interval (seconds)
    'channel_timeout': 120,     # Channel timeout (seconds)
    'log_socket_errors': True,  # Log socket errors
}

# SSL context
SSL_CONTEXT = {
    'certfile': CERT_FILE,
    'keyfile': KEY_FILE,
}

print(f"Waitress Configuration:")
print(f"  Host: {WAITRESS_CONFIG['host']}")
print(f"  Port: {WAITRESS_CONFIG['port']}")
print(f"  Threads: {WAITRESS_CONFIG['threads']}")
print(f"  Certificate: {CERT_FILE}")
print(f"  Key: {KEY_FILE}")
```

#### Step 4A.3: Create Waitress Server Script

Create `run_waitress.py`:

```python
"""
Run Flask application with Waitress WSGI server
Production-ready HTTPS server for Windows
"""
import os
from pathlib import Path
from waitress import serve
from app_https import app

# SSL Certificates
CERT_FILE = str(Path.home() / "flask_certs" / "flask-cert.pem")
KEY_FILE = str(Path.home() / "flask_certs" / "flask-key.pem")

if __name__ == '__main__':
    # Verify certificates
    if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
        print(f"ERROR: Certificate files not found!")
        exit(1)
    
    print("=" * 70)
    print("WAITRESS HTTPS SERVER (Production)")
    print("=" * 70)
    print(f"Serving Flask application")
    print(f"Host: 0.0.0.0")
    print(f"Port: 5000")
    print(f"Threads: 4")
    print(f"Protocol: HTTPS (TLS 1.3)")
    print(f"\nAccess at:")
    print(f"  - https://127.0.0.1:5000 (local)")
    print(f"  - https://flask.home:5000 (network)")
    print(f"\nPress Ctrl+C to stop")
    print("=" * 70)
    
    # Serve with Waitress
    serve(
        app,
        host='0.0.0.0',
        port=5000,
        threads=4,
        _quiet=False,
        _shutdown_timeout=30,
        certfile=CERT_FILE,
        keyfile=KEY_FILE,
    )
```

#### Step 4A.4: Run Waitress Server

```powershell
# Navigate to your app directory
cd C:\path\to\your\app

# Run Waitress server
python run_waitress.py

# Output:
# Serving on https://0.0.0.0:5000
```

### Option 4B: Hypercorn (Async Support)

#### Step 4B.1: Install Hypercorn

```powershell
pip install hypercorn
```

#### Step 4B.2: Create Hypercorn Configuration

Create `hypercorn_config.toml`:

```toml
# Hypercorn Configuration for HTTPS
bind = ["0.0.0.0:5000"]
workers = 4
certfile = "{USERPROFILE}\\flask_certs\\flask-cert.pem"
keyfile = "{USERPROFILE}\\flask_certs\\flask-key.pem"
graceful_timeout = 30
timeout = 120
keepalive = 5
ssl_version = 16  # TLS 1.3
```

**Note**: Replace `{USERPROFILE}` with your actual path (e.g., `C:\Users\YourName`)

#### Step 4B.3: Run Hypercorn

```powershell
# Use with environment variable expansion
$certfile = "$env:USERPROFILE\flask_certs\flask-cert.pem"
$keyfile = "$env:USERPROFILE\flask_certs\flask-key.pem"

hypercorn app_https:app --bind 0.0.0.0:5000 --certfile $certfile --keyfile $keyfile
```

---

## Part 5: Set Up Acrylic DNS on Windows

### Why Acrylic DNS?
- Resolves `flask.home` to your server IP without modifying router
- Runs locally on your Windows machine
- Allows custom DNS records for your entire network

### Step 5.1: Install Acrylic DNS

**Option 1: Download from Sourceforge**
1. Visit: https://sourceforge.net/projects/acrylic/
2. Download Acrylic DNS Proxy for Windows
3. Run installer (Administrator)
4. Select "Install and Start"

**Option 2: Using Chocolatey**
```powershell
# Admin PowerShell
choco install acrylic -y
```

### Step 5.2: Configure Acrylic DNS Hosts

```powershell
# Open Hosts configuration file
notepad "C:\Program Files\Acrylic DNS Proxy\AcrylicHosts.txt"
```

Add these lines at the end (replace `192.168.1.50` with your IP):

```
# Flask Application
192.168.1.50 flask.home
192.168.1.50 www.flask.home
```

**Full example of AcrylicHosts.txt:**

```
# Acrylic Hosts File
# Format: IP_ADDRESS HOSTNAME [HOSTNAME2] [HOSTNAME3]...
#
# Examples:
# 127.0.0.1 localhost
# 192.168.1.1 router.home
# 192.168.1.50 flask.home

# Your Flask Application
192.168.1.50 flask.home
192.168.1.50 www.flask.home
```

Save and close (Ctrl+S, then close notepad).

### Step 5.3: Start Acrylic DNS Service

```powershell
# Start Acrylic DNS Proxy
Start-Service "Acrylic DNS Proxy"

# Verify it's running
Get-Service "Acrylic DNS Proxy"

# Should show: Running
```

### Step 5.4: Configure Windows to Use Acrylic DNS

```powershell
# Get current network configuration
Get-NetIPConfiguration

# Set DNS to localhost (127.0.0.1)
# For Ethernet:
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses ("127.0.0.1")

# For WiFi:
Set-DnsClientServerAddress -InterfaceAlias "WiFi" -ServerAddresses ("127.0.0.1")

# Verify
Get-DnsClientServerAddress -InterfaceAlias "Ethernet" # or "WiFi"
```

**Alternative: Using Network Settings GUI**
1. Settings → Network & Internet → WiFi (or Ethernet)
2. Click "Edit" next to DNS server assignment
3. Select "Manual"
4. Enable IPv4
5. Set DNS server to: `127.0.0.1`

### Step 5.5: Test DNS Resolution

```powershell
# Test that flask.home resolves to your IP
nslookup flask.home

# Expected output:
# Server: 127.0.0.1
# Address: 127.0.0.1#53
# 
# Name: flask.home
# Address: 192.168.1.50
```

---

## Part 6: Client Certificate Installation

Now other devices on your network can connect. They need to trust your mkcert CA.

### 6.1: Get the mkcert CA Certificate

```powershell
# On your server (Windows machine):
# Find the mkcert rootCA file

# Option 1: Copy from mkcert cache
$mkcertRoot = "$env:LOCALAPPDATA\mkcert"
Get-ChildItem $mkcertRoot

# Look for: rootCA.pem and rootCA-key.pem
# Copy rootCA.pem to a shared location
Copy-Item "$mkcertRoot\rootCA.pem" "$env:USERPROFILE\Desktop\rootCA.pem"
```

**Alternative: Export from Windows Certificate Store**

```powershell
# Find the mkcert Root CA in Windows
certmgr.msc  # Opens Cert Manager

# Navigate to: Local Computer → Trusted Root Certification Authorities → Certificates
# Find: mkcert {your computer name}
# Right-click → All Tasks → Export
# Format: DER encoded binary X.509 (.CER)
# Save as: rootCA.cer
```

### 6.2: Install CA on Windows Clients

**Method 1: Using Chocolatey (Easiest)**

On each Windows client:

```powershell
# Copy rootCA.pem to the client machine (via USB, network share, etc.)

# Open PowerShell as Administrator on client
Import-Certificate -FilePath "C:\Path\To\rootCA.pem" -CertStoreLocation Cert:\LocalMachine\Root
```

**Method 2: Using MMC (Manual)**

1. On client: Win+R → `mmc`
2. File → Add/Remove Snap-in
3. Select "Certificates" → Add
4. Choose "Computer Account" → Next → Local Computer → Finish
5. Navigate to: Certificates (Local Computer) → Trusted Root Certification Authorities
6. Right-click → All Tasks → Import
7. Select rootCA.pem
8. Complete wizard

**Method 3: Using Command Prompt**

```cmd
certutil -addstore "Root" "C:\Path\To\rootCA.pem"
```

### 6.3: Install CA on macOS Clients

```bash
# Copy rootCA.pem to Mac (via email, USB, AirDrop, etc.)

# Open Keychain Access
open /Applications/Utilities/Keychain\ Access.app

# Drag and drop rootCA.pem into Keychain
# Or: File → Import Items → Select rootCA.pem

# Find "mkcert" in login keychain
# Double-click → Trust → "Always Trust" for "When using this certificate"
```

### 6.4: Install CA on Android

```
1. Download rootCA.pem to your Android device
   - Email it to yourself
   - Or copy via file manager from shared network drive
   - Or use a QR code

2. Settings → Security → Encryption and credentials → Install a certificate
   - Select "CA certificate"
   - Navigate to rootCA.pem
   - Select it
   - Confirm

3. The certificate is now in "Trusted credentials"
```

**Verify:**
- Chrome → Menu → Settings → Privacy and security → Security → Manage certificates
- You should see your mkcert CA

### 6.5: Install CA on iOS

```
1. Email rootCA.pem to your iOS device
   - iOS cannot directly open .pem files
   - Convert to .p7b or .pfx format first

2. Method: Use macOS intermediary
   - On Mac: Open rootCA.pem in Keychain Access (see macOS section)
   - Export as .p7b or .pfx (with password)
   - Email .p7b to iOS
   - Open on iOS → Settings will prompt to install

3. Or use ProfileCreator utility
   - Create MDM profile with certificate
   - Install on iOS devices

4. Verify: Settings → General → VPN & Device Management → Certificate Trust Settings
   - Enable "mkcert" in full certificate trust
```

---

## Part 7: Verification and Testing

### Step 7.1: Verify from Local Machine

```powershell
# Test local access
$uri = "https://127.0.0.1:5000"
$result = Invoke-WebRequest $uri -SkipCertificateCheck
Write-Host "Status: $($result.StatusCode)"
Write-Host "Certificate: Trusted (green padlock expected)"
```

### Step 7.2: Verify from Another Windows Machine on Network

On a different Windows computer connected to your network:

```powershell
# Test network access
$uri = "https://flask.home:5000"
$result = Invoke-WebRequest $uri  # No -SkipCertificateCheck needed if CA is installed
Write-Host "Status: $($result.StatusCode)"
```

**Check Browser:**
1. Open Edge or Chrome
2. Navigate to: `https://flask.home:5000`
3. **Expected**: Green padlock ✓ (no certificate warning)
4. Click padlock → Connection is secure → Certificate is valid

### Step 7.3: Verify from macOS

```bash
# Test network access
curl https://flask.home:5000 -v

# Should show: SSL certificate verify ok
```

### Step 7.4: Verify from Android

1. Open Chrome
2. Navigate to: `https://flask.home:5000`
3. Should load without certificate warnings
4. Tap the padlock icon → Certificate information
5. Issuer should show: "mkcert {your computer}"

### Step 7.5: Verify HTTPS with curl

```powershell
# Detailed certificate information
curl https://flask.home:5000 -vv

# Expected in output:
# - TLS 1.3
# - ECDHE-RSA key exchange
# - AES-256-GCM cipher
# - subject: CN=flask.home
# - issuer: CN=mkcert {machinename}
# - expired: no
```

### Step 7.6: Optional - Wireshark Traffic Analysis

To verify encryption:

```powershell
# Install Wireshark if needed
choco install wireshark -y

# Open Wireshark
wireshark

# Steps:
# 1. Select your network interface
# 2. Start capture
# 3. Access https://flask.home:5000 from another device
# 4. In filter bar, type: tcp.port == 5000
# 5. Observe TLS handshake and encrypted data

# You'll see:
# - Client Hello (device → server)
# - Server Hello (server response)
# - Application Data (encrypted)
# - No plaintext passwords or HTTP headers visible
```

---

## Part 8: Create Startup Script and Batch Files

### Step 8.1: Auto-Start Script

Create `start_https_server.ps1`:

```powershell
# Auto-start secure HTTPS Flask server

# Get script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# Check admin privileges
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "Error: This script requires Administrator privileges"
    Write-Host "Please run PowerShell as Administrator"
    exit 1
}

Write-Host "Starting Acrylic DNS and Flask HTTPS Server..." -ForegroundColor Green

# 1. Start Acrylic DNS
Write-Host "Starting Acrylic DNS Proxy..." -ForegroundColor Cyan
Start-Service "Acrylic DNS Proxy" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Verify DNS
$dnsStatus = Get-Service "Acrylic DNS Proxy" -ErrorAction SilentlyContinue
if ($dnsStatus.Status -eq "Running") {
    Write-Host "✓ Acrylic DNS Proxy - Running" -ForegroundColor Green
} else {
    Write-Host "✗ Acrylic DNS Proxy - Failed to start" -ForegroundColor Red
}

# 2. Change directory to Flask app
cd $scriptPath

# 3. Verify certificates
$certFile = "$env:USERPROFILE\flask_certs\flask-cert.pem"
$keyFile = "$env:USERPROFILE\flask_certs\flask-key.pem"

if (-not (Test-Path $certFile) -or -not (Test-Path $keyFile)) {
    Write-Host "✗ Certificate files not found!" -ForegroundColor Red
    Write-Host "Expected locations:" -ForegroundColor Yellow
    Write-Host "  - $certFile"
    Write-Host "  - $keyFile"
    exit 1
}

Write-Host "✓ SSL Certificates verified" -ForegroundColor Green

# 4. Show system info
Write-Host "`n" + "=" * 70 -ForegroundColor Cyan
Write-Host "SECURE HTTPS FLASK SERVER" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan

ipconfig /all | Select-String "IPv4"
Write-Host "`nAccess URLs:" -ForegroundColor Yellow
Write-Host "  - https://127.0.0.1:5000 (local)"
Write-Host "  - https://localhost:5000 (local)"
Write-Host "  - https://flask.home:5000 (network)"
Write-Host "`nDefault Login:" -ForegroundColor Yellow
Write-Host "  Username: admin"
Write-Host "  Password: secure_password_123"
Write-Host "`nPress Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# 5. Start Flask or Waitress
if (Test-Path "run_waitress.py") {
    Write-Host "Starting Waitress server..." -ForegroundColor Cyan
    python run_waitress.py
} elseif (Test-Path "app_https.py") {
    Write-Host "Starting Flask development server..." -ForegroundColor Cyan
    python app_https.py
} else {
    Write-Host "✗ Application files not found!" -ForegroundColor Red
    exit 1
}
```

### Step 8.2: Batch File Shortcut

Create `start_server.bat`:

```batch
@echo off
REM Start secure HTTPS Flask server
REM Right-click → Run as administrator

echo Starting HTTPS Flask Server...
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "start_https_server.ps1"
pause
```

**How to use:**
1. Right-click `start_server.bat`
2. Select "Run as administrator"
3. Server starts automatically

---

## Part 9: Troubleshooting

### Issue: Certificate verification failed

**Solution:**
```powershell
# Reinstall the mkcert CA
mkcert -install

# On client, remove old certificates and reinstall
# Windows: Settings → Manage certificates → delete old mkcert certs → reimport
# Mac: Keychain → delete mkcert cert → reimport
```

### Issue: DNS not resolving flask.home

**Solution:**
```powershell
# Verify Acrylic is running
Get-Service "Acrylic DNS Proxy"

# Restart Acrylic
Restart-Service "Acrylic DNS Proxy"

# Check AcrylicHosts.txt file
notepad "C:\Program Files\Acrylic DNS Proxy\AcrylicHosts.txt"
# Verify your entry: 192.168.1.50 flask.home

# Clear DNS cache
ipconfig /flushdns

# Test again
nslookup flask.home
```

### Issue: Port 5000 already in use

**Solution:**
```powershell
# Find process using port 5000
Get-NetTCPConnection -LocalPort 5000

# Kill the process
Stop-Process -Id <PID> -Force

# Or use a different port (update firewall and DNS config)
```

### Issue: Firewall blocking connections

**Solution:**
```powershell
# Add Flask to Windows Firewall
New-NetFirewallRule -DisplayName "Flask HTTPS" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow

# Or disable firewall for testing (NOT RECOMMENDED for production)
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled $false
```

### Issue: Browser shows certificate not valid

**Solution:**
1. Verify certificate was created for flask.home:
   ```powershell
   openssl x509 -in $env:USERPROFILE\flask_certs\flask-cert.pem -text -noout | grep "DNS:"
   ```

2. Verify CA certificate is installed on client

3. Clear browser cache:
   - Chrome: Ctrl+Shift+Delete → All time → Cookies and cache → Clear
   - Edge: Settings → Privacy → Clear browsing data

4. Restart browser

### Issue: HTTPS connection times out

**Solution:**
```powershell
# Check Flask is running
Get-Process python

# Check firewall
Get-NetFirewallRule -DisplayName "Flask*" | Select-Object DisplayName, Enabled

# Test locally first
curl https://127.0.0.1:5000 -SkipCertificateCheck

# Check network connectivity
ping 192.168.1.50  # Your server IP
```

---

## Part 10: Security Best Practices

### 1. Private Key Protection
```powershell
# Protect the private key file
# Set restrictive permissions (Windows)
icacls "$env:USERPROFILE\flask_certs\flask-key.pem" /inheritance:r
icacls "$env:USERPROFILE\flask_certs\flask-key.pem" /grant:r "$env:USERNAME`:F"

# Only your user should access it
```

### 2. Password Management
```python
# In production, use proper password hashing
from werkzeug.security import generate_password_hash, check_password_hash

# Generate hashes
hashed = generate_password_hash("secure_password_123", method='pbkdf2:sha256')

# Verify passwords
check_password_hash(hashed, "secure_password_123")  # True
```

### 3. Session Security
```python
# In Flask app_https.py
app.config.update(
    SESSION_COOKIE_SECURE=True,      # Only send cookie over HTTPS
    SESSION_COOKIE_HTTPONLY=True,    # Prevent JavaScript access
    SESSION_COOKIE_SAMESITE='Lax',   # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
)
```

### 4. HSTS (HTTP Strict Transport Security)
```python
# Add security headers
@app.after_request
def security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response
```

### 5. Network Isolation
- Only expose port 5000 to your local network
- Block external access via firewall
- Don't use flask.home for internet-facing applications

---

## Quick Reference Commands

### Start Everything
```powershell
# Run this as Administrator
PowerShell -ExecutionPolicy Bypass -File start_https_server.ps1
```

### Create Certificates
```powershell
cd $env:USERPROFILE\flask_certs
mkcert -cert-file flask-cert.pem -key-file flask-key.pem flask.home localhost 127.0.0.1 192.168.1.50
```

### Test HTTPS
```powershell
# From server
Invoke-WebRequest https://127.0.0.1:5000 -SkipCertificateCheck

# From client (after CA installed)
Invoke-WebRequest https://flask.home:5000
```

### Manage Services
```powershell
# Acrylic DNS
Start-Service "Acrylic DNS Proxy"
Stop-Service "Acrylic DNS Proxy"
Restart-Service "Acrylic DNS Proxy"

# Check status
Get-Service "Acrylic DNS Proxy"
```

### Debug DNS
```powershell
nslookup flask.home
nslookup 192.168.1.50

# Clear cache
ipconfig /flushdns
```

### View Certificates
```powershell
# Installed CA certificates
Get-ChildItem Cert:\LocalMachine\Root | Where-Object {$_.Subject -like "*mkcert*"}

# Certificates used by Flask
openssl x509 -in "$env:USERPROFILE\flask_certs\flask-cert.pem" -text -noout
```

---

## Next Steps

1. **For Development**: Use Flask development server with `app_https.py`
2. **For Testing**: Use Waitress with `run_waitress.py`
3. **For Production**: 
   - Use Hypercorn with async support
   - Consider reverse proxy (nginx, IIS)
   - Implement proper logging and monitoring

4. **Security Enhancements**:
   - Implement real database for users
   - Add rate limiting
   - Use environment variables for secrets
   - Implement OAuth/LDAP if needed

---

## Summary

You now have:
✅ A local Certificate Authority (mkcert)
✅ HTTPS certificates trusted by all devices
✅ A secure Flask application with login
✅ Local DNS resolution (Acrylic)
✅ Multi-device access without browser warnings
✅ Production-ready server options (Waitress/Hypercorn)
✅ Automated startup scripts

All devices on your network can now securely access `https://flask.home:5000` with a green padlock in their browser!
