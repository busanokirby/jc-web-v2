# 🔐 Security Verification Checklist

Quick verification that your deployment is secure. Run before going live.

## ✅ Pre-Deployment Security Checks

### 1. Secrets & Configuration

```bash
# Verify SECRET_KEY is set
echo "SECRET_KEY: $SECRET_KEY" | grep -v "dev-secret"

# Verify FLASK_ENV is production
echo "FLASK_ENV: $FLASK_ENV" | grep "production"

# Verify no secrets in code
grep -r "SECRET_KEY = " app/ | grep -v "os.environ"
grep -r "password" app/ | grep -v ".pyc" | grep -v "#"

# Verify .env is in .gitignore
grep "\.env" .gitignore

# Verify no database credentials in code
grep -r "postgresql://" app/
grep -r "DATABASE_URL" app/
```

### 2. Database Security

```bash
# Test database connection
python -c "
from app import create_app
app = create_app()
with app.app_context():
    from app.extensions import db
    from sqlalchemy import text
    try:
        result = db.session.execute(text('SELECT 1'))
        print('✓ Database connection successful')
    except Exception as e:
        print(f'✗ Database error: {e}')
"

# Verify database user is not 'postgres'
echo "Current DB User: (check environment variables)"
echo $DATABASE_URL | grep -v postgres

# Check database password strength
# (Verify in your password manager)
```

### 3. HTTPS/SSL Configuration

```bash
# Check if certificate is valid
openssl s_client -connect your-domain.com:443 << EOF
Q
EOF

# Check certificate expiration
echo | openssl s_client -servername your-domain.com -connect your-domain.com:443 2>/dev/null | \
  openssl x509 -noout -dates

# Verify HSTS header
curl -I https://your-domain.com | grep -i "Strict-Transport"

# Test SSL configuration
curl -I https://your-domain.com | grep -i "X-"
```

### 4. Application Health

```bash
# Check health endpoint
curl https://your-domain.com/health

# Should return:
# {"status": "healthy", "message": "Application is running"}

# Check for version disclosure
curl -I https://your-domain.com | grep -i "Server"

# Should NOT reveal sensitive info
```

### 5. Authentication Security

```bash
# Test rate limiting on login
for i in {1..6}; do
  echo "Attempt $i:"
  curl -X POST https://your-domain.com/auth/login \
    -d "username=admin&password=wrong" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -w "Status: %{http_code}\n"
done

# Should return 429 (Too Many Requests) after 5 attempts
```

### 6. Security Headers Verification

```bash
# Check all security headers
curl -I https://your-domain.com

# Required headers:
# ✓ Strict-Transport-Security
# ✓ X-Content-Type-Options: nosniff
# ✓ X-Frame-Options: SAMEORIGIN
# ✓ X-XSS-Protection: 1; mode=block
# ✓ Referrer-Policy
# ✓ Content-Security-Policy
```

### 7. Service & Port Security

```bash
# Check open ports (should be limited)
sudo nmap -sT localhost

# Should show:
# 22/tcp - SSH (if applicable)
# 80/tcp - HTTP (redirect only)
# 443/tcp - HTTPS

# Check for unnecessary services
sudo systemctl list-units --type service --state active

# Should NOT have:
# - telnet
# - FTP
# - Unencrypted protocols
```

### 8. File & Permission Security

```bash
# Check .env file permissions
ls -la .env
# Should be: -rw------- or -rw-r----- (600 or 640)

# Fix if needed:
chmod 600 .env

# Check sensitive file permissions
ls -la logs/
ls -la instance/

# Verify SQL files aren't exposed
find . -name "*.sql" -o -name "*.db" -o -name "*.sqlite"
```

### 9. Logging Verification

```bash
# Check logs exist and are being written
ls -la logs/
tail logs/app.log
tail logs/security.log

# Verify logs don't contain sensitive data
grep -i "password\|token\|secret\|key" logs/
# Should return nothing or only mentions in code with values hidden
```

