"""
Security utilities for JC Icons Management System

Provides security helpers, validators, and middleware
"""
import re
import hashlib
import secrets
from functools import wraps
from flask import request, abort
from datetime import datetime, timedelta


# ============================================================================
# Input Validation
# ============================================================================

def is_valid_username(username):
    """
    Validate username format
    - 3-32 characters
    - Alphanumeric and underscores only
    """
    if not username or not isinstance(username, str):
        return False
    if len(username) < 3 or len(username) > 32:
        return False
    # Allow alphanumeric and underscore
    return bool(re.match(r'^[a-zA-Z0-9_]+$', username))


def is_valid_email(email):
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False
    # Simple email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_password(password):
    """
    Validate password strength
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """
    if not password or not isinstance(password, str):
        return False
    
    if len(password) < 8:
        return False
    
    checks = {
        'uppercase': bool(re.search(r'[A-Z]', password)),
        'lowercase': bool(re.search(r'[a-z]', password)),
        'digit': bool(re.search(r'[0-9]', password)),
    }
    
    return all(checks.values())


def get_password_strength(password):
    """
    Get password strength score (0-100)
    Returns (score, message)
    """
    if not password:
        return 0, "Password is empty"
    
    score = 0
    feedback = []
    
    # Length
    if len(password) >= 8:
        score += 20
    if len(password) >= 12:
        score += 10
    if len(password) >= 16:
        score += 10
    else:
        feedback.append("Use at least 8 characters")
    
    # Character types
    if re.search(r'[a-z]', password):
        score += 15
    else:
        feedback.append("Include lowercase letters")
    
    if re.search(r'[A-Z]', password):
        score += 15
    else:
        feedback.append("Include uppercase letters")
    
    if re.search(r'[0-9]', password):
        score += 15
    else:
        feedback.append("Include numbers")
    
    if re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>/?]', password):
        score += 10
    else:
        feedback.append("Include special characters for extra security")
    
    # Common patterns (reduce score)
    common_patterns = [
        r'123', r'abc', r'qwerty', r'password',
        r'111', r'aaa', r'000'
    ]
    if any(re.search(pattern, password.lower()) for pattern in common_patterns):
        score -= 20
        feedback.append("Avoid common patterns")
    
    score = max(0, min(100, score))  # Clamp 0-100
    
    if score >= 80:
        message = "Strong password"
    elif score >= 60:
        message = "Good password"
    elif score >= 40:
        message = "Fair password"
    else:
        message = "Weak password"
    
    if feedback:
        message += ". " + ", ".join(feedback)
    
    return score, message


def sanitize_input(value, max_length=None):
    """
    Sanitize user input
    - Strip whitespace
    - Remove control characters
    - Optionally limit length
    """
    if not isinstance(value, str):
        return value
    
    # Remove control characters (but keep newlines/tabs in some cases)
    value = ''.join(c for c in value if ord(c) >= 32 or c in '\n\t\r')
    
    # Strip whitespace
    value = value.strip()
    
    # Limit length
    if max_length and len(value) > max_length:
        value = value[:max_length]
    
    return value


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.attempts = {}  # {identifier: [(timestamp, count)]}
    
    def is_allowed(self, identifier, max_attempts=5, window_seconds=300):
        """
        Check if request is allowed
        
        Args:
            identifier: User IP, username, etc.
            max_attempts: Max attempts allowed
            window_seconds: Time window in seconds
        
        Returns:
            (allowed: bool, remaining: int, reset_time: int-seconds)
        """
        now = datetime.utcnow()
        
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        
        # Remove old attempts outside window
        cutoff = now - timedelta(seconds=window_seconds)
        self.attempts[identifier] = [
            (ts, count) for ts, count in self.attempts[identifier]
            if ts > cutoff
        ]
        
        # Count attempts in window
        current_attempts = sum(count for _, count in self.attempts[identifier])
        
        if current_attempts >= max_attempts:
            # Get reset time
            oldest = self.attempts[identifier][0][0]
            reset_time = int((oldest + timedelta(seconds=window_seconds) - now).total_seconds())
            return False, 0, max(0, reset_time)
        
        # Record this attempt
        if not self.attempts[identifier] or self.attempts[identifier][-1][0] < now:
            self.attempts[identifier].append((now, 1))
        else:
            ts, count = self.attempts[identifier][-1]
            self.attempts[identifier][-1] = (ts, count + 1)
        
        remaining = max_attempts - current_attempts - 1
        return True, remaining, 0
    
    def reset(self, identifier):
        """Reset rate limit for identifier"""
        self.attempts.pop(identifier, None)


