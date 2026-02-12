"""
Configuration for JC Icons Management System V2
Supports development, testing, and production environments
"""
import os
from datetime import timedelta


class Config:
    """Base configuration"""
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError('SECRET_KEY environment variable is required for security')
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Security headers
    PREFERRED_URL_SCHEME = 'https'
    
    @staticmethod
    def init_app(app):
        """Initialize app-specific configurations"""
        pass


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = False
    SESSION_COOKIE_SECURE = False
    PREFERRED_URL_SCHEME = 'http'
    
    @staticmethod
    def init_db_uri():
        """Get database URI for development"""
        import os
        project_root = os.path.abspath(os.path.dirname(__file__))
        instance_path = os.path.join(project_root, 'instance')
        os.makedirs(instance_path, exist_ok=True)
        db_path = os.path.join(instance_path, 'jc_icons_v2.db')
        return f'sqlite:///{db_path}'


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SESSION_COOKIE_SECURE = False
    PREFERRED_URL_SCHEME = 'http'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    @staticmethod
    def init_db_uri():
        """Get database URI for production"""
        # For production, use an external database
        # Examples: PostgreSQL, MySQL, etc.
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            raise ValueError('DATABASE_URL environment variable is required in production')
        
        # Handle heroku postgres:// -> postgresql://
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        
        return db_url


def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development').lower()
    
    if env == 'testing':
        return TestingConfig
    elif env == 'production':
        return ProductionConfig
    else:
        return DevelopmentConfig
