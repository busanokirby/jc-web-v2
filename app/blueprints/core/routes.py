"""
Core routes (dashboard, settings, etc.)
"""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.blueprints.core import core_bp
from app.services.authz import admin_required
from app.models.settings import Setting
from app.services.feature_flags import get_all_feature_flags
from app.extensions import db


@core_bp.route('/health')
def health():
    """Health check endpoint for monitoring and load balancers"""
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        return jsonify({'status': 'healthy', 'message': 'Application is running'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'message': str(e)}), 503


@core_bp.route('/')
@core_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    # Show a low-stock count on the dashboard Inventory card
    try:
        from app.models.inventory import Product
        low_count = Product.query.filter(Product.stock_on_hand <= Product.reorder_threshold).count()
    except Exception:
        low_count = 0
    return render_template('core/dashboard.html', low_count=low_count)


@core_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    """Admin settings page for feature flags"""
    if request.method == 'POST':
        # Update POS_ENABLED
        pos_enabled = request.form.get('pos_enabled') == 'on'
        Setting.set_value('POS_ENABLED', 'true' if pos_enabled else 'false')
        
        # Update SALES_CAN_EDIT_INVENTORY
        sales_edit_inv = request.form.get('sales_can_edit_inventory') == 'on'
        Setting.set_value('SALES_CAN_EDIT_INVENTORY', 'true' if sales_edit_inv else 'false')
        
        # Update TECH_CAN_VIEW_DETAILS
        tech_view_details = request.form.get('tech_can_view_details') == 'on'
        Setting.set_value('TECH_CAN_VIEW_DETAILS', 'true' if tech_view_details else 'false')
        
        flash('Settings updated successfully.', 'success')
        return redirect(url_for('core.settings'))
    
    # Get current feature flags
    flags = get_all_feature_flags()
    
    return render_template('core/settings.html', flags=flags)