# Global rate limiter
rate_limiter = RateLimiter()


def rate_limit(max_attempts=5, window_seconds=300, key_func=None):
    """
    Decorator for rate limiting
    
    Args:
        max_attempts: Max requests allowed
        window_seconds: Time window
        key_func: Function to extract identifier from request
                  Default: uses client IP
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if key_func:
                identifier = key_func()
            else:
                identifier = request.remote_addr
            
            allowed, remaining, reset_time = rate_limiter.is_allowed(
                identifier, max_attempts, window_seconds
            )
            
            if not allowed:
                abort(429)  # Too Many Requests
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================================
# CSRF Protection
# ============================================================================

def generate_csrf_token():
    """Generate a secure CSRF token"""
    return secrets.token_hex(32)


# ============================================================================
# Password Utilities
# ============================================================================

def hash_password(password):
    """Hash password using werkzeug (used by Flask-Login)"""
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password, method='pbkdf2:sha256')


def verify_password(password_hash, password):
    """Verify password against hash"""
    from werkzeug.security import check_password_hash
    return check_password_hash(password_hash, password)


# ============================================================================
# Audit Logging
# ============================================================================

def log_security_event(event_type, user_id=None, username=None, ip_address=None, details=None):
    """
    Log security events for audit trail
    
    Args:
        event_type: Type of event (login, logout, permission_denied, etc.)
        user_id: User ID if applicable
        username: Username if applicable
        ip_address: Client IP address
        details: Additional details
    """
    from flask import request, current_app
    from datetime import datetime
    
    if not ip_address:
        ip_address = request.remote_addr if request else 'unknown'
    
    timestamp = datetime.utcnow().isoformat()
    
    audit_message = {
        'timestamp': timestamp,
        'event_type': event_type,
        'user_id': user_id,
        'username': username,
        'ip_address': ip_address,
        'details': details
    }
    
    # Log to security logger
    if hasattr(current_app, 'security_logger'):
        current_app.security_logger.info(str(audit_message))
    else:
        current_app.logger.warning(f"Security event: {audit_message}")


# ============================================================================
# Session Security
# ============================================================================

def get_session_info():
    """Get information about current session"""
    from flask import session
    return {
        'created': session.get('_flashes'),  # Just as example
        'user_agent': request.headers.get('User-Agent'),
        'remote_addr': request.remote_addr,
    }


# ============================================================================
# SQL Injection Prevention
# ============================================================================

def is_sql_injection_attempt(value):
    """
    Detect common SQL injection patterns
    Note: SQLAlchemy ORM prevents this, but good to log suspicious activity
    """
    if not isinstance(value, str):
        return False
    
    sql_patterns = [
        r"('\s*OR\s*'|\"?\s*OR\s*\"?)",  # OR injections
        r"(';?\s*DROP\s+)",  # DROP table
        r"(UNION\s+SELECT)",  # UNION injections
        r"(--\s*$)",  # SQL comments
        r"(;\s*DELETE\s+)",  # DELETE
        r"(/\*.*\*/)",  # Multi-line comments
    ]
    
    value_upper = value.upper()
    for pattern in sql_patterns:
        if re.search(pattern, value_upper, re.IGNORECASE):
            return True
    
    return False


# ============================================================================
# XSS Prevention
# ============================================================================

def is_xss_attempt(value):
    """
    Detect common XSS patterns
    Note: Flask templates auto-escape by default
    """
    if not isinstance(value, str):
        return False
    
    xss_patterns = [
        r'<script[^>]*>',
        r'javascript:',
        r'on\w+\s*=',  # onerror=, onclick=, etc.
        r'<iframe',
        r'<object',
        r'<embed',
    ]
    
    for pattern in xss_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            return True
    
    return False


# ============================================================================
# Security Headers Context Processor
# ============================================================================

def inject_security_context():
    """Inject security context into all templates"""
    from flask import url_for, session
    return {
        'csrf_token': generate_csrf_token() if '_csrf_token' not in session else session['_csrf_token'],
        'static_url': url_for('static', filename=''),
    }
