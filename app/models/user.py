"""
User model for authentication and authorization
"""
from app.extensions import db
from app.models.base import BaseModel
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(UserMixin, BaseModel, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), default='JC Icons', nullable=False)  # Company/Organization name
    role = db.Column(db.String(20), nullable=False)  # ADMIN, SALES, TECH
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, *roles):
        """Check if user has any of the specified roles.

        The SALES and TECH roles are considered interchangeable; a technician
        is allowed to perform sales functions and vice‑versa.  This simplifies
        permission lists throughout the codebase.
        """
        if self.role == 'SALES' and 'TECH' in roles:
            return True
        if self.role == 'TECH' and 'SALES' in roles:
            return True
        return self.role in roles
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'