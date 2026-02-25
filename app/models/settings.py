"""
Settings model for feature flags and system configuration
"""
from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class Setting(BaseModel, db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.String(500), nullable=False)
    description = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @staticmethod
    def get_value(key, default='false'):
        """Get setting value by key"""
        setting = Setting.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @staticmethod
    def get_bool(key, default=False):
        """Get setting as boolean"""
        value = Setting.get_value(key, 'true' if default else 'false')
        return value.lower() in ('true', '1', 'yes', 'on')
    
    @staticmethod
    def set_value(key, value, description=None):
        """Set or update setting value"""
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
            if description:
                setting.description = description
        else:
            setting = Setting(key=key, value=str(value), description=description)
            db.session.add(setting)
        db.session.commit()
    
    def __repr__(self):
        return f'<Setting {self.key}={self.value}>'