### 10. Backup Verification

```bash
# Verify backups exist
ls -la /path/to/backups/

# Verify backup encryption
file /path/to/backups/latest.sql.gpg
# Should show: GPG encrypted data

# Test backup by restoring to test database
# (Do not test on production!)
```

## 🔍 Security Scanning

### Dependency Vulnerabilities

```bash
# Install vulnerability scanner
pip install pip-audit

# Scan for vulnerable packages
pip-audit

# Check specific package versions
pip list | grep Flask
pip list | grep Werkzeug
```

### Code Security Analysis

```bash
# Install security scanner
pip install bandit

# Scan application code
bandit -r app/ -ll

# Review findings
# Fix any HIGH or MEDIUM severity issues
```

### SSL/TLS Configuration

```bash
# Option 1: Use online tool
# https://www.ssllabs.com/ssltest/

# Option 2: Use testssl.sh locally
# git clone --depth 1 https://github.com/drwetter/testssl.sh.git
# ./testssl.sh/testssl.sh https://your-domain.com
```

### Security Headers Test

```bash
# Option 1: Use online tool
# https://securityheaders.com/

# Option 2: Manual checking
curl -I https://your-domain.com | \
  grep -E "Strict-Transport|X-Content|X-Frame|CSP"
```

## 📋 Final Checklist

Before going live, verify:

- [ ] All environment variables are set and secure
- [ ] Database credentials are strong and unique
- [ ] SSL certificate is valid and not self-signed
- [ ] HTTPS redirects HTTP traffic
- [ ] All security headers are present
- [ ] Rate limiting is working (test with login endpoint)
- [ ] Application health check passes
- [ ] Logs are being written
- [ ] Backups are encrypted and tested
- [ ] No sensitive data in logs
- [ ] File permissions are correct
- [ ] No vulnerable dependencies
- [ ] Code security scan passes
- [ ] Firewall is configured
- [ ] Unnecessary ports are closed
- [ ] SSH is hardened (key auth only)

## ⚠️ If Something Fails

1. **Check Logs**
   ```bash
   tail -f logs/app.log
   tail -f logs/security.log
   docker-compose logs app
   ```

2. **Debug Health Endpoint**
   ```bash
   curl -v https://your-domain.com/health
   ```

3. **Test Database Connection**
   ```bash
   python scripts/verify_deployment.py
   ```

4. **Check Environment Variables**
   ```bash
   echo $SECRET_KEY
   echo $FLASK_ENV
   echo $DATABASE_URL | head -c 30
   ```

5. **Review Security Configuration**
   ```python
   python -c "from app import create_app; app = create_app(); print(app.config)"
   ```

## 🚨 Incident Response

If you detect a security issue:

1. **Isolate the system**
   ```bash
   sudo systemctl stop jc-icons-app
   ```

2. **Preserve evidence**
   ```bash
   cp -r logs logs.backup
   ```

3. **Check for compromise**
   ```bash
   last                    # Recent logins
   lastb                   # Failed login attempts
   tail -f /var/log/auth.log
   ```

4. **Review audit trail**
   ```bash
   tail logs/security.log | grep -E "login|error|permission"
   ```

5. **Notify team immediately**
   - Document what happened
   - Take screenshots
   - Don't delete evidence
   - Follow incident response plan

## ✅ Monitoring

Set up continuous monitoring:

```bash
# Monitor security logs in real-time
watch -n 5 'tail logs/security.log'

# Alert on suspicious activity
# (Configure with your monitoring tool)
grep -i "attempt\|failed\|denied" logs/security.log | wc -l

# Check health periodically
watch -n 60 'curl -s https://your-domain.com/health | jq .'
```

---

**✓ Security verification complete. Ready for production!**

Run this checklist:
- [ ] Before first deployment
- [ ] Monthly (automated)
- [ ] Before major updates
- [ ] After any security incident

---

Last Updated: February 2026
