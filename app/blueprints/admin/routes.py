"""
Admin routes for email and system configuration
"""
from __future__ import annotations
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from datetime import time

from app.extensions import db
from app.models.email_config import SMTPSettings, EmailReport
from app.services.authz import admin_required
from app.services.email_service import EmailService
from app.services.report_service import ReportService
from app.services.excel_service import ExcelReportService

from . import admin_bp


@admin_bp.route('/email-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def email_settings():
    """Admin page for email configuration"""
    config = SMTPSettings.get_active_config()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'save':
            if not config:
                config = SMTPSettings()
                db.session.add(config)
            
            config.smtp_server = request.form.get('smtp_server', '').strip()
            config.smtp_port = int(request.form.get('smtp_port', 587))
            config.email_address = request.form.get('email_address', '').strip()
            config.use_tls = request.form.get('use_tls') == 'on'
            config.frequency = request.form.get('frequency', 'daily')
            
            # Parse time
            time_str = request.form.get('auto_send_time', '09:00')
            try:
                hour, minute = map(int, time_str.split(':'))
                config.auto_send_time = time(hour, minute)
            except (ValueError, IndexError):
                flash('Invalid time format. Use HH:MM', 'danger')
                return redirect(url_for('admin.email_settings'))
            
            # Update password if provided
            password = request.form.get('email_password', '').strip()
            if password:
                config.set_password(password)
            
            db.session.commit()
            flash('Email settings updated successfully', 'success')
            return redirect(url_for('admin.email_settings'))
        
        elif action == 'toggle':
            if config:
                config.is_enabled = not config.is_enabled
                db.session.commit()
                status = 'enabled' if config.is_enabled else 'disabled'
                flash(f'Email reporting {status}', 'success')
            return redirect(url_for('admin.email_settings'))
        
        elif action == 'test':
            if config and config.smtp_server and config.email_address:
                # Generate test report
                from datetime import date
                start_date = date.today()
                end_date = date.today()
                
                report_data = ReportService.generate_report_data(start_date, end_date, 'daily')
                excel_bytes = ExcelReportService.create_report(report_data)
                excel_filename = ExcelReportService.generate_filename(start_date, end_date)
                
                # Send test email
                success, message = EmailService.send_report(
                    config,
                    config.email_address,
                    report_data,
                    excel_bytes,
                    excel_filename
                )
                
                if success:
                    flash('Test email sent successfully to ' + config.email_address, 'success')
                else:
                    flash(f'Failed to send test email: {message}', 'danger')
            else:
                flash('Please configure SMTP settings first', 'warning')
            
            return redirect(url_for('admin.email_settings'))
    
    # Calculate next send time
    next_send_time = None
    if config and config.is_enabled:
        from datetime import datetime
        now = datetime.now()
        scheduled_time = datetime.combine(now.date(), config.auto_send_time)
        
        if scheduled_time <= now:
            # Next send is tomorrow
            from datetime import timedelta
            scheduled_time += timedelta(days=1)
        
        next_send_time = scheduled_time
    
    return render_template(
        'admin/email_settings.html',
        config=config,
        next_send_time=next_send_time
    )


@admin_bp.route('/email-logs')
@login_required
@admin_required
def email_logs():
    """View email sending logs"""
    page = request.args.get('page', 1, type=int)
    
    logs = (
        EmailReport.query
        .order_by(EmailReport.created_at.desc())
        .paginate(page=page, per_page=20)
    )
    
    return render_template(
        'admin/email_logs.html',
        logs=logs
    )


@admin_bp.route('/email-logs/<int:log_id>', methods=['GET'])
@login_required
@admin_required
def email_log_detail(log_id):
    """View detailed email log"""
    log = EmailReport.query.get_or_404(log_id)
    
    return render_template(
        'admin/email_log_detail.html',
        log=log
    )


@admin_bp.route('/email-test-data', methods=['GET'])
@login_required
@admin_required
def email_test_data():
    """Generate and display test report data"""
    from datetime import date
    
    start_date = date.today()
    end_date = date.today()
    
    report_data = ReportService.generate_report_data(start_date, end_date, 'daily')
    
    return jsonify(report_data)
