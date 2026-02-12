# 🔐 Security Quick Start

Get your JC Icons application secured in 10 minutes.

## 1️⃣ Generate Secure Secrets (2 min)

```bash
# Generate SECRET_KEY (copy the output)
python -c "import secrets; print(secrets.token_hex(32))"

# Example output:
# a7f3c8e9d2b5f1a4c6e9b2d5f8a1c4e7f9a2b5c8d1e4f7a0b3c6d9e2f5a8c

# Generate admin password (copy the output)
python -c "import secrets; print(secrets.token_urlsafe(16))"

# Example output:
# Kx9_L2m-pQ5wJ8vR3
```

## 2️⃣ Create Environment Configuration (2 min)

```bash
# Copy template
cp .env.example .env

# Edit with your values
nano .env
# or
code .env
```

Fill in these values:

```
SECRET_KEY=<paste-your-generated-key>
FLASK_ENV=production
FLASK_DEBUG=false
ADMIN_PASSWORD=<paste-your-generated-password>

# For production with external database:
DATABASE_URL=postgresql://user:password@hostname:5432/dbname
```

Save and close the file.

## 3️⃣ Secure the .env File (1 min)

```bash
# Linux/macOS
chmod 600 .env

# Windows (PowerShell)
icacls .env /inheritance:r /grant:r "%USERNAME%:F"
```

## 4️⃣ Install Dependencies (2 min)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

## 5️⃣ Initialize Database (2 min)

```bash
# Initialize tables
python scripts/init_db.py init

# Create additional users (optional)
python scripts/init_db.py create-user
# Follow the prompts
```

## 6️⃣ Verify Security (1 min)

```bash
# Run security verification
python scripts/verify_deployment.py

# Should see mostly green checkmarks ✓
```

## 7️⃣ Test Application

```bash
# Start the app
python run.py

# Open browser: http://localhost:5000
# Login with:
# Username: admin
# Password: (from ADMIN_PASSWORD)
```

## 8️⃣ HTTPS Setup (Before Going Live)

### For **Heroku**:
 Automatic - free HTTPS included

### For **Self-Hosted** (Linux):

```bash
# Install Let's Encrypt
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d your-domain.com

# Auto-renew
sudo certbot renew --dry-run
```

### For **AWS/Docker**:
Follow deployment guide → DEPLOYMENT.md → AWS section

## 9️⃣ Configure Database (Production Only)

```bash
# PostgreSQL on Linux
sudo -u postgres createuser jc_icons -P
sudo -u postgres createdb jc_icons_v2 -O jc_icons

# Update .env
DATABASE_URL=postgresql://jc_icons:password@localhost:5432/jc_icons_v2

# Test connection
python scripts/verify_deployment.py
```

## 🔟 Pre-Deployment Security Checklist

```bash
# Run these before deploying:

# 1. Check no secrets in code
grep -r "SECRET_KEY = " app/
grep -r "password" app/ | grep -v ".pyc"

# 2. Verify .env not in git
git status | grep ".env"
# Should show: .env (if present, already in .gitignore)

# 3. Test rate limiting
curl -X POST http://localhost:5000/auth/login \
  -d "username=admin&password=wrong" \
  -H "Content-Type: application/x-www-form-urlencoded"
# Repeat 5x - 6th should return 429

# 4. Check security headers
curl -I http://localhost:5000 | grep -i "X-\|CSP"

# 5. Run all tests
pytest -v

# 6. Run security scan
bandit -r app/ -ll

# 7. Check dependencies
pip-audit
```

---

## 🎯 Common Security Tasks

### Change Admin Password

```bash
python
from app import create_app
from app.models.user import User
from app.extensions import db
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    admin.password_hash = generate_password_hash('new-password')
    db.session.commit()
    print("✓ Password changed")
```

### Create Additional User

```bash
python scripts/init_db.py create-user

# Follow the prompts:
# Username: john
# Full Name: John Doe
# Password: (enter secure password)
# Role: 1 (ADMIN) or 2 (SALES) or 3 (TECH)
```

### View Security Logs

```bash
# Real-time monitoring
tail -f logs/security.log

# Find failed logins
grep "login_failed" logs/security.log

# Count events
cut -d']' -f2 logs/security.log | sort | uniq -c
```

### Backup Database

```bash
# PostgreSQL
pg_dump -U jc_icons jc_icons_v2 > backup.sql.gz

# Restore
pg_restore backup.sql.gz
```

---

## 🚨 Security Issues?

1. **If you detect a security vulnerability:**
   - Do NOT open a public issue on GitHub
   - Create a private security advisory
   - Include reproduction steps and impact

2. **If your app is compromised:**
   ```bash
   # Stop the app
   sudo systemctl stop jc-icons-app
   
   # Backup logs
   cp -r logs logs.backup
   
   # Check recent activity
   tail -100 logs/security.log
   
   # Contact your security team
   ```

3. **If credentials are leaked:**
   ```bash
   # Rotate all secrets
   # 1. Generate new SECRET_KEY
   # 2. Update .env
   # 3. Restart application
   # 4. Force password reset for all users
   ```

---

## 📚 Learn More

| Topic | Document |
|-------|----------|
| **Complete Security Guide** | [SECURITY.md](SECURITY.md) |
| **Pre-Deployment Verification** | [SECURITY_VERIFICATION.md](SECURITY_VERIFICATION.md) |
| **Implementation Details** | [SECURITY_IMPLEMENTATION.md](SECURITY_IMPLEMENTATION.md) |
| **Deployment Guide** | [DEPLOYMENT.md](DEPLOYMENT.md) |

---

##  Security Checklist

- [ ] SECRET_KEY generated and set
- [ ] FLASK_ENV=production
- [ ] FLASK_DEBUG=false
- [ ] .env file permissions (600)
- [ ] Database credentials strong
- [ ] HTTPS certificate (for production)
- [ ] Security verification passes
- [ ] No hardcoded secrets in code
- [ ] Tests pass
- [ ] Security logs working
- [ ] Rate limiting verified
- [ ] Backups configured

---

## 🟢 You're Good to Go!

Once all checks pass, your application is:

 **Secure** - Industry-standard security practices  
 **Hardened** - Protected against common attacks  
 **Monitored** - Audit trail for all activities  
 **Documented** - Complete security documentation  
 **Compliant** - OWASP best practices  

**Ready for production deployment!**

---

## Support

Questions? Check:

1. `SECURITY.md` - Comprehensive guide
2. `SECURITY_VERIFICATION.md` - Step-by-step checks
3. `DEPLOYMENT.md` - Deployment-specific security
4. `README.md` - General getting started

---

Last Updated: February 2026
