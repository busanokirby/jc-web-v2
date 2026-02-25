"""
Email Configuration and Reporting Models
"""
from __future__ import annotations
from datetime import datetime, time
from app.extensions import db
import os
import base64
import logging

logger = logging.getLogger(__name__)


class SMTPSettings(db.Model):
    """SMTP Configuration for automated email reporting"""
    __tablename__ = 'smtp_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # SMTP Configuration
    smtp_server = db.Column(db.String(255), nullable=False)  # e.g., 'smtp.gmail.com'
    smtp_port = db.Column(db.Integer, default=587)
    email_address = db.Column(db.String(255), nullable=False)
    email_password_encrypted = db.Column(db.LargeBinary, nullable=False)
    use_tls = db.Column(db.Boolean, default=True)
    
    # Control flags
    is_enabled = db.Column(db.Boolean, default=False)
    auto_send_time = db.Column(db.Time, default=lambda: time(9, 0))  # Default 9:00 AM
    
    # Frequency: 'daily', 'every_3_days', 'weekly'
    frequency = db.Column(db.String(20), default='daily')
    
    # Tracking
    last_sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    email_logs = db.relationship('EmailReport', backref='smtp_config', cascade='all, delete-orphan')
    
    @staticmethod
    def get_cipher():
        """Get Fernet cipher for password encryption/decryption"""
        try:
            from cryptography.fernet import Fernet
            
            key = os.environ.get('EMAIL_ENCRYPTION_KEY')
            
            if not key:
                # Fallback: generate a stable key from app secret
                try:
                    from flask import current_app
                    base_key = current_app.config.get('SECRET_KEY', 'default-key-12345')
                except:
                    base_key = 'default-key-12345'
                
                # Hash to create stable key
                import hashlib
                hashed = hashlib.sha256(base_key.encode()).digest()
                key = base64.urlsafe_b64encode(hashed)
            else:
                # Ensure key is properly formatted
                if isinstance(key, str):
                    # If string, encode and base64
                    if len(key) < 44:  # Less than typical base64 length
                        key = base64.urlsafe_b64encode(key.encode().ljust(32))
                    else:
                        key = key.encode()
                
                # Validate it's proper base64
                try:
                    base64.urlsafe_b64decode(key)
                except:
                    # If not valid base64, create new key
                    import hashlib
                    hashed = hashlib.sha256(key if isinstance(key, bytes) else key.encode()).digest()
                    key = base64.urlsafe_b64encode(hashed)
            
            return Fernet(key)
        except Exception as e:
            logger.error(f"Failed to initialize Fernet cipher: {e}")
            # Return a dummy cipher that doesn't encrypt (for fallback)
            return None
    
    def set_password(self, password: str):
        """Encrypt and store password"""
        try:
            cipher = self.get_cipher()
            if cipher:
                encrypted = cipher.encrypt(password.encode())
                self.email_password_encrypted = encrypted
            else:
                # Fallback: store plaintext (not secure, but prevents crashes)
                self.email_password_encrypted = password.encode()
        except Exception as e:
            logger.error(f"Failed to encrypt password: {e}")
            # Fallback: store plaintext
            self.email_password_encrypted = password.encode()
    
    def get_password(self) -> str:
        """Decrypt and retrieve password"""
        try:
            cipher = self.get_cipher()
            if cipher:
                decrypted = cipher.decrypt(self.email_password_encrypted)
                return decrypted.decode()
            else:
                # Fallback: assume plaintext
                return self.email_password_encrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt password: {e}")
            # Fallback: assume plaintext
            try:
                return self.email_password_encrypted.decode()
            except:
                return ""
    
    @classmethod
    def get_active_config(cls):
        """Get the active SMTP configuration (assumes single config)"""
        return cls.query.first()
    
    def __repr__(self) -> str:
        return f"<SMTPSettings {self.email_address} enabled={self.is_enabled} frequency={self.frequency}>"


class EmailReport(db.Model):
    """Log of automated email reports sent"""
    __tablename__ = 'email_report'
    
    id = db.Column(db.Integer, primary_key=True)
    smtp_settings_id = db.Column(db.Integer, db.ForeignKey('smtp_settings.id'), nullable=False)
    
    # Report metadata
    report_type = db.Column(db.String(50), default='daily_sales')  # daily_sales, weekly_sales, etc.
    recipient_email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    
    # Report data summary
    total_revenue = db.Column(db.Numeric(12, 2), default=0)
    total_transactions = db.Column(db.Integer, default=0)
    total_sales_payments = db.Column(db.Numeric(12, 2), default=0)
    total_repair_payments = db.Column(db.Numeric(12, 2), default=0)
    
    # Status tracking
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    error_message = db.Column(db.Text, nullable=True)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)
    
    # Report period
    report_date_start = db.Column(db.Date, nullable=True)
    report_date_end = db.Column(db.Date, nullable=True)
    
    # Attachment info
    attachment_filename = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def mark_sent(self):
        """Mark report as successfully sent"""
        self.status = 'sent'
        self.sent_at = datetime.utcnow()
        db.session.commit()
    
    def mark_failed(self, error_msg: str):
        """Mark report as failed with error message"""
        self.status = 'failed'
        self.error_message = error_msg
        db.session.commit()
    
    def __repr__(self) -> str:
        return f"<EmailReport {self.report_type} {self.status} to {self.recipient_email}>"
