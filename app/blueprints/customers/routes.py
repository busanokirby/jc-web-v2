from __future__ import annotations

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.extensions import db
from app.models.customer import Customer
from app.models.repair import Device
from app.services.authz import roles_required
from app.services.guards import require_tech_can_view_details

from . import customers_bp


def _get_customer_query_for_user():
    """Get base customer query filtered by user role"""
    query = Customer.query
    
    # TECH users can only see customers they created or have repairs for
    if current_user.role == "TECH":
        # Subquery for customers with repairs
        customers_with_repairs = db.session.query(Device.customer_id).distinct()
        query = query.filter(
            or_(
                Customer.created_by_user_id == current_user.id,
                Customer.id.in_(customers_with_repairs)
            )
        )
    
    return query


def _tech_can_access_customer(customer_id: int) -> bool:
    """Check if current TECH user has access to this customer"""
    if current_user.role != "TECH":
        return True
    
    customer = Customer.query.get(customer_id)
    if not customer:
        return False
    
    # TECH can access if they created it or have a repair for it
    if customer.created_by_user_id == current_user.id:
        return True
    
    # Check if TECH has any repairs for this customer
    has_repair = Device.query.filter_by(customer_id=customer_id).first() is not None
    return has_repair


@customers_bp.route("/")
@login_required
@roles_required("ADMIN", "SALES", "TECH")
@require_tech_can_view_details
def customers():
    """List all customers with search"""
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    
    query = _get_customer_query_for_user()
    if q:
        query = query.filter(
            or_(
                Customer.name.ilike(f"%{q}%"),
                Customer.phone.ilike(f"%{q}%"),
                Customer.customer_code.ilike(f"%{q}%"),
                Customer.email.ilike(f"%{q}%")
            )
        )
    
    customers_list = (
        query.order_by(Customer.name)
        .paginate(page=page, per_page=50)
    )
    
    return render_template(
        "customers/customers.html",
        customers=customers_list,
        q=q
    )


@customers_bp.route("/<int:customer_id>")
@login_required
@roles_required("ADMIN", "SALES", "TECH")
@require_tech_can_view_details
def customer_detail(customer_id: int):
    """View customer details and their repairs"""
    if not _tech_can_access_customer(customer_id):
        return render_template("errors/403.html"), 403
    
    customer = Customer.query.get_or_404(customer_id)
    repairs = Device.query.filter_by(customer_id=customer_id).order_by(Device.id.desc()).all()
    
    # Calculate customer statistics
    total_repairs = len(repairs)
    completed_repairs = len([r for r in repairs if r.status == "Completed"])
    total_spent = sum(r.total_cost for r in repairs if r.total_cost)
    balance_due = sum(r.balance_due for r in repairs if r.payment_status in ("Pending", "Partial"))
    
    return render_template(
        "customers/customer_detail.html",
        customer=customer,
        repairs=repairs,
        stats={
            "total_repairs": total_repairs,
            "completed_repairs": completed_repairs,
            "total_spent": total_spent,
            "balance_due": balance_due
        }
    )


@customers_bp.route("/<int:customer_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN", "SALES", "TECH")
def edit_customer(customer_id: int):
    """Edit customer details"""
    if not _tech_can_access_customer(customer_id):
        return render_template("errors/403.html"), 403
    
    customer = Customer.query.get_or_404(customer_id)
    
    if request.method == "POST":
        customer.name = (request.form.get("name") or "").strip()
        customer.phone = (request.form.get("phone") or "").strip()
        customer.email = (request.form.get("email") or "").strip() or None
        customer.address = (request.form.get("address") or "").strip() or None
        customer.business_name = (request.form.get("business_name") or "").strip() or None
        customer.customer_type = request.form.get("customer_type", "Individual")
        
        if not customer.name or not customer.phone:
            flash("Name and phone are required.", "danger")
            return render_template("customers/edit_customer.html", customer=customer)
        
        db.session.commit()
        flash("Customer updated successfully.", "success")
        return redirect(url_for("customers.customer_detail", customer_id=customer.id))
    
    return render_template("customers/edit_customer.html", customer=customer)


@customers_bp.route("/<int:customer_id>/delete", methods=["POST"])
@login_required
@roles_required("ADMIN")
def delete_customer(customer_id: int):
    """Delete a customer and all associated data"""
    customer = Customer.query.get_or_404(customer_id)
    customer_name = customer.name
    
    # Check if customer has repairs
    repairs = Device.query.filter_by(customer_id=customer_id).all()
    if repairs:
        pending_repairs = [r for r in repairs if r.status != "Completed"]
        if pending_repairs:
            flash(
                f"Cannot delete customer with {len(pending_repairs)} pending repairs. "
                "Please complete or re-assign them first.",
                "danger"
            )
            return redirect(url_for("customers.customer_detail", customer_id=customer_id))
    
    # Delete customer (cascade will delete repairs)
    db.session.delete(customer)
    db.session.commit()
    
    flash(f"Customer '{customer_name}' and all associated records have been deleted.", "success")
    return redirect(url_for("customers.customers"))


@customers_bp.route("/search/api", methods=["GET"])
@login_required
@roles_required("ADMIN", "SALES")
def search_api():
    """API endpoint for customer search (for autocomplete)"""
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", 10, type=int)
    
    if len(q) < 2:
        return jsonify([])
    
    customers_list = Customer.query.filter(
        or_(
            Customer.name.ilike(f"%{q}%"),
            Customer.phone.ilike(f"%{q}%"),
            Customer.customer_code.ilike(f"%{q}%")
        )
    ).limit(limit).all()
    
    return jsonify([
        {
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "code": c.customer_code,
            "email": c.email
        }
        for c in customers_list
    ])
