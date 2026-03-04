from __future__ import annotations

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.extensions import db
from app.models.customer import Customer, Department
from app.models.repair import Device
from app.models.sales import Sale
from app.services.authz import roles_required
from app.services.codes import generate_customer_code
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
                Customer.business_name.ilike(f"%{q}%"),
                Customer.phone.ilike(f"%{q}%"),
                Customer.customer_code.ilike(f"%{q}%"),
                Customer.email.ilike(f"%{q}%")
            )
        )
    
    customers_list = (
        query.order_by(Customer.name)
        .paginate(page=page, per_page=50, error_out=False)
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

    # Paginate repairs & sales on the detail page to avoid loading large histories
    from app.services.pagination import get_page_args
    repairs_page = request.args.get('repairs_page', 1, type=int)
    sales_page = request.args.get('sales_page', 1, type=int)

    repairs = Device.query.filter_by(customer_id=customer_id).order_by(Device.id.desc()).paginate(page=repairs_page, per_page=10, error_out=False)

    # Calculate customer statistics (include sales)
    total_repairs = repairs.total if getattr(repairs, 'total', None) is not None else len(repairs)
    completed_repairs = len([r for r in (repairs.items if getattr(repairs, 'items', None) is not None else repairs) if r.status == "Completed"])

    # Repairs spending (sum over the paginated set only to keep computation cheap on detail page)
    total_repairs_spent = sum((r.total_cost or 0) for r in (repairs.items if getattr(repairs, 'items', None) is not None else repairs))
    repairs_balance = sum((r.balance_due or 0) for r in (repairs.items if getattr(repairs, 'items', None) is not None else repairs) if r.payment_status in ("Pending", "Partial"))

    # Sales associated with this customer (paginated)
    sales = Sale.query.filter_by(customer_id=customer_id).order_by(Sale.created_at.desc()).paginate(page=sales_page, per_page=10, error_out=False)
    total_sales_spent = sum((s.total or 0) for s in (sales.items if getattr(sales, 'items', None) is not None else sales))
    sales_balance = 0
    for s in (sales.items if getattr(sales, 'items', None) is not None else sales):
        paid = sum((p.amount or 0) for p in s.payments)
        outstanding = (s.total or 0) - paid
        if outstanding > 0 and s.status in ("PARTIAL", "DRAFT"):
            sales_balance += outstanding

    total_spent = total_repairs_spent + total_sales_spent
    balance_due = repairs_balance + sales_balance
    
    return render_template(
        "customers/customer_detail.html",
        customer=customer,
        repairs=repairs,
        sales=sales,
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
        skip_phone = request.form.get("skip_phone", "no") == "yes"
        phone = (request.form.get("phone") or "").strip()
        
        # Validate phone if provided
        if phone:
            # Check if phone is 11 digits
            if not phone.isdigit() or len(phone) != 11:
                flash("Phone number must be exactly 11 digits.", "danger")
                return render_template("customers/edit_customer.html", customer=customer)
            customer.phone = phone
        elif not skip_phone:
            customer.phone = customer.phone  # Keep existing phone
        else:
            # Allow empty phone by generating a placeholder
            import uuid
            customer.phone = f"SKIP{uuid.uuid4().hex[:7].upper()}"[:11]
        
        customer.email = (request.form.get("email") or "").strip() or None
        customer.address = (request.form.get("address") or "").strip() or None
        customer.business_name = (request.form.get("business_name") or "").strip() or None
        customer.customer_type = request.form.get("customer_type", "Individual")
        
        if not customer.name:
            flash("Name is required.", "danger")
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
@roles_required("ADMIN", "SALES", "TECH")
def search_api():
    """API endpoint for customer search (for autocomplete)"""
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", 10, type=int)
    
    if len(q) < 2:
        return jsonify([])
    
    customers_list = Customer.query.filter(
        or_(
            Customer.name.ilike(f"%{q}%"),
            Customer.business_name.ilike(f"%{q}%"),
            Customer.phone.ilike(f"%{q}%"),
            Customer.customer_code.ilike(f"%{q}%")
        )
    ).limit(limit).all()
    
    return jsonify([
        {
            "id": c.id,
            "name": c.name,
            "business_name": c.business_name,
            "phone": c.phone,
            "code": c.customer_code,
            "email": c.email
        }
        for c in customers_list
    ])


@customers_bp.route("/add", methods=["POST"])
@login_required
@roles_required("ADMIN", "SALES")
def add_customer():
    """Add a new customer (API endpoint for POS)"""
    customer_type = (request.form.get("customer_type") or "Individual").strip()
    skip_phone = request.form.get("skip_phone", "no") == "yes"
    phone = (request.form.get("phone") or "").strip()
    email = (request.form.get("email") or "").strip() or None
    address = (request.form.get("address") or "").strip() or None
    
    # Get name based on customer type
    if customer_type == "Individual":
        name = (request.form.get("name") or "").strip()
        business_name = None
    else:
        # For Business/Government, use company_name or fall back to business_name
        name = (request.form.get("company_name") or request.form.get("name") or "").strip()
        business_name = (request.form.get("company_name") or "").strip() or None
    
    if not name:
        return jsonify({"success": False, "message": "Name is required"}), 400
    
    # Validate phone if provided
    if phone:
        if not phone.isdigit() or len(phone) != 11:
            return jsonify({"success": False, "message": "Phone number must be exactly 11 digits"}), 400
    elif not skip_phone:
        return jsonify({"success": False, "message": "Please provide a phone number or select skip phone option"}), 400
    else:
        # Generate a temporary phone placeholder when skipped
        import uuid
        phone = f"SKIP{uuid.uuid4().hex[:7].upper()}"[:11]
    
    # Check if customer already exists by phone
    existing = Customer.query.filter_by(phone=phone).first()
    if existing:
        return jsonify({"success": False, "message": "Customer with this phone already exists"}), 400
    
    try:
        customer = Customer(
            customer_code=generate_customer_code(),
            name=name,
            phone=phone,
            email=email,
            address=address,
            customer_type=customer_type,
            business_name=business_name,
            created_by_user_id=current_user.id
        )
        db.session.add(customer)
        db.session.flush()
        
        # Create department if details provided and customer is Business/Government
        department = None
        if customer_type != "Individual":
            dept_name = (request.form.get("department_name") or "").strip()
            if dept_name:
                from app.models.customer import Department
                department = Department(
                    customer_id=customer.id,
                    name=dept_name,
                    contact_person=(request.form.get("department_contact") or "").strip() or None,
                    phone=(request.form.get("department_phone") or "").strip() or None,
                    email=(request.form.get("department_email") or "").strip() or None,
                    is_active=True
                )
                db.session.add(department)
                db.session.flush()
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "phone": customer.phone,
                "email": customer.email,
                "customer_type": customer.customer_type,
                "business_name": business_name
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@customers_bp.route("/<int:customer_id>/quick-repair", methods=["POST"])
@login_required
@roles_required("ADMIN", "TECH")
def quick_repair(customer_id: int):
    """Quick repair creation directly from customer details page"""
    if not _tech_can_access_customer(customer_id):
        return render_template("errors/403.html"), 403
    
    customer = Customer.query.get_or_404(customer_id)
    
    # Get or create department if specified
    department_id = None
    department_choice = request.form.get("department_id", "").strip()
    
    if customer.customer_type != "Individual" and department_choice:
        if department_choice == "__new__":
            # Create new department
            from app.models.customer import Department
            dept_name = (request.form.get("new_department_name") or "").strip()
            dept_contact = (request.form.get("new_department_contact") or "").strip()
            
            if not dept_name:
                flash("Department name is required.", "danger")
                return redirect(url_for("customers.customer_detail", customer_id=customer_id))
            
            department = Department(
                customer_id=customer_id,
                name=dept_name,
                contact_person=dept_contact or None,
                is_active=True
            )
            db.session.add(department)
            db.session.flush()
            department_id = department.id
        else:
            # Use existing department
            try:
                department_id = int(department_choice)
            except (ValueError, TypeError):
                pass
    
    # Redirect to repair creation with customer pre-filled
    from app.services.codes import generate_ticket_number
    
    device_type = (request.form.get("device_type") or "").strip()
    brand = (request.form.get("brand") or "").strip() or None
    model = (request.form.get("model") or "").strip() or None
    issue_description = (request.form.get("issue_description") or "").strip()
    
    if not device_type or not issue_description:
        flash("Device type and issue description are required.", "danger")
        return redirect(url_for("customers.customer_detail", customer_id=customer_id))
    
    # Create the repair directly
    from app.models.repair import Device
    from app.services.financials import recompute_repair_financials
    from decimal import Decimal
    
    try:
        device = Device(
            ticket_number=generate_ticket_number(),
            customer_id=customer_id,
            department_id=department_id,
            device_type=device_type,
            brand=brand,
            model=model,
            issue_description=issue_description,
            status="Received",
            priority="Normal",
            diagnostic_fee=Decimal("0.00"),
            repair_cost=Decimal("0.00"),
            parts_cost=Decimal("0.00"),
            created_by_user_id=current_user.id,
        )
        recompute_repair_financials(device)
        db.session.add(device)
        db.session.commit()
        
        flash(f"Repair ticket created: {device.ticket_number}", "success")
        return redirect(url_for("repairs.repair_detail", device_id=device.id))
    except Exception as e:
        db.session.rollback()
        flash(f"Error creating repair: {str(e)}", "danger")
        return redirect(url_for("customers.customer_detail", customer_id=customer_id))


@customers_bp.route("/<int:customer_id>/quick-sale", methods=["POST"])
@login_required
@roles_required("ADMIN", "SALES")
def quick_sale(customer_id: int):
    """Quick sale creation directly from customer details page"""
    customer = Customer.query.get_or_404(customer_id)
    
    # Get or create department if specified
    department_id = None
    department_choice = request.form.get("department_id", "").strip()
    
    if customer.customer_type != "Individual" and department_choice:
        if department_choice == "__new__":
            # Create new department
            from app.models.customer import Department
            dept_name = (request.form.get("new_department_name") or "").strip()
            dept_contact = (request.form.get("new_department_contact") or "").strip()
            
            if not dept_name:
                flash("Department name is required.", "danger")
                return redirect(url_for("customers.customer_detail", customer_id=customer_id))
            
            department = Department(
                customer_id=customer_id,
                name=dept_name,
                contact_person=dept_contact or None,
                is_active=True
            )
            db.session.add(department)
            db.session.flush()
            department_id = department.id
        else:
            # Use existing department
            try:
                department_id = int(department_choice)
            except (ValueError, TypeError):
                pass
    
    # Create a minimal sale record
    from app.services.codes import generate_ticket_number
    from app.models.sales import Sale
    from decimal import Decimal
    import uuid
    
    try:
        notes = (request.form.get("notes") or "").strip() or "Quick sale from customer detail"
        
        sale = Sale(
            invoice_no=f"JC-{uuid.uuid4().hex[:8].upper()}",
            customer_id=customer_id,
            department_id=department_id,
            status="DRAFT",
            notes=notes,
            subtotal=Decimal("0.00"),
            discount=Decimal("0.00"),
            tax=Decimal("0.00"),
            total=Decimal("0.00")
        )
        db.session.add(sale)
        db.session.commit()
        
        flash(f"Sale created: {sale.invoice_no}. You can now add items in the POS system.", "success")
        return redirect(url_for("sales.pos", sale_id=sale.id))
    except Exception as e:
        db.session.rollback()
        flash(f"Error creating sale: {str(e)}", "danger")
        return redirect(url_for("customers.customer_detail", customer_id=customer_id))


@customers_bp.route("/<int:customer_id>/departments-api", methods=["GET"])
@login_required
@roles_required("ADMIN", "TECH", "SALES")
def departments_api(customer_id: int):
    """API endpoint to fetch customer departments (for dynamic UI updates)"""
    customer = Customer.query.get_or_404(customer_id)
    
    return jsonify({
        "customer_id": customer.id,
        "customer_type": customer.customer_type,
        "departments": [
            {
                "id": dept.id,
                "name": dept.name,
                "contact_person": dept.contact_person,
                "is_active": dept.is_active
            }
            for dept in customer.departments if dept.is_active
        ]
    })


@customers_bp.route("/<int:customer_id>/departments", methods=["POST"])
@login_required
@roles_required("ADMIN", "TECH", "SALES")
def create_department(customer_id: int):
    """API endpoint to create a new department for a customer"""
    customer = Customer.query.get_or_404(customer_id)
    data = request.get_json()
    
    # Validate required fields
    if not data.get("name"):
        return jsonify({"error": "Department name is required"}), 400
    
    dept = Department(
        customer_id=customer_id,
        name=data.get("name"),
        contact_person=data.get("contact_person"),
        phone=data.get("phone"),
        email=data.get("email"),
        is_active=data.get("is_active", True)
    )
    
    db.session.add(dept)
    db.session.commit()
    
    return jsonify({
        "id": dept.id,
        "name": dept.name,
        "contact_person": dept.contact_person,
        "phone": dept.phone,
        "email": dept.email,
        "is_active": dept.is_active
    }), 201


@customers_bp.route("/<int:customer_id>/departments/<int:dept_id>/api", methods=["GET"])
@login_required
@roles_required("ADMIN", "TECH", "SALES")
def get_department(customer_id: int, dept_id: int):
    """API endpoint to fetch a single department"""
    customer = Customer.query.get_or_404(customer_id)
    dept = Department.query.filter_by(id=dept_id, customer_id=customer_id).first_or_404()
    
    return jsonify({
        "id": dept.id,
        "name": dept.name,
        "contact_person": dept.contact_person,
        "phone": dept.phone,
        "email": dept.email,
        "is_active": dept.is_active
    })


@customers_bp.route("/<int:customer_id>/departments/<int:dept_id>", methods=["PUT"])
@login_required
@roles_required("ADMIN", "TECH", "SALES")
def update_department(customer_id: int, dept_id: int):
    """API endpoint to update a department"""
    customer = Customer.query.get_or_404(customer_id)
    dept = Department.query.filter_by(id=dept_id, customer_id=customer_id).first_or_404()
    data = request.get_json()
    
    # Update fields
    if "name" in data:
        if not data["name"]:
            return jsonify({"error": "Department name cannot be empty"}), 400
        dept.name = data["name"]
    
    if "contact_person" in data:
        dept.contact_person = data["contact_person"]
    
    if "phone" in data:
        dept.phone = data["phone"]
    
    if "email" in data:
        dept.email = data["email"]
    
    if "is_active" in data:
        dept.is_active = data["is_active"]
    
    db.session.commit()
    
    return jsonify({
        "id": dept.id,
        "name": dept.name,
        "contact_person": dept.contact_person,
        "phone": dept.phone,
        "email": dept.email,
        "is_active": dept.is_active
    })


@customers_bp.route("/<int:customer_id>/departments/<int:dept_id>", methods=["DELETE"])
@login_required
@roles_required("ADMIN", "TECH", "SALES")
def delete_department(customer_id: int, dept_id: int):
    """API endpoint to delete a department"""
    customer = Customer.query.get_or_404(customer_id)
    dept = Department.query.filter_by(id=dept_id, customer_id=customer_id).first_or_404()
    
    db.session.delete(dept)
    db.session.commit()
    
    return "", 204

