# 🔐 Security Guide - JC Icons Management System

Comprehensive security documentation for the JC Icons application.

## Table of Contents

1. [Security Architecture](#security-architecture)
2. [Authentication & Authorization](#authentication--authorization)
3. [Network Security](#network-security)
4. [Data Protection](#data-protection)
5. [Input Validation](#input-validation)
6. [Session Management](#session-management)
7. [Logging & Monitoring](#logging--monitoring)
8. [Deployment Security](#deployment-security)
9. [Security Checklist](#security-checklist)
10. [Incident Response](#incident-response)

---

## Security Architecture

### Multi-Layer Protection

```
┌─────────────────────────────────────────────────────────────┐
│  Web Browser / Client                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  HTTPS/TLS Layer                                             │
│  - SSL/TLS Encryption                                        │
│  - Certificate Pinning                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Security Headers                                            │
│  - HSTS                                                      │
│  - CSP (Content-Security-Policy)                             │
│  - X-Frame-Options                                           │
│  - X-Content-Type-Options                                    │
│  - X-XSS-Protection                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Web Application Firewall (Optional)                         │
│  - Rate Limiting                                             │
│  - IP Filtering                                              │
│  - Request Inspection                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Application Layer                                           │
│  - Authentication (Login)                                    │
│  - Authorization (Role-Based)                                │
│  - Input Validation                                          │
│  - CSRF Protection                                           │
│  - SQL Injection Prevention                                  │
│  - XSS Prevention                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Database Layer                                              │
│  - User Authentication (Passwords)                           │
│  - Data Encryption (At Rest)                                 │
│  - Access Control                                            │
│  - Backups & Recovery                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Authentication & Authorization

### Password Security

#### Requirement Policies

```python
from app.services.security import is_valid_password, get_password_strength

# Minimum Requirements:
# - At least 8 characters
# - At least one uppercase letter
# - At least one lowercase letter  
# - At least one digit

# Example:
password = "MySecure123"
if is_valid_password(password):
    score, message = get_password_strength(password)
    print(f"Password strength: {score}/100 - {message}")
```

#### Password Storage

- Passwords are hashed using **PBKDF2-SHA256** via werkzeug
- Never stored in plain text
- Each password has unique salt
- Salts are generated cryptographically securely

#### Password Reset Flow

1. User requests password reset
2. System generates secure token (valid 1 hour)
3. Token sent via email (not via SMS or security questions)
4. User sets new password matching policy
5. Old sessions are invalidated
6. Security event is logged

### Role-Based Access Control (RBAC)

Three roles implemented:

| Role | Permissions | Details |
|------|-----------|---------|
| **ADMIN** | Full system access | Can manage users, settings, all features |
| **SALES** | Sales operations | Can manage customers, sales, POS |
| **TECH** | Repair operations | Can manage repairs, technicians (if enabled) |

#### Role Implementation Example

```python
from app.services.authz import roles_required, admin_required

@app.route('/sensitive-data')
@login_required
@roles_required('ADMIN')
def sensitive_data():
    # Only ADMIN can access
    return render_template('admin/sensitive.html')
```

#### Feature Toggles

Feature-based access control via settings:

```python
from app.services.feature_flags import is_tech_can_view_details

if current_user.role == 'TECH' and is_tech_can_view_details():
    # TECH can view details if feature is enabled
    return show_detail_view()
```

---

## Network Security

### HTTPS/TLS Configuration

#### Production Requirements

1. **SSL Certificate**
   - Use certificates from trusted CAs (Let's Encrypt recommended)
   - Certificates valid for 90 days (auto-renew)
   - Support TLS 1.2 minimum

2. **Cipher Suites**
   ```
   Recommended: Modern Cipher Suites
   - TLS_AES_256_GCM_SHA384
   - TLS_CHACHA20_POLY1305_SHA256
   - TLS_AES_128_GCM_SHA256
   ```

3. **Certificate Pinning** (Optional)
   ```python
   # Pin certificates for critical APIs
   SSL_PINNING_ENABLED = True
   SSL_PINS = ['sha256/AAAAAAAAAA==', 'sha256/BBBBBBBBB==']
   ```

### Security Headers

#### Headers Automatically Added

```python
# Content-Security-Policy
default-src 'self'                           # Only allow from own domain
script-src 'self' 'unsafe-inline'           # Scripts from self
style-src 'self' 'unsafe-inline'            # Styles from self
img-src 'self' data:                        # Images from self or data URLs
connect-src 'self'                          # Only connect to own domain

# HTTP Strict-Transport-Security (HSTS)
max-age: 31536000 (1 year)                  # Enforce HTTPS for 1 year
includeSubDomains: true                     # Include all subdomains

# X-Frame-Options
SAMEORIGIN                                  # Allow framing only from same origin

# X-Content-Type-Options
nosniff                                     # Prevent MIME type sniffing

# X-XSS-Protection
1; mode=block                               # Enable XSS filter and block

# Referrer-Policy
strict-origin-when-cross-origin             # Control referrer information
```

#### Nginx Configuration Example

```nginx
# Security Headers
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# Content-Security-Policy
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; img-src 'self' data:; font-src 'self' cdn.jsdelivr.net; connect-src 'self';" always;

# Disable directory listing
autoindex off;

# Hide Nginx version
server_tokens off;
```

### Rate Limiting

#### Login Endpoint Protection

```python
# 5 failed attempts per 5 minutes -> 429 Too Many Requests
@auth_bp.route('/login', methods=['GET', 'POST'])
@rate_limit(max_attempts=5, window_seconds=300)
def login():
    # Login logic
```

#### Custom Rate Limiting

```python
from app.services.security import rate_limiter

def my_view():
    allowed, remaining, reset_time = rate_limiter.is_allowed(
        identifier=request.remote_addr,
        max_attempts=10,
        window_seconds=60
    )
    
    if not allowed:
        return "Rate limit exceeded", 429
    
    # Process request
    return "OK"
```

---

## Data Protection

### Encryption at Rest

#### Database Encryption

```python
# PostgreSQL with Encryption
# Enable at database creation:
CREATE EXTENSION pgcrypto;

# Encrypt sensitive columns:
ALTER TABLE user ADD COLUMN encrypted_data bytea;
UPDATE user SET encrypted_data = pgp_pub_encrypt(
    sensitive_data,
    dearmor('-----BEGIN PGP PUBLIC KEY...')
);
```

#### Environment Secrets Encryption

Store passwords and API keys encrypted:

```bash
# Use git-crypt for encrypted .env files
git-crypt init
git-crypt add-gpg-user <gpg-key-id>

# Mark .env as encrypted in .gitattributes
echo ".env filter=git-crypt diff=git-crypt" >> .gitattributes
git add .env .gitattributes
```

### Data Backups

#### Backup Strategy

1. **Frequency**: Daily automated backups
2. **Retention**: 30-day backup retention
3. **Location**: Off-site encrypted storage
4. **Testing**: Monthly restore tests

#### PostgreSQL Backup/Restore

```bash
# Full backup
pg_dump -U jc_icons jc_icons_v2 > backup.sql

# Compressed backup
pg_dump -U jc_icons jc_icons_v2 | gzip > backup.sql.gz

# Restore
psql -U jc_icons jc_icons_v2 < backup.sql

# Point-in-time recovery
psql -U jc_icons jc_icons_v2 -c "SELECT pg_start_backup('label')"
# ... perform operations ...
psql -U jc_icons jc_icons_v2 -c "SELECT pg_stop_backup()"
```

---

## Input Validation

### Input Validation Helpers

```python
from app.services.security import (
    is_valid_username,
    is_valid_email,
    is_valid_password,
    sanitize_input,
    is_sql_injection_attempt,
    is_xss_attempt
)

# Validate username
if not is_valid_username(username):
    return error("Invalid username format")

# Validate email
if not is_valid_email(email):
    return error("Invalid email format")

# Validate password
if not is_valid_password(password):
    score, message = get_password_strength(password)
    return error(f"Password too weak: {message}")

# Sanitize input
clean_input = sanitize_input(user_input, max_length=255)

# Detect suspicious patterns
if is_sql_injection_attempt(input_data):
    log_security_event('sql_injection_attempt')
    return error("Invalid input")

if is_xss_attempt(input_data):
    log_security_event('xss_attempt')
    return error("Invalid input")
```

### Form Validation Best Practices

```html
<!-- Validate on client side -->
<form method="POST" action="/users">
    <!-- Required field -->
    <input type="text" name="username" required 
           minlength="3" maxlength="32"
           pattern="[a-zA-Z0-9_]+" 
           title="3-32 characters, alphanumeric and underscore only">
    
    <!-- Email input -->
    <input type="email" name="email" required>
    
    <!-- Min password length -->
    <input type="password" name="password" required minlength="8">
    
    <!-- Server validates everything -->
    <button type="submit">Submit</button>
</form>
```

### SQL Injection Prevention

The application uses **SQLAlchemy ORM** which prevents SQL injection:

```python
# ✅ SAFE - Using ORM
user = User.query.filter_by(username=username).first()

# ❌ UNSAFE - Raw SQL (NEVER DO THIS)
user = User.query.raw(f"SELECT * FROM user WHERE username = '{username}'")

# ✅ SAFE - If raw SQL needed, use parameterized queries
user = User.query.from_statement(
    text("SELECT * FROM user WHERE username = :username")
).params(username=username).first()
```

### XSS Prevention

Flask templates auto-escape by default:

```html
<!-- Untrusted user input is automatically escaped -->
<h1>{{ user.name }}</h1>

<!-- Output if user.name = "<script>alert()</script>":
<h1>&lt;script&gt;alert()&lt;/script&gt;</h1>
-->

<!-- If you must render HTML, use safe markupsafe -->
{% autoescape false %}
    <!-- Only for trusted content -->
    {{ trusted_html_content|safe }}
{% endautoescape %}
```

---

## Session Management

### Session Configuration

```python
# In config.py or environment
SESSION_COOKIE_SECURE = True          # Only send over HTTPS
SESSION_COOKIE_HTTPONLY = True        # No access from JavaScript
SESSION_COOKIE_SAMESITE = 'Lax'       # CSRF protection
PERMANENT_SESSION_LIFETIME = 86400    # 1 day
```

### Session Fixation Prevention

```python
# Flask-Login automatically creates new session on login
from flask_login import login_user

# Old session is invalidated, new one created
login_user(user, remember=remember)
```

### Session Timeout

```python
# Automatic timeout configuration
PERMANENT_SESSION_LIFETIME = timedelta(days=7)

# Check session age before sensitive operations
from datetime import timedelta
session.permanent = True
app.permanent_session_lifetime = timedelta(days=7)
```

---

## Logging & Monitoring

### Security Logging

Event types logged:

```python
from app.services.security import log_security_event

# Authentication events
log_security_event('login_success', user_id=user.id, username=user.username)
log_security_event('login_failed', username=username)
log_security_event('logout', user_id=user.id)

# Authorization events
log_security_event('permission_denied', user_id=user.id, details='Accessed unauthorized resource')

# Data access events
log_security_event('data_accessed', user_id=user.id, details='Viewed repair ticket #123')
log_security_event('data_modified', user_id=user.id, details='Updated customer record')

# Security events
log_security_event('suspicious_activity', details='SQL injection attempt detected')
log_security_event('rate_limit_exceeded', ip_address='192.168.1.1')
log_security_event('password_change', user_id=user.id)
```

### Log Files

```
logs/
├── app.log              # Application events
└── security.log         # Security events and audit trail
```

### Log Monitoring

```bash
# Real-time monitoring
tail -f logs/security.log

# Search for specific events
grep "login_failed" logs/security.log
grep "permission_denied" logs/security.log
grep "suspicious_activity" logs/security.log

# Count events by type
cut -d']' -f2 logs/security.log | sort | uniq -c
```

### Alerting Rules

```python
# Export to monitoring system (Prometheus, ELK, DataDog)
# Alert on:
# - 5 failed logins from same IP in 5 minutes
# - Multiple SQL injection attempts
# - Repeated permission denied from same user
# - System errors above threshold
```

---

## Deployment Security

### Environment Setup

```bash
# Create .env.prod with secure values
cat > .env.prod << EOF
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
FLASK_ENV=production
FLASK_DEBUG=false
DATABASE_URL=postgresql://secure_user:secure_pass@db_host:5432/jc_icons_v2
ADMIN_PASSWORD=$(python -c "import secrets; print(secrets.token_urlsafe(16))")
EOF

# Secure the file
chmod 600 .env.prod
```

### Server Hardening

```bash
#!/bin/bash
# Linux server hardening script

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install security tools
sudo apt-get install -y fail2ban ufw git

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# Configure fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo systemctl restart fail2ban

# Harden SSH
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# Disable unnecessary services
sudo systemctl disable avahi-daemon
sudo systemctl disable cups
```

### Database Security

```sql
-- Create limited-privilege user
CREATE ROLE jc_icons LOGIN PASSWORD 'strong_password';
CREATE DATABASE jc_icons_v2 OWNER jc_icons;

-- Grant minimal required permissions
GRANT CONNECT ON DATABASE jc_icons_v2 TO jc_icons;
GRANT USAGE ON SCHEMA public TO jc_icons;
GRANT CREATE ON DATABASE jc_icons_v2 TO jc_icons;

-- Row-level security
ALTER TABLE user ENABLE ROW LEVEL SECURITY;
CREATE POLICY users_isolation ON user
    USING (user_id = current_user_id())
    WITH CHECK (user_id = current_user_id());

-- Audit table
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100),
    user_id INTEGER,
    timestamp TIMESTAMP DEFAULT NOW(),
    details TEXT,
    ip_address VARCHAR(45)
);

-- Create trigger for audit logging
CREATE TRIGGER audit_user_changes
AFTER UPDATE OR DELETE ON user
FOR EACH ROW
EXECUTE FUNCTION log_user_audit();
```

---

## Security Checklist

### Before Deployment

- [ ] **Secrets Management**
  - [ ] SECRET_KEY is randomly generated (32+ bytes)
  - [ ] No hardcoded secrets in code
  - [ ] .env files are in .gitignore
  - [ ] Database credentials are strong
  - [ ] API keys rotated within last 90 days

- [ ] **Authentication**
  - [ ] Password hashing is PBKDF2-SHA256 or better
  - [ ] All user inputs are validated
  - [ ] Session timeout is configured
  - [ ] CSRF tokens on all forms
  - [ ] Rate limiting on login (5 attempts/5 minutes)

- [ ] **Authorization**
  - [ ] Role-based access control tested
  - [ ] Feature toggles working
  - [ ] Resource ownership validated
  - [ ] Admin-only functions protected

- [ ] **Network Security**
  - [ ] HTTPS/TLS 1.2+ enabled
  - [ ] Security headers present
  - [ ] HSTS enabled
  - [ ] CSP configured
  - [ ] No HTTP (only HTTPS)

- [ ] **Data Protection**
  - [ ] Sensitive data encrypted at rest
  - [ ] Database backups encrypted
  - [ ] Backup restoration tested
  - [ ] Database connections encrypted
  - [ ] Logs don't contain sensitive data

- [ ] **Input Validation**
  - [ ] All inputs validated on server
  - [ ] SQL injection prevention enabled
  - [ ] XSS protection enabled
  - [ ] File uploads validated (if applicable)

- [ ] **Infrastructure**
  - [ ] Firewall configured
  - [ ] SSH hardened (key-based auth only)
  - [ ] Unnecessary services disabled
  - [ ] OS and packages updated
  - [ ] fail2ban or equivalent configured

- [ ] **Monitoring & Logging**
  - [ ] Security logging enabled
  - [ ] Log aggregation configured
  - [ ] Alerts on suspicious activity
  - [ ] Regular log review scheduled
  - [ ] Retention policy set (at least 90 days)

- [ ] **Documentation**
  - [ ] Security procedures documented
  - [ ] Incident response plan
  - [ ] Update procedures documented
  - [ ] Contact information recorded
  - [ ] Runbooks created

- [ ] **Testing**
  - [ ] Security tests pass
  - [ ] Penetration testing (recommended)
  - [ ] SSL/TLS configuration validated
  - [ ] Authentication tested
  - [ ] Authorization tested

---

## Incident Response

### Security Incident Response Plan

#### 1. Detection & Reporting

```bash
# If you notice suspicious activity:
# 1. Document the evidence
# 2. Take screenshots/logs
# 3. Preserve the evidence (don't delete logs)
# 4. Contact security team immediately
```

#### 2. Containment (Immediate)

```python
# Disable compromised account
user = User.query.get(user_id)
user.is_active = False
db.session.commit()
log_security_event('account_disabled_due_to_incident', user_id=user_id)

# Force password reset
from app.services.security import generate_password_reset_token
token = generate_password_reset_token(user_id)
# Send password reset email

# Invalidate sessions
session.clear()
```

#### 3. Eradication (Short-term)

- [ ] Identify the root cause
- [ ] Fix the vulnerability
- [ ] Update systems
- [ ] Rotate credentials
- [ ] Review access logs
- [ ] Check for lateral movement
- [ ] Remove malicious code

#### 4. Recovery (Medium-term)

- [ ] Restore from clean backups
- [ ] Monitor for re-infection
- [ ] Verify integrity of data
- [ ] Restore services
- [ ] Notify users if needed

#### 5. Lessons Learned (Post-incident)

- [ ] Post-incident meeting
- [ ] Document what happened
- [ ] Update procedures
- [ ] Implement preventive measures
- [ ] Share findings with team
- [ ] Update documentation

### Emergency Contacts

| Role | Name | Email | Phone | On-Call |
|------|------|-------|-------|---------|
| Security Lead | | | | |
| System Admin | | | | |
| Database Admin | | | | |
| Manager | | | | |

---

## Additional Resources

### OWASP Top 10

1. Broken Authentication
2. Sensitive Data Exposure
3. Injection
4. Broken Access Control
5. Broken Function Level Access Control
6. Security Misconfiguration
7. XSS
8. Insecure Deserialization
9. Using Components with Known Vulnerabilities
10. Insufficient Logging and Monitoring

### Security Scanning

```bash
# Dependency vulnerability scanning
pip install safety
safety check

# OWASP dependency check
pip install pip-audit
pip-audit --desc

# Code security scanning
pip install bandit
bandit -r app/
```

### Tools & Services

- **SSL Labs**: https://www.ssllabs.com/ - Test SSL/TLS configuration
- **Security Headers**: https://securityheaders.com/ - Check security headers
- **OWASP ZAP**: https://www.zaproxy.org/ - Penetration testing
- **SonarQube**: https://www.sonarqube.org/ - Code quality
- **Dependabot**: GitHub native dependency updates

---

## Contact & Updates

For security questions or to report vulnerabilities:
- Create a private security advisory on GitHub
- Do NOT open public issues for security vulnerabilities
- Include reproduction steps and impact assessment

---

**Last Updated:** February 2026  
**Next Review:** August 2026  
**Version:** 1.0.0
