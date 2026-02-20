from __future__ import annotations

from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from sqlalchemy import or_
from string import ascii_letters, digits
import secrets

from app.extensions import db
from app.models.user import User
from app.services.authz import roles_required
from app.services.security import is_valid_password, get_password_strength

from . import users_bp


def generate_temp_password(length=12):
    """Generate a secure temporary password"""
    characters = ascii_letters + digits
    return ''.join(secrets.choice(characters) for _ in range(length))


@users_bp.route("/")
@login_required
@roles_required("ADMIN")
def users():
    """List all users"""
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    
    query = User.query
    if q:
        query = query.filter(
            or_(
                User.username.ilike(f"%{q}%"),
                User.full_name.ilike(f"%{q}%"),
                User.role.ilike(f"%{q}%")
            )
        )
    
    users_list = (
        query.order_by(User.created_at.desc())
        .paginate(page=page, per_page=50, error_out=False)
    )
    
    return render_template(
        "users/users.html",
        users=users_list,
        q=q
    )


@users_bp.route("/create", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN")
def create_user():
    """Create a new user account"""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip().lower()
        full_name = (request.form.get("full_name") or "").strip()
        role = request.form.get("role", "SALES")
        
        # Validation
        if not username or not full_name:
            flash("Username and full name are required.", "danger")
            return render_template(
                "users/create_user.html",
                roles=["ADMIN", "SALES", "TECH"]
            )
        
        if len(username) < 3:
            flash("Username must be at least 3 characters.", "danger")
            return render_template(
                "users/create_user.html",
                roles=["ADMIN", "SALES", "TECH"],
                form_data=request.form
            )
        
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return render_template(
                "users/create_user.html",
                roles=["ADMIN", "SALES", "TECH"],
                form_data=request.form
            )
        
        # Generate temporary password
        temp_password = generate_temp_password()
        
        # Create user
        user = User(
            username=username,
            full_name=full_name,
            role=role,
            is_active=True
        )
        user.set_password(temp_password)
        
        db.session.add(user)
        db.session.commit()
        
        # Store in session temporarily for display on success page
        session['new_user_username'] = username
        session['new_user_password'] = temp_password
        session['new_user_full_name'] = full_name
        session['new_user_role'] = role
        session.modified = True
        
        return redirect(url_for("users.user_created"))
    
    return render_template(
        "users/create_user.html",
        roles=["ADMIN", "SALES", "TECH"]
    )


@users_bp.route("/created", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN")
def user_created():
    """Display newly created user credentials with copy button"""
    username = session.pop('new_user_username', None)
    temp_password = session.pop('new_user_password', None)
    full_name = session.pop('new_user_full_name', None)
    role = session.pop('new_user_role', None)
    
    if not username or not temp_password:
        flash("Invalid session. Please create a new user.", "warning")
        return redirect(url_for("users.create_user"))
    
    if request.method == "POST":
        # User clicked "Done" or similar
        return redirect(url_for("users.users"))
    
    return render_template(
        "users/user_created.html",
        username=username,
        password=temp_password,
        full_name=full_name,
        role=role
    )


@users_bp.route("/<int:user_id>/reset-password", methods=["POST"])
@login_required
@roles_required("ADMIN")
def reset_password(user_id: int):
    """Reset user password to temporary one"""
    user = User.query.get_or_404(user_id)
    
    temp_password = generate_temp_password()
    user.set_password(temp_password)
    db.session.commit()
    
    # Store in session temporarily
    session['reset_user_username'] = user.username
    session['reset_user_password'] = temp_password
    session.modified = True
    
    return redirect(url_for("users.password_reset"))


@users_bp.route("/password-reset-done", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN")
def password_reset():
    """Display password reset credentials"""
    username = session.pop('reset_user_username', None)
    temp_password = session.pop('reset_user_password', None)
    
    if not username or not temp_password:
        flash("Invalid session.", "warning")
        return redirect(url_for("users.users"))
    
    if request.method == "POST":
        return redirect(url_for("users.users"))
    
    return render_template(
        "users/password_reset_done.html",
        username=username,
        password=temp_password
    )


@users_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN")
def edit_user(user_id: int):
    """Edit user details"""
    user = User.query.get_or_404(user_id)
    
    # Prevent editing own role/status
    is_self = (user.id == current_user.id) if current_user else False
    
    if request.method == "POST":
        user.full_name = (request.form.get("full_name") or "").strip()
        
        # Only allow changing role/status if not editing self or if current user is ADMIN
        if (not is_self) or (current_user and current_user.role == "ADMIN"):
            new_role = request.form.get("role", user.role)
            if new_role in ["ADMIN", "SALES", "TECH"]:
                user.role = new_role
            
            new_active = request.form.get("is_active") == "on"
            user.is_active = new_active
        
        if not user.full_name:
            flash("Full name is required.", "danger")
            return render_template(
                "users/edit_user.html",
                user=user,
                roles=["ADMIN", "SALES", "TECH"],
                is_self=is_self
            )
        
        db.session.commit()
        flash(f"User '{user.username}' updated successfully.", "success")
        return redirect(url_for("users.users"))
    
    return render_template(
        "users/edit_user.html",
        user=user,
        roles=["ADMIN", "SALES", "TECH"],
        is_self=is_self
    )


@users_bp.route("/<int:user_id>/delete", methods=["POST"])
@login_required
@roles_required("ADMIN")
def delete_user(user_id: int):
    """Delete a user account"""
    user = User.query.get_or_404(user_id)
    
    # Prevent self-deletion
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("users.users"))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f"User '{username}' has been deleted.", "success")
    return redirect(url_for("users.users"))


@users_bp.route("/<int:user_id>/toggle-status", methods=["POST"])
@login_required
@roles_required("ADMIN")
def toggle_status(user_id: int):
    """Toggle user active/inactive status"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deactivating self
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "danger")
        return redirect(url_for("users.users"))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = "activated" if user.is_active else "deactivated"
    flash(f"User '{user.username}' has been {status}.", "success")
    return redirect(url_for("users.users"))


@users_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Allow logged-in users to change their password"""
    if request.method == "POST":
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        
        # Validate current password
        if not current_password:
            flash("Current password is required.", "danger")
            return render_template("users/change_password.html")
        
        if not current_user.check_password(current_password):
            flash("Current password is incorrect.", "danger")
            return render_template("users/change_password.html")
        
        # Validate new password is provided
        if not new_password:
            flash("New password is required.", "danger")
            return render_template("users/change_password.html")
        
        # Validate password confirmation
        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return render_template("users/change_password.html")
        
        # Validate new password is not same as current
        if current_user.check_password(new_password):
            flash("New password must be different from current password.", "danger")
            return render_template("users/change_password.html")
        
        # Validate password strength
        if not is_valid_password(new_password):
            score, message = get_password_strength(new_password)
            flash(f"Password does not meet security requirements. {message}", "danger")
            return render_template("users/change_password.html")
        
        # Update password
        try:
            current_user.set_password(new_password)
            db.session.commit()
            flash("Your password has been changed successfully.", "success")
            return redirect(url_for("core.dashboard"))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while changing your password: {str(e)}", "danger")
            return render_template("users/change_password.html")
    
    return render_template("users/change_password.html")
