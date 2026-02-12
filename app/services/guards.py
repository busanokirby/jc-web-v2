"""
Route guards for feature flags
"""
from functools import wraps
from flask import abort, render_template
from flask_login import current_user
from app.services.feature_flags import is_pos_enabled, is_sales_can_edit_inventory, is_tech_can_view_details


def require_pos_enabled(f):
    """
    Decorator to block access to POS routes when POS is disabled
    Returns friendly 403 page
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_pos_enabled():
            return render_template('sales/pos_disabled.html'), 403
        return f(*args, **kwargs)
    return decorated_function


def require_inventory_edit_enabled(f):
    """
    Decorator to block SALES users from inventory edit routes when toggle is OFF
    ADMIN is always allowed
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Admin can always edit
        if current_user.role == 'ADMIN':
            return f(*args, **kwargs)
        
        # For SALES, check if inventory edit is enabled
        if not is_sales_can_edit_inventory():
            return render_template('inventory/edit_disabled.html'), 403
        
        return f(*args, **kwargs)
    return decorated_function


def require_tech_can_view_details(f):
    """
    Decorator to block TECH users from viewing details when toggle is OFF
    ADMIN is always allowed
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Admin can always view details
        if current_user.role == 'ADMIN':
            return f(*args, **kwargs)
        
        # For TECH, check if viewing details is enabled
        if current_user.role == 'TECH' and not is_tech_can_view_details():
            return render_template('errors/403.html'), 403
        
        return f(*args, **kwargs)
    return decorated_function