from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from flask import render_template, request, redirect, url_for, flash, Response, jsonify
import json
from flask_login import login_required, current_user

from app.extensions import db
from app.models.customer import Customer
from app.models.inventory import Product
from app.models.repair import Device, RepairPartUsed
from app.services.authz import roles_required
from app.services.codes import generate_customer_code, generate_ticket_number
from app.services.financials import safe_decimal, recompute_repair_financials
from app.services.stock import stock_out, StockError
from app.services.guards import require_tech_can_view_details

from . import repairs_bp


@repairs_bp.route("/")
@login_required
@roles_required("ADMIN", "TECH")
def repairs():
    """List and search repairs"""
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    page = request.args.get("page", 1, type=int)

    query = Device.query

    if q:
        # search by ticket number or customer name or device model
        query = query.join(Customer, Device.customer_id == Customer.id).filter(
            (Device.ticket_number.ilike(f"%{q}%")) |
            (Customer.name.ilike(f"%{q}%")) |
            (Device.model.ilike(f"%{q}%"))
        )

    if status:
        query = query.filter(Device.status == status)

    if date_from:
        try:
            df = datetime.fromisoformat(date_from).date()
            query = query.filter(Device.received_date >= df)
        except Exception:
            pass

    if date_to:
        try:
            dt = datetime.fromisoformat(date_to).date()
            query = query.filter(Device.received_date <= dt)
        except Exception:
            pass

    devices_pagination = query.order_by(Device.id.desc()).paginate(page=page, per_page=50)

    return render_template("repairs/repairs.html", devices=devices_pagination, q=q, status=status, date_from=date_from, date_to=date_to)


@repairs_bp.route('/search/api', methods=['GET'])
@login_required
@roles_required('ADMIN', 'TECH')
def repairs_search_api():
    """Autocomplete/search API for repairs"""
    q = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)

    if not q or len(q) < 2:
        return Response(json.dumps([]), mimetype='application/json')

    results = (
        Device.query.join(Customer, Device.customer_id == Customer.id)
        .filter(
            (Device.ticket_number.ilike(f"%{q}%")) |
            (Customer.name.ilike(f"%{q}%"))
        )
        .order_by(Device.id.desc())
        .limit(limit)
        .all()
    )

    payload = [
        {
            'id': d.id,
            'ticket': d.ticket_number,
            'customer': d.owner.name if d.owner else None,
            'device': f"{d.brand or ''} {d.model or ''}".strip()
        }
        for d in results
    ]
    return Response(json.dumps(payload), mimetype='application/json')


@repairs_bp.route("/add", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN", "TECH")
def add_repair():
    customers = Customer.query.order_by(Customer.name).all()
    
    if request.method == "POST":
        # Get customer selection mode
        customer_mode = request.form.get("customer_mode", "existing")
        customer = None
        
        if customer_mode == "existing":
            # Use existing customer
            customer_id = request.form.get("existing_customer_id")
            if not customer_id:
                flash("Please select a customer.", "danger")
                return redirect(url_for("repairs.add_repair"))
            customer = Customer.query.get_or_404(int(customer_id))
        else:
            # Create or update customer
            skip_phone = request.form.get("skip_phone", "no") == "yes"
            phone = (request.form.get("customer_phone") or "").strip()
            
            # Validate phone if provided
            if phone:
                # Check if phone is 11 digits
                if not phone.isdigit() or len(phone) != 11:
                    flash("Phone number must be exactly 11 digits.", "danger")
                    return redirect(url_for("repairs.add_repair"))
            elif not skip_phone:
                flash("Please provide a phone number or check 'Skip phone number entry'.", "danger")
                return redirect(url_for("repairs.add_repair"))
            else:
                # Generate a temporary phone placeholder when skipped
                import uuid
                phone = f"SKIP{uuid.uuid4().hex[:7].upper()}"[:11]
            
            customer = Customer.query.filter_by(phone=phone).first()
            
            if customer:
                # Update existing customer if requested
                update_customer = request.form.get("update_customer_details", "no") == "yes"
                if update_customer:
                    customer.name = (request.form.get("customer_name") or "").strip() or customer.name
                    customer.email = (request.form.get("customer_email") or "").strip() or customer.email
                    customer.address = (request.form.get("customer_address") or "").strip() or customer.address
                    customer.business_name = (request.form.get("business_name") or "").strip() or customer.business_name
                    customer.customer_type = request.form.get("customer_type", customer.customer_type)
            else:
                # Create new customer
                customer = Customer(
                    customer_code=generate_customer_code(),
                    name=(request.form.get("customer_name") or "").strip() or "Unknown",
                    email=(request.form.get("customer_email") or "").strip() or None,
                    phone=phone,
                    address=(request.form.get("customer_address") or "").strip() or None,
                    business_name=(request.form.get("business_name") or "").strip() or None,
                    customer_type=request.form.get("customer_type", "Individual"),
                    created_by_user_id=current_user.id,
                )
                db.session.add(customer)
            db.session.flush()

        device_type = request.form.get("device_type")
        if not device_type:
            flash("Device type is required.", "danger")
            return redirect(url_for("repairs.add_repair"))

        # Handle multiple service types (comma-separated)
        service_types = request.form.getlist("service_type")
        service_type_str = ", ".join(service_types) if service_types else "Hardware Repair"
        
        # Duplicate detection: if serial number provided, check active tickets for same customer
        serial_number = (request.form.get("serial_number") or "").strip() or None
        if serial_number:
            existing_dev = Device.query.filter(Device.serial_number == serial_number, Device.customer_id == customer.id).filter(Device.status != 'Completed').first()
            if existing_dev:
                flash("A repair ticket for this serial number already exists and is not completed.", "danger")
                return redirect(url_for("repairs.add_repair"))

        # Also check recent similar tickets (same customer, same device_type and issue) in last 7 days
        issue_desc = (request.form.get("issue_description") or "").strip()
        if not serial_number and issue_desc:
            recent = datetime.utcnow() - timedelta(days=7)
            similar = Device.query.filter(Device.customer_id == customer.id, Device.device_type == request.form.get("device_type"), Device.issue_description == issue_desc, Device.created_at >= recent).first()
            if similar:
                flash("A similar repair ticket was created recently for this customer.", "warning")
                return redirect(url_for("repairs.add_repair"))

        # capture original deposit input to detect overpayment attempts
        orig_deposit = safe_decimal(request.form.get("deposit_paid"), "0.00")

        d = Device(
            ticket_number=generate_ticket_number(),
            customer_id=customer.id,
            device_type=device_type,
            brand=(request.form.get("brand") or "").strip() or None,
            model=(request.form.get("model") or "").strip() or None,
            serial_number=(request.form.get("serial_number") or "").strip() or None,
            issue_description=(request.form.get("issue_description") or "").strip(),
            symptoms=(request.form.get("symptoms") or "").strip() or None,
            device_age=(request.form.get("device_age") or "").strip() or None,
            accessories=(request.form.get("accessories") or "").strip() or None,
            service_type=service_type_str,
            is_warranty_repair=request.form.get("is_warranty_repair", "no"),

            status=request.form.get("status", "Received"),
            priority=request.form.get("priority", "Normal"),
            diagnostic_fee=safe_decimal(request.form.get("diagnostic_fee"), "0.00"),
            repair_cost=safe_decimal(request.form.get("repair_cost"), "0.00"),
            deposit_paid=orig_deposit,
            parts_cost=Decimal("0.00"),
            created_by_user_id=current_user.id,
            technician_name_override=(request.form.get("technician_name_override") or "").strip() or None,
        )

        recompute_repair_financials(d)
        db.session.add(d)
        db.session.commit()

        # If original deposit exceeded total cost it will have been capped
        if orig_deposit > d.deposit_paid:
            flash(f"Deposit amount exceeded the total cost and was capped to ₱{d.deposit_paid}", "warning")
        else:
            flash(f"Repair ticket created: {d.ticket_number}", "success")
        # Redirect to print ticket with option to add receipt
        return redirect(url_for("repairs.print_ticket", device_id=d.id))

    return render_template("repairs/add_repairs.html", customers=customers)


@repairs_bp.route("/<int:device_id>")
@login_required
@roles_required("ADMIN", "TECH")
@require_tech_can_view_details
def repair_detail(device_id: int):
    device = Device.query.get_or_404(device_id)
    days_in_shop = (date.today() - device.received_date).days if device.received_date else 0
    products = Product.query.filter_by(is_active=True, is_service=False).order_by(Product.name).all()
    return render_template("repairs/repair_detail.html", device=device, days_in_shop=days_in_shop, products=products)


@repairs_bp.route("/<int:device_id>/status", methods=["POST"])
@login_required
@roles_required("ADMIN", "TECH")
def update_status(device_id: int):
    device = Device.query.get_or_404(device_id)
    device.status = request.form.get("status", device.status)
    device.technician_notes = request.form.get("technician_notes", device.technician_notes)
    device.solution_applied = request.form.get("solution_applied", device.solution_applied)

    if device.status == "Completed":
        device.actual_completion = date.today()

    # Optional: update labor/diagnostic costs
    device.diagnostic_fee = safe_decimal(request.form.get("diagnostic_fee"), str(device.diagnostic_fee or "0.00"))
    device.repair_cost = safe_decimal(request.form.get("repair_cost"), str(device.repair_cost or "0.00"))

    recompute_repair_financials(device)
    db.session.commit()

    flash("Repair updated.", "success")
    return redirect(url_for("repairs.repair_detail", device_id=device.id))


@repairs_bp.route("/<int:device_id>/parts/add", methods=["POST"])
@login_required
@roles_required("ADMIN", "TECH")
def add_part_used(device_id: int):
    device = Device.query.get_or_404(device_id)

    product_id = int(request.form.get("product_id"))
    qty = int(request.form.get("qty") or 0)
    if qty <= 0:
        flash("Quantity must be greater than 0.", "danger")
        return redirect(url_for("repairs.repair_detail", device_id=device.id))

    product = Product.query.get_or_404(product_id)

    unit_price = safe_decimal(product.sell_price, "0.00")
    line_total = unit_price * Decimal(qty)

    # Deduct stock first (strict)
    try:
        stock_out(product, qty, reference_type="REPAIR", reference_id=device.id, notes=f"Ticket {device.ticket_number}")
    except StockError as e:
        db.session.rollback()
        flash(str(e), "danger")
        return redirect(url_for("repairs.repair_detail", device_id=device.id))

    db.session.add(RepairPartUsed(
        device_id=device.id,
        product_id=product.id,
        qty=qty,
        unit_price=unit_price,
        line_total=line_total,
    ))

    # Update device parts_cost from sum of rows
    parts_total = sum((row.line_total for row in device.parts_used_rows), start=Decimal("0.00"))
    parts_total += line_total  # include new row (device.parts_used_rows not refreshed yet)
    device.parts_cost = parts_total

    recompute_repair_financials(device)

    db.session.commit()

    # Fetch the newly added part for frontend convenience
    new_part = RepairPartUsed.query.filter_by(device_id=device.id).order_by(RepairPartUsed.id.desc()).first()

    # Return JSON for AJAX requests, redirect for form submits
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({
            "success": True,
            "message": "Part added successfully",
            "parts_cost": str(device.parts_cost),
            "total_cost": str(device.total_cost),
            "balance_due": str(device.balance_due),
            "deposit_paid": str(device.deposit_paid),
            "payment_status": device.payment_status,
            "part": {
                "id": new_part.id if new_part else None,
                "product_name": new_part.product.name if new_part and new_part.product else product.name,
                "qty": new_part.qty if new_part else qty,
                "unit_price": str(new_part.unit_price) if new_part else str(unit_price),
                "line_total": str(new_part.line_total) if new_part else str(line_total)
            }
        })
    else:
        flash("Part added and stock deducted.", "success")
        return redirect(url_for("repairs.repair_detail", device_id=device.id))


@repairs_bp.route("/<int:device_id>/print", methods=["GET"])
@login_required
@roles_required("ADMIN", "TECH")
def print_ticket(device_id: int):
    """Print repair ticket"""
    device = Device.query.get_or_404(device_id)
    return render_template("repairs/print_ticket.html", device=device, now=datetime.now())


@repairs_bp.route("/<int:device_id>/payment", methods=["POST"])
@login_required
@roles_required("ADMIN", "TECH")
def add_payment(device_id: int):
    """Record payment for a repair"""
    device = Device.query.get_or_404(device_id)
    
    amount = safe_decimal(request.form.get("amount"), "0.00")
    payment_method = request.form.get("payment_method", "Unknown")
    apply_as_deposit = request.form.get('apply_as_deposit', 'yes') == 'yes'
    
    if amount <= 0:
        flash("Payment amount must be greater than 0.", "danger")
        return redirect(url_for("repairs.repair_detail", device_id=device.id))

    current_deposit = safe_decimal(device.deposit_paid, "0.00")
    remaining = safe_decimal(device.total_cost, "0.00") - current_deposit

    if remaining <= 0:
        flash("This repair is already fully paid. No additional payment accepted.", "warning")
        return redirect(url_for("repairs.repair_detail", device_id=device.id))

    if apply_as_deposit:
        # Accept only up to remaining; cap any overpayment
        accepted = amount if amount <= remaining else remaining
        device.deposit_paid = current_deposit + accepted
        recompute_repair_financials(device)
        db.session.commit()

        if accepted < amount:
            flash(f"Payment exceeded remaining amount. Accepted ₱{accepted} and capped to total. Excess ₱{(amount - accepted)} not recorded.", "warning")
        else:
            flash(f"Payment of ₱{accepted} recorded via {payment_method}", "success")

        return redirect(url_for("repairs.repair_detail", device_id=device.id))
    else:
        # Treat payment as settlement: require amount to be >= remaining to settle
        if amount < remaining:
            flash(f"Amount is not enough to settle the repair (remaining ₱{remaining}). Please provide sufficient amount or apply as deposit.", "danger")
            return redirect(url_for("repairs.repair_detail", device_id=device.id))

        # Mark as paid without changing deposit_paid
        device.balance_due = Decimal('0.00')
        device.payment_status = 'Paid'
        db.session.commit()

        flash(f"Repair settled (marked as Paid) via {payment_method}. Deposit not modified.", "success")
        return redirect(url_for("repairs.repair_detail", device_id=device.id))


@repairs_bp.route("/<int:device_id>/receipt", methods=["GET"])
@login_required
@roles_required("ADMIN", "TECH")
def print_receipt(device_id: int):
    """Print payment receipt for a repair"""
    device = Device.query.get_or_404(device_id)
    
    return render_template("repairs/receipt.html", device=device, now=datetime.now())


@repairs_bp.route("/<int:device_id>/parts/<int:part_id>/update-qty", methods=["POST"])
@login_required
@roles_required("ADMIN", "TECH")
def update_part_qty(device_id: int, part_id: int):
    """Update quantity of a part used in repair"""
    device = Device.query.get_or_404(device_id)
    part = RepairPartUsed.query.get_or_404(part_id)
    
    if part.device_id != device_id:
        return jsonify({"success": False, "message": "Part does not belong to this device"}), 400
    
    try:
        new_qty = int(request.form.get("qty") or 0)
    except Exception:
        return jsonify({"success": False, "message": "Invalid quantity"}), 400
    
    if new_qty <= 0:
        return jsonify({"success": False, "message": "Quantity must be greater than 0"}), 400
    
    old_qty = part.qty
    qty_diff = new_qty - old_qty
    
    # Adjust stock if quantity changed
    if qty_diff != 0:
        try:
            if qty_diff > 0:  # Need more stock
                stock_out(part.product, qty_diff, reference_type="REPAIR", reference_id=device.id, notes=f"Qty adjustment for {part.product.name}")
            else:  # Return stock
                from app.services.stock import stock_in as stock_in_func
                stock_in_func(part.product, abs(qty_diff), notes=f"Qty adjustment return for {part.product.name}")
        except StockError as e:
            db.session.rollback()
            return jsonify({"success": False, "message": str(e)}), 400
    
    # Update part quantity and line total
    part.qty = new_qty
    part.line_total = part.unit_price * Decimal(new_qty)
    
    # Recalculate device parts cost
    parts_total = sum((row.line_total for row in device.parts_used_rows), start=Decimal("0.00"))
    device.parts_cost = parts_total
    
    recompute_repair_financials(device)
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "line_total": str(part.line_total),
        "parts_cost": str(device.parts_cost),
        "total_cost": str(device.total_cost),
        "balance_due": str(device.balance_due),
        "deposit_paid": str(device.deposit_paid),
        "payment_status": device.payment_status
    })


@repairs_bp.route("/<int:device_id>/parts/<int:part_id>/update-price", methods=["POST"])
@login_required
@roles_required("ADMIN", "TECH")
def update_part_price(device_id: int, part_id: int):
    """Update unit price of a part used in repair (AJAX)"""
    device = Device.query.get_or_404(device_id)
    part = RepairPartUsed.query.get_or_404(part_id)

    if part.device_id != device_id:
        return jsonify({"success": False, "message": "Part does not belong to this device"}), 400

    # Accept price from form or JSON
    price_raw = request.form.get("price") if request.form.get("price") is not None else (request.json.get("price") if request.json else None)
    try:
        new_price = safe_decimal(price_raw, str(part.unit_price))
    except Exception:
        return jsonify({"success": False, "message": "Invalid price"}), 400

    if new_price < Decimal("0.00"):
        return jsonify({"success": False, "message": "Price must be non-negative"}), 400

    part.unit_price = new_price
    part.line_total = (part.unit_price * Decimal(part.qty))

    # Recalculate device parts cost
    parts_total = sum((row.line_total for row in device.parts_used_rows), start=Decimal("0.00"))
    device.parts_cost = parts_total

    recompute_repair_financials(device)
    db.session.commit()

    return jsonify({
        "success": True,
        "line_total": str(part.line_total),
        "parts_cost": str(device.parts_cost),
        "total_cost": str(device.total_cost),
        "balance_due": str(device.balance_due),
        "deposit_paid": str(device.deposit_paid),
        "payment_status": device.payment_status
    })


@repairs_bp.route("/<int:device_id>/delete", methods=["POST"])
@login_required
@roles_required("ADMIN")
def delete_repair(device_id: int):
    """Delete a repair ticket (ADMIN only). Restores stock for used parts."""
    device = Device.query.get_or_404(device_id)

    try:
        # Restore stock for parts used
        from app.services.stock import stock_in
        for part in list(device.parts_used_rows):
            try:
                stock_in(part.product, part.qty, notes=f"Restore stock - deleted repair {device.ticket_number}")
            except Exception:
                # if stock_in fails, continue to attempt deletion but log/rollback if necessary
                pass

        db.session.delete(device)
        db.session.commit()
        flash(f"Repair {device.ticket_number} deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting repair: {str(e)}", "danger")

    return redirect(url_for("repairs.repairs"))