from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from flask import render_template, request, redirect, url_for, flash, Response
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
    if request.method == "POST":
        # Customer info (simple: lookup by phone)
        phone = (request.form.get("customer_phone") or "").strip()
        if not phone:
            flash("Customer phone is required.", "danger")
            return redirect(url_for("repairs.add_repair"))

        customer = Customer.query.filter_by(phone=phone).first()
        if not customer:
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
            deposit_paid=safe_decimal(request.form.get("deposit_paid"), "0.00"),
            parts_cost=Decimal("0.00"),
            created_by_user_id=current_user.id,
            technician_name_override=(request.form.get("technician_name_override") or "").strip() or None,
        )

        recompute_repair_financials(d)
        db.session.add(d)
        db.session.commit()

        flash(f"Repair ticket created: {d.ticket_number}", "success")
        return redirect(url_for("repairs.print_ticket", device_id=d.id))

    return render_template("repairs/add_repairs.html")


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
    
    if amount <= 0:
        flash("Payment amount must be greater than 0.", "danger")
        return redirect(url_for("repairs.repair_detail", device_id=device.id))
    
    device.deposit_paid = safe_decimal(device.deposit_paid, "0.00") + amount
    recompute_repair_financials(device)
    
    db.session.commit()
    flash(f"Payment of {amount} recorded via {payment_method}", "success")
    return redirect(url_for("repairs.repair_detail", device_id=device.id))