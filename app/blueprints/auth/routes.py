"""
Authentication routes (login/logout)
"""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.blueprints.auth import auth_bp
from app.models.user import User
from app.services.security import rate_limit, log_security_event


@auth_bp.route('/login', methods=['GET', 'POST'])
@rate_limit(max_attempts=5, window_seconds=300)  # 5 attempts per 5 minutes
def login():
    """User login page"""
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not username or not password:
            flash('Please enter both username and password.', 'danger')
            log_security_event('login_attempt_empty', username=username, ip_address=request.remote_addr)
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid username or password.', 'danger')
            log_security_event('login_failed', username=username, ip_address=request.remote_addr, details='Invalid credentials')
            return render_template('auth/login.html')
        
        if not user.is_active:
            flash('Your account has been deactivated. Please contact an administrator.', 'danger')
            log_security_event('login_attempt_inactive', user_id=user.id, username=username, ip_address=request.remote_addr)
            return render_template('auth/login.html')
        
        login_user(user, remember=remember)
        flash(f'Welcome back, {user.full_name}!', 'success')
        log_security_event('login_success', user_id=user.id, username=username, ip_address=request.remote_addr)
        
        # Redirect to next page or dashboard
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('core.dashboard'))
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """User logout"""
    if current_user.is_authenticated:
        log_security_event('logout', user_id=current_user.id, username=current_user.username, ip_address=request.remote_addr)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))