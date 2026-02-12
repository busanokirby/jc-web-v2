"""
Application factory for JC Icons Management System V2
"""
import os
import logging
from flask import Flask, render_template
from decimal import Decimal, ROUND_HALF_UP
from app.extensions import db, login_manager
from app.models.user import User


def setup_logging(app):
    """Configure logging for the application"""
    import logging
    
    if not app.debug and not app.testing:
        # Production logging
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Application logger
        file_handler = logging.FileHandler('logs/app.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Security logger
        security_handler = logging.FileHandler('logs/security.log')
        security_handler.setFormatter(logging.Formatter(
            '%(asctime)s [SECURITY] %(levelname)s: %(message)s'
        ))
        security_handler.setLevel(logging.INFO)
        security_logger = logging.getLogger('security')
        security_logger.addHandler(security_handler)
        security_logger.setLevel(logging.INFO)
        app.security_logger = security_logger
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('JC Icons Management System startup')
    else:
        # Development/Testing logging
        app.logger.setLevel(logging.DEBUG)


def create_app(config=None):
    """
    Create and configure the Flask application
    """
    # Get the project root directory (parent of app folder)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # Create app with correct template and static folder paths
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=os.path.join(project_root, 'templates'),
        static_folder=os.path.join(project_root, 'static')
    )
    
    # Load configuration
    if config is None:
        # Development default
        config = os.environ.get('FLASK_ENV', 'development')
        if config == 'testing':
            from config import TestingConfig
            config = TestingConfig
        elif config == 'production':
            from config import ProductionConfig
            config = ProductionConfig
        else:
            from config import DevelopmentConfig
            config = DevelopmentConfig
    
    # Apply config
    if isinstance(config, str):
        # If config is a string, import it dynamically
        from config import get_config
        config = get_config()
    
    app.config.from_object(config)
    
    # Set database URI
    if hasattr(config, 'init_db_uri'):
        app.config['SQLALCHEMY_DATABASE_URI'] = config.init_db_uri()
    else:
        # Fallback to development SQLite
        instance_path = os.path.join(project_root, 'instance')
        os.makedirs(instance_path, exist_ok=True)
        db_path = os.path.join(instance_path, 'jc_icons_v2.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.core.routes import core_bp
    from app.blueprints.repairs.routes import repairs_bp
    from app.blueprints.customers.routes import customers_bp
    from app.blueprints.users.routes import users_bp
    from app.blueprints.reports.routes import reports_bp
    # Ensure inventory blueprint extra routes are imported so new endpoints are registered
    from app.blueprints.inventory import extra_routes  # noqa
    from app.blueprints.inventory.routes import inventory_bp
    from app.blueprints.sales.routes import sales_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(core_bp, url_prefix='')
    app.register_blueprint(repairs_bp, url_prefix='/repairs')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(sales_bp, url_prefix='/sales')
    
    # Setup logging
    setup_logging(app)
    
    # Add security headers middleware
    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # HSTS (only in production)
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "font-src 'self' cdn.jsdelivr.net; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        response.headers['Content-Security-Policy'] = csp
        
        return response
    
    # Trust proxy headers in production
    if not app.debug:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    
    # Template filters
    @app.template_filter('currency')
    def currency_filter(value):
        """Format Decimal as currency string"""
        from app.services.financials import safe_decimal
        value = safe_decimal(value, '0.00')
        return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,}"
    
    @app.template_filter('datetimeformat')
    def datetimeformat_filter(value, fmt='%Y-%m-%d'):
        """Format date or datetime"""
        from datetime import datetime, date
        if value is None:
            return ''
        if isinstance(value, date) and not isinstance(value, datetime):
            value = datetime.combine(value, datetime.min.time())
        return value.strftime(fmt)

    @app.context_processor
    def inject_inventory_counts():
        """Provide low-stock count globally for the nav badge"""
        try:
            from app.models.inventory import Product
            low_count = Product.query.filter(Product.is_active==True, Product.stock_on_hand <= Product.reorder_threshold).count()
        except Exception:
            # If DB not ready or migrations pending, fail gracefully
            low_count = 0
        return dict(inventory_low_count=low_count)
    
    # Register error handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    # Create database tables and initialize settings
    with app.app_context():
        db.create_all()
        initialize_database()
    
    return app


def initialize_database():
    """
    Initialize database with default settings and admin user if needed
    """
    from app.models.settings import Setting
    from app.models.user import User
    from werkzeug.security import generate_password_hash
    
    # Create default settings if they don't exist
    if not Setting.query.filter_by(key='POS_ENABLED').first():
        db.session.add(Setting(key='POS_ENABLED', value='true', description='Enable Point of Sale module'))
    
    if not Setting.query.filter_by(key='SALES_CAN_EDIT_INVENTORY').first():
        db.session.add(Setting(key='SALES_CAN_EDIT_INVENTORY', value='true', 
                              description='Allow SALES role to edit inventory'))
    
    if not Setting.query.filter_by(key='TECH_CAN_VIEW_DETAILS').first():
        db.session.add(Setting(key='TECH_CAN_VIEW_DETAILS', value='true', 
                              description='Allow TECH role to view repair and customer details'))
    
    # Create default admin user if no users exist
    if User.query.count() == 0:
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        admin_user = User(
            username='admin',
            password_hash=generate_password_hash(admin_password),
            full_name='System Administrator',
            role='ADMIN'
        )
        db.session.add(admin_user)
        print(f"Created default admin user - username: admin, password: {admin_password}")
    
    db.session.commit()

    # Ensure inventory schema (add reorder fields for products if missing) - safe for dev
    try:
        from sqlalchemy import text
        with db.engine.begin() as conn:
            cols = [row[1] for row in conn.execute(text("PRAGMA table_info('product')")).fetchall()]
            if 'reorder_threshold' not in cols:
                conn.execute(text("ALTER TABLE product ADD COLUMN reorder_threshold INTEGER NOT NULL DEFAULT 5"))
            if 'reorder_to' not in cols:
                conn.execute(text("ALTER TABLE product ADD COLUMN reorder_to INTEGER NOT NULL DEFAULT 20"))
    except Exception:
        # If running migrations or DB locked, skip; DB should be migrated by user in production
        pass