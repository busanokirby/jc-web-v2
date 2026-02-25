from __future__ import annotations

from decimal import Decimal
from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    current_app as app,
    Response,
)
from flask_login import login_required
from datetime import datetime, timedelta, date, time
import json
from io import StringIO
import csv
import logging

logger = logging.getLogger(__name__)

from app.extensions import db
from app.models.customer import Customer
from app.models.inventory import Product
from app.models.sales import Sale, SaleItem, SalePayment
from app.models.repair import RepairPartUsed, Device
from sqlalchemy.orm import joinedload
from app.services.authz import roles_required
from app.services.guards import require_pos_enabled
from app.services.codes import generate_invoice_no
from app.services.stock import stock_out, stock_in, StockError
from app.services.financials import safe_decimal
from app.services.pagination import get_page_args, paginate_sequence
from app.services.report_service import ReportService
from sqlalchemy import func, or_, and_

from . import sales_bp


@sales_bp.route("/pos", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN", "SALES")
@require_pos_enabled
def pos():
    """
    Point of Sale - multi-item cart with optional customer details
    """
    products_list = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    customers = Customer.query.order_by(Customer.name).all()

    if request.method == "POST":
        try:
            items_json = request.form.get("items", "[]")
            items = json.loads(items_json)
            if not items:
                flash("Your cart is empty. Please add items before completing the sale.", "danger")
                return redirect(url_for("sales.pos"))
            
            # Optional customer info
            customer_id = request.form.get("customer_id")
            if customer_id:
                try:
                    customer_id = int(customer_id)
                except (ValueError, TypeError):
                    customer_id = None
            
            discount = safe_decimal(request.form.get("discount") or "0", "0.00")
            payment_method = request.form.get("payment_method", "Cash")

            # validate mutually-exclusive options from POS
            apply_as_deposit = request.form.get('apply_as_deposit', 'no') == 'yes'
            claim_on_credit = request.form.get('claim_on_credit', 'no') == 'yes'
            if apply_as_deposit and claim_on_credit:
                flash('Cannot record a deposit and claim on credit at the same time.', 'danger')
                return redirect(url_for('sales.pos'))
            
            subtotal = Decimal("0.00")
            items_with_products = []
            
            for item in items:
                product_id = int(item.get("product_id"))
                qty = int(item.get("qty"))
                item_price = safe_decimal(item.get("price"), "0.00")  # Allow price override
                
                if qty <= 0:
                    flash("Invalid quantity. Please enter a quantity greater than 0.", "danger")
                    return redirect(url_for("sales.pos"))
                
                product = Product.query.get_or_404(product_id)
                
                # Check stock only for non-services
                if not product.is_service and qty > product.stock_on_hand:
                    flash(f"Not enough stock for {product.name}. Available: {product.stock_on_hand}", "danger")
                    return redirect(url_for("sales.pos"))
                
                # Use provided price or product's sell price
                unit_price = item_price if item_price is not None else safe_decimal(product.sell_price, "0.00")
                line_total = unit_price * Decimal(qty)
                subtotal += line_total
                
                items_with_products.append({
                    "product": product,
                    "qty": qty,
                    "unit_price": unit_price,
                    "line_total": line_total
                })
            
            total = max(Decimal("0.00"), subtotal - discount)
            
            # claim_on_credit already handled above from the submitted form

            # Create sale with optional customer
            sale = Sale(
                invoice_no=generate_invoice_no(),
                customer_id=customer_id,
                status="PAID" if not claim_on_credit else "PARTIAL",
                subtotal=subtotal,
                discount=discount,
                tax=Decimal("0.00"),
                total=total,
                claimed_on_credit=claim_on_credit
            )
            db.session.add(sale)
            db.session.flush()
            
            # Add items to sale
            for item_data in items_with_products:
                product = item_data["product"]
                qty = item_data["qty"]
                unit_price = item_data["unit_price"]
                line_total = item_data["line_total"]
                
                sale_item = SaleItem(
                    sale_id=sale.id,
                    product_id=product.id,
                    qty=qty,
                    unit_price=unit_price,
                    line_total=line_total
                )
                db.session.add(sale_item)
                
                # Deduct stock for non-services
                if not product.is_service:
                    try:
                        stock_out(product, qty, reference_type="SALE", reference_id=sale.id, notes=f"Invoice {sale.invoice_no}")
                    except StockError as e:
                        db.session.rollback()
                        flash(f"Stock error: {str(e)}", "danger")
                        return redirect(url_for("sales.pos"))
            
            # Record payment unless this is a credited sale (no immediate payment)
            if not claim_on_credit:
                db.session.add(SalePayment(sale_id=sale.id, amount=total, method=payment_method))

            db.session.commit()
            
            flash(f"Sale completed! Invoice: {sale.invoice_no}", "success")
            return redirect(url_for("sales.invoice", sale_id=sale.id))
            
        except json.JSONDecodeError:
            flash("Invalid cart data. Please try again.", "danger")
            return redirect(url_for("sales.pos"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error processing sale: {str(e)}", "danger")
            return redirect(url_for("sales.pos"))

    # Convert products to JSON for frontend
    products_json = [{
        "id": p.id,
        "name": p.name,
        "sku": p.sku,
        "sell_price": float(p.sell_price),
        "stock_on_hand": p.stock_on_hand,
        "is_service": p.is_service
    } for p in products_list]
    
    return render_template("sales/pos.html", products=products_json, customers=customers)


@sales_bp.route("/list")
@login_required
@roles_required("ADMIN", "SALES")
def sales_list():
    # Optional search query + filters
    q = (request.args.get('q') or '').strip()
    status = (request.args.get('status') or '').strip()
    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')

    # Parse optional dates (YYYY-MM-DD)
    date_from = None
    date_to = None
    try:
        if date_from_str:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
        if date_to_str:
            # include entire day
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
    except Exception:
        date_from = date_to = None

    # Run DB-backed multi-field ilike search whenever there's a query or explicit filters
    if q or status or date_from or date_to:
        pattern = f"%{q}%" if q else None
        page, per_page = get_page_args()
        fetch_limit = max(per_page * 10, 200)  # cap how many rows each DB query will return for merging

        # Sales queries (use joinedload to avoid N+1 when building history)
        try:
            sales_base = Sale.query.options(
                joinedload(Sale.items).joinedload(SaleItem.product),  # type: ignore[arg-type]
                joinedload(Sale.customer),  # type: ignore[arg-type]
                joinedload(Sale.payments)  # type: ignore[arg-type]
            )
            if status:
                sales_base = sales_base.filter(Sale.status.ilike(status.upper()))
            if date_from:
                sales_base = sales_base.filter(Sale.created_at >= date_from)
            if date_to:
                sales_base = sales_base.filter(Sale.created_at <= date_to)

            sales_invoice = []
            sales_customer = []
            sales_product = []
            if pattern:
                sales_invoice = sales_base.filter(Sale.invoice_no.ilike(pattern)).order_by(Sale.created_at.desc()).limit(fetch_limit).all()
                sales_customer = (
                    sales_base.join(Customer)
                    .filter(
                        or_(
                            Customer.name.ilike(pattern),
                            Customer.phone.ilike(pattern),
                            Customer.customer_code.ilike(pattern)
                        )
                    )
                    .order_by(Sale.created_at.desc())
                    .limit(fetch_limit)
                    .all()
                )
                sales_product = (
                    sales_base.join(SaleItem).join(Product)
                    .filter(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern)))
                    .order_by(Sale.created_at.desc())
                    .distinct()
                    .limit(fetch_limit)
                    .all()
                )

                # Also allow searching by payment method on the sale (e.g., Cash)
                sales_payment = (
                    sales_base.join(SalePayment).filter(SalePayment.method.ilike(pattern)).order_by(Sale.created_at.desc()).distinct().limit(fetch_limit).all()
                )
                # include payment-method matches in merge
                sales_invoice = sales_invoice + sales_payment if sales_payment else sales_invoice
            else:
                # no textual query, but filters present -> pull matching sales
                sales_invoice = sales_base.order_by(Sale.created_at.desc()).limit(fetch_limit).all()

            # Merge and deduplicate
            sales_set = {}
            for s in sales_invoice + sales_customer + sales_product:
                sales_set[s.id] = s
            sales = list(sales_set.values())
        except Exception as e:
            app.logger.error(f"Sales search error: {str(e)}")
            sales = []

        # Devices / Repairs queries (eager-load parts + owner)
        try:
            devices_base = Device.query.options(
                joinedload(Device.parts_used_rows).joinedload(RepairPartUsed.product),  # type: ignore[arg-type]
                joinedload(Device.owner),  # type: ignore[arg-type]
            )
            if status:
                # Device.payment_status is Title-cased (e.g. 'Paid')
                devices_base = devices_base.filter(Device.payment_status.ilike(status.capitalize()))
            if date_from:
                devices_base = devices_base.filter(
                    or_(Device.actual_completion >= (date_from.date() if hasattr(date_from, 'date') else None), Device.created_at >= date_from)
                )
            if date_to:
                devices_base = devices_base.filter(
                    or_(Device.actual_completion <= (date_to.date() if hasattr(date_to, 'date') else None), Device.created_at <= date_to)
                )

            devices_ticket = []
            devices_service = []
            devices_customer = []
            devices_product = []
            if pattern:
                devices_ticket = devices_base.filter(Device.ticket_number.ilike(pattern)).order_by(Device.created_at.desc()).limit(fetch_limit).all()
                devices_service = devices_base.filter(Device.service_type.ilike(pattern)).order_by(Device.created_at.desc()).limit(fetch_limit).all()
                devices_customer = (
                    devices_base.join(Customer)
                    .filter(
                        or_(
                            Customer.name.ilike(pattern),
                            Customer.phone.ilike(pattern),
                            Customer.customer_code.ilike(pattern)
                        )
                    )
                    .order_by(Device.created_at.desc())
                    .limit(fetch_limit)
                    .all()
                )
                devices_product = devices_base.join(RepairPartUsed).join(Product).filter(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern))).order_by(Device.created_at.desc()).distinct().limit(fetch_limit).all()
            else:
                devices_ticket = devices_base.order_by(Device.created_at.desc()).limit(fetch_limit).all()

            # Merge and deduplicate
            devices_set = {}
            for d in devices_ticket + devices_service + devices_customer + devices_product:
                devices_set[d.id] = d
            devices = list(devices_set.values())
        except Exception as e:
            app.logger.error(f"Devices search error: {str(e)}")
            devices = []
    else:
        # Regular recent sales (eager load items and product to avoid N+1)
        try:
            sales = Sale.query.options(
                joinedload(Sale.items).joinedload(SaleItem.product),  # type: ignore[arg-type]
                joinedload(Sale.customer),  # type: ignore[arg-type]
                joinedload(Sale.payments)  # type: ignore[arg-type]
            ).order_by(Sale.created_at.desc()).limit(200).all()
        except Exception as e:
            app.logger.error(f"Sales fetch error: {str(e)}")
            sales = []

        # Devices that have monetary transactions (parts, repair cost) or released on credit
        try:
            devices = Device.query.options(
                joinedload(Device.parts_used_rows).joinedload(RepairPartUsed.product),  # type: ignore[arg-type]
                joinedload(Device.owner),  # type: ignore[arg-type]
            ).filter(
                or_(
                    Device.parts_used_rows.any(),
                    Device.total_cost > 0,
                    Device.claimed_on_credit == True
                )
            ).order_by(Device.created_at.desc()).limit(200).all()
        except Exception as e:
            app.logger.error(f"Devices fetch error: {str(e)}")
            devices = []

    # Build unified history entries with a searchable text blob
    history = []
    try:
        for s in sales:
            try:
                items_count = sum(item.qty for item in (s.items or [])) if s.items else 0
                # Build a searchable string containing invoice, customer name/code/phone and product SKUs/names
                parts_text = ' '.join(
                    f"{item.product.sku or ''} {item.product.name or ''}" for item in (s.items or []) if item.product
                )
                customer_name = ''
                company_name = ''
                if getattr(s, 'customer', None):
                    customer_name = s.customer.name or ''
                    company_name = s.customer.business_name or ''
                customer_phone = s.customer.phone if getattr(s, 'customer', None) and getattr(s.customer, 'phone', None) else ''
                customer_code = s.customer.customer_code if getattr(s, 'customer', None) and getattr(s.customer, 'customer_code', None) else ''
                payment_methods = ' '.join((p.method or '') for p in (s.payments or []))
                search_text = f"{s.invoice_no or ''} {customer_name} {customer_code} {customer_phone} {parts_text} {payment_methods}"

                # compute payments total and remaining balance for sale
                payments_total = sum((p.amount or 0) for p in (s.payments or []))
                balance_due = float((s.total or 0) - payments_total)

                history.append({
                    'type': 'sale',
                    'invoice': s.invoice_no,
                    'created_at': s.created_at,
                    'items_count': items_count,
                    'subtotal': float(s.subtotal or 0),
                    'discount': float(s.discount or 0),
                    'total': float(s.total or 0),
                    'status': s.status,
                    'id': s.id,
                    'balance_due': balance_due,
                    'payments_total': payments_total,
                    'claimed_on_credit': getattr(s, 'claimed_on_credit', False),
                    'search_text': search_text,
                    'customer_name': customer_name,
                    'company_name': company_name,
                })
            except Exception as e:
                app.logger.warning(f"Error building sale history entry: {str(e)}")
                continue
    except Exception as e:
        app.logger.error(f"Error processing sales: {str(e)}")

    try:
        for d in devices:
            try:
                parts_qty = sum(p.qty for p in (d.parts_used_rows or [])) if d.parts_used_rows else 0
                parts_text = ' '.join(
                    f"{p.product.sku or ''} {p.product.name or ''}" for p in (d.parts_used_rows or []) if p.product
                )
                customer_name = ''
                company_name = ''
                if getattr(d, 'owner', None):
                    customer_name = d.owner.name or ''
                    company_name = d.owner.business_name or ''
                # Prefer actual_completion as the 'created_at' for repair transactions when available
                # Normalize `actual_completion` (Date) to a datetime so sorting between sales (datetime)
                # and repairs (date) does not raise TypeError.
                if d.actual_completion:
                    # actual_completion is a date object (no time) --> convert to datetime at midnight
                    try:
                        from datetime import datetime as _dt, time as _time
                        if isinstance(d.actual_completion, _dt):
                            tx_date = d.actual_completion
                        else:
                            tx_date = _dt.combine(d.actual_completion, _dt.min.time())
                    except Exception:
                        # Fallback to created_at if anything unexpected
                        tx_date = d.created_at
                else:
                    tx_date = d.created_at

                search_text = f"{d.ticket_number or ''} {customer_name} {parts_text} {d.service_type or ''}"
                history.append({
                    'type': 'repair',
                    'invoice': d.ticket_number,
                    'created_at': tx_date,
                    'items_count': parts_qty,
                    'subtotal': float(d.total_cost or 0),
                    'discount': 0.0,
                    'total': float(d.total_cost or 0),
                    'status': d.payment_status,
                    'id': d.id,
                    'balance_due': float(d.balance_due or 0),
                    'payments_total': float((d.total_cost or 0) - (d.balance_due or 0)),
                    'claimed_on_credit': getattr(d, 'claimed_on_credit', False),
                    'search_text': search_text,
                    'customer_name': customer_name,
                    'company_name': company_name,
                })
            except Exception as e:
                app.logger.warning(f"Error building device history entry: {str(e)}")
                continue
    except Exception as e:
        app.logger.error(f"Error processing devices: {str(e)}")

    # Sort by created_at desc and build a paginated result from the merged history.
    try:
        history_sorted = sorted(history, key=lambda x: x.get('created_at') or datetime.min, reverse=True)
    except TypeError:
        # Defensive fallback: if mixed/unexpected types remain, coerce to string timestamp and sort
        app.logger.warning('Mixed date/datetime types detected when sorting history; applying fallback ordering.')
        history_sorted = sorted(history, key=lambda x: str(x.get('created_at') or ''), reverse=True)

    # Paginate the in-memory merged history so the UI treats it the same as other list views
    page, per_page = get_page_args()
    history_pagination = paginate_sequence(history_sorted, page=page, per_page=per_page)

    # Credit summary for quick access (keep lightweight queries)
    credits_q = Device.query.filter(Device.claimed_on_credit == True)
    credits_count = credits_q.count()
    credits_total = float(sum((d.balance_due or 0) for d in credits_q.limit(500).all()))

    return render_template("sales/sales_list.html", history=history_pagination, q=q, credits_count=credits_count, credits_total=credits_total)


@sales_bp.route('/credits')
@login_required
@roles_required('ADMIN', 'SALES')
def credits():
    """List devices released on credit (outstanding claims)."""
    devices = Device.query.filter(Device.claimed_on_credit == True).order_by(Device.created_at.desc()).all()
    sales_on_credit = (
        Sale.query
        .options(joinedload(Sale.payments), joinedload(Sale.customer))  # type: ignore[arg-type]
        .filter(Sale.claimed_on_credit == True)
        .order_by(Sale.created_at.desc())
        .all()
    )

    history = []

    # include repair device credits
    for d in devices:
        parts_qty = sum(p.qty for p in d.parts_used_rows) if d.parts_used_rows else 0
        parts_text = ' '.join(
            f"{p.product.sku or ''} {p.product.name or ''}" for p in d.parts_used_rows if p.product
        )
        search_text = f"{d.ticket_number or ''} {parts_text}"
        cust_name = ''
        comp_name = ''
        if getattr(d, 'owner', None):
            cust_name = d.owner.name or ''
            comp_name = d.owner.business_name or ''
        history.append({
            'type': 'repair',
            'invoice': d.ticket_number,
            'created_at': d.created_at,
            'items_count': parts_qty,
            'subtotal': float(d.total_cost or 0),
            'discount': 0.0,
            'total': float(d.total_cost or 0),
            'status': d.payment_status,
            'id': d.id,
            'balance_due': float(d.balance_due or 0),
            'payments_total': float((d.total_cost or 0) - (d.balance_due or 0)),
            'claimed_on_credit': True,
            'search_text': search_text,
            'customer_name': cust_name,
            'company_name': comp_name,
        })

    # include sales on credit
    for s in sales_on_credit:
        items_count = sum(item.qty for item in s.items) if s.items else 0
        parts_text = ' '.join(f"{item.product.sku or ''} {item.product.name or ''}" for item in s.items if item.product)
        payments_total = sum((p.amount or 0) for p in (s.payments or []))
        balance_due = float((s.total or 0) - payments_total)
        search_text = f"{s.invoice_no or ''} {parts_text}"
        cust_name = ''
        comp_name = ''
        if getattr(s, 'customer', None):
            cust_name = s.customer.name or ''
            comp_name = s.customer.business_name or ''
        history.append({
            'type': 'sale',
            'invoice': s.invoice_no,
            'created_at': s.created_at,
            'items_count': items_count,
            'subtotal': float(s.subtotal or 0),
            'discount': float(s.discount or 0),
            'total': float(s.total or 0),
            'status': s.status,
            'id': s.id,
            'balance_due': balance_due,
            'payments_total': payments_total,
            'claimed_on_credit': True,
            'search_text': search_text,
            'customer_name': cust_name,
            'company_name': comp_name,
        })

    # Total credits and paginate the in-memory history for consistent UI behavior
    credits_count = len(history)
    credits_total = 0.0
    for d in devices:
        credits_total += float(d.balance_due or 0)
    for s in sales_on_credit:
        credits_total += float((s.total or 0) - sum((p.amount or 0) for p in (s.payments or [])))

    # Paginate the in-memory list so the sales_list template can rely on a Pagination object
    page, per_page = get_page_args()
    history_pagination = paginate_sequence(history, page=page, per_page=per_page)

    # Render the same sales_list template but indicate credits_only to adjust header/UI
    return render_template('sales/sales_list.html', history=history_pagination, q='', credits_only=True, credits_count=credits_count, credits_total=credits_total)


@sales_bp.route('/<int:sale_id>/payment', methods=['POST'])
@login_required
@roles_required('ADMIN', 'SALES')
def add_payment_for_sale(sale_id: int):
    """Record payment for a sale that was released on credit (quick-action from credits list)."""
    sale = Sale.query.get_or_404(sale_id)

    amount = safe_decimal(request.form.get('amount'), '0.00')
    payment_method = request.form.get('payment_method', 'Unknown')

    if amount <= 0:
        flash('Payment amount must be greater than 0.', 'danger')
        return redirect(url_for('sales.sales_list'))

    payments_total = sum((p.amount or 0) for p in (sale.payments or []))
    remaining = (sale.total or 0) - payments_total

    if remaining <= 0:
        flash('This sale is already fully paid. No additional payment accepted.', 'warning')
        return redirect(url_for('sales.invoice', sale_id=sale.id))

    # Accept only up to remaining; cap any overpayment
    accepted = amount if amount <= remaining else remaining
    db.session.add(SalePayment(sale_id=sale.id, amount=accepted, method=payment_method))

    # Update sale status and clear claim if fully paid
    new_paid_total = payments_total + accepted
    if new_paid_total >= (sale.total or 0):
        sale.status = 'PAID'
        sale.claimed_on_credit = False
    else:
        sale.status = 'PARTIAL'

    db.session.commit()

    if accepted < amount:
        flash(f'Payment exceeded remaining amount. Accepted ₱{accepted} and capped to total. Excess ₱{(amount - accepted)} not recorded.', 'warning')
    else:
        flash(f'Payment of ₱{accepted} recorded via {payment_method}', 'success')

    return redirect(url_for('sales.invoice', sale_id=sale.id))


@sales_bp.route("/<int:sale_id>/invoice")
@login_required
@roles_required("ADMIN", "SALES")
def invoice(sale_id: int):
    sale = Sale.query.get_or_404(sale_id)
    # compute payment totals and remaining balance
    payments_total = sum((p.amount or 0) for p in (sale.payments or []))
    balance_due = float((sale.total or 0) - payments_total)
    return render_template(
        "sales/invoice.html",
        sale=sale,
        payments_total=payments_total,
        balance_due=balance_due,
        credit_claim=False,
    )


@sales_bp.route("/<int:sale_id>/credit-claim")
@login_required
@roles_required("ADMIN", "SALES")
def credit_claim(sale_id: int):
    """Render a claim-on-credit receipt for a sale.

    Only accessible for sales that have been marked as claimed on credit.
    The template reuses the invoice layout but adds a prominent label and
    balance information.
    """
    sale = Sale.query.get_or_404(sale_id)
    if not sale.claimed_on_credit:
        flash('This sale is not marked as claimed on credit.', 'warning')
        return redirect(url_for('sales.sales_list'))
    payments_total = sum((p.amount or 0) for p in (sale.payments or []))
    balance_due = float((sale.total or 0) - payments_total)
    return render_template(
        "sales/invoice.html",
        sale=sale,
        payments_total=payments_total,
        balance_due=balance_due,
        credit_claim=True,
    )


@sales_bp.route("/daily-sales")
@login_required
@roles_required("ADMIN", "SALES")
def daily_sales():
    """Daily Sales Report = payments received on the selected date (sales + repairs)."""

    # parse and validate date parameter
    date_str = request.args.get('date', '')
    today_date = datetime.now().date()
    if date_str:
        try:
            selected_date = datetime.fromisoformat(date_str).date()
        except Exception:
            selected_date = today_date
    else:
        selected_date = today_date

    if selected_date > today_date:
        return redirect(url_for('sales.daily_sales', date=today_date.isoformat()))

    # bounds for datetime comparisons
    start_dt = datetime.combine(selected_date, datetime.min.time())
    end_dt = datetime.combine(selected_date, datetime.max.time())

    records = []
    total_payments = Decimal("0.00")
    partial_payment_count = 0
    partial_payment_total = Decimal("0.00")

    # =========================================================
    # SALES: use SalePayment.paid_at (with strict date filtering)
    # =========================================================
    # CRITICAL FIX: Removed fallback to Sale.created_at in filter
    # This prevents double-counting of transactions
    # Now only includes payments with actual paid_at timestamps
    sale_payments = (
        SalePayment.query
        .join(Sale, SalePayment.sale_id == Sale.id)
        .options(
            joinedload(SalePayment.sale).joinedload(Sale.customer),  # type: ignore[arg-type]
            joinedload(SalePayment.sale).joinedload(Sale.items).joinedload(SaleItem.product),  # type: ignore[arg-type]
            joinedload(SalePayment.sale).joinedload(Sale.payments),  # type: ignore[arg-type]
        )
        .filter(
            SalePayment.paid_at.isnot(None),  # Strict: paid_at must be set
            func.date(SalePayment.paid_at) == selected_date,
            Sale.status.in_(['PAID', 'PARTIAL']),
        )
        .order_by(SalePayment.paid_at.desc(), SalePayment.id.desc())
        .all()
    )

    for pay in sale_payments:
        sale = pay.sale
        if not sale:
            continue

        cust_obj = sale.customer
        # ensure we have a simple string so template prints nicely
        if cust_obj:
            cust_name = cust_obj.display_name
        else:
            cust_name = 'Walk-in Customer'

        # Ignore cancelled/drafts if you use them
        if (sale.status or "").upper() in ["VOID", "DRAFT"]:
            continue

        amount = Decimal(pay.amount or 0)
        if amount <= 0:
                # Validation: skip negative/zero amounts
                logger.warning(
                    f"Skipping invalid payment {pay.id}: amount={amount}, sale={pay.sale_id}"
                )
                continue  # Only include received payments (positive amounts)
        desc = ""
        if sale.items:
            desc = ", ".join(
                f"{it.qty}×{it.product.name if it.product else 'Unknown'}"
                for it in sale.items
            )

        # Determine if sale is still partial AFTER payments (overall state)
        sale_total = Decimal(sale.total or 0)

        def _payment_within_report(p):
            paid_at = getattr(p, "paid_at", None)
            sale_created_at = getattr(p.sale, "created_at", None) if getattr(p, 'sale', None) else None
            if paid_at:
                return paid_at <= end_dt
            if sale_created_at:
                return sale_created_at <= end_dt
            return False

        total_paid_upto = Decimal(sum((p.amount or 0) for p in (sale.payments or []) if _payment_within_report(p)))
        is_partial = total_paid_upto < sale_total

        if is_partial:
            partial_payment_count += 1
            partial_payment_total += amount

        total_payments += amount

        records.append({
            "datetime": pay.paid_at or getattr(pay.sale, 'created_at', None),  # payment time (fallback to sale.created_at)
            "customer": cust_name,
            "type": "Purchase",
            "description": desc,
            "amount": float(amount),  # amount received (deposit/partial/full)
            "payment_status": "PARTIAL" if is_partial else "PAID",
            "is_partial": is_partial,
            "receipt_id": sale.id,
            "receipt_type": "sale",
        })

    # =========================================================
    # REPAIRS: keep your existing logic unless you also have a RepairPayment table.
    # (Without a repair payment timestamp, repairs can't be truly payment-date accurate.)
    # =========================================================
    repair_query = (
        Device.query
        .options(joinedload(Device.owner))  # type: ignore[arg-type]
        .filter(
            or_(
                Device.actual_completion == selected_date,
                and_(func.date(Device.deposit_paid_at) == selected_date),
                and_(
                    Device.deposit_paid > 0,
                    func.date(Device.created_at) == selected_date,
                ),
            )
        )
    )
    repairs = repair_query.all()

    for d in repairs:
        # include repairs where either fully paid, partial, or have a deposit recorded
        if getattr(d, "charge_waived", False):
            continue

        has_deposit = (d.deposit_paid or 0) > 0
        status_upper = (d.payment_status or "").capitalize()
        if (status_upper not in ['Partial', 'Paid']) and not has_deposit:
            continue

        cust = d.owner.display_name if getattr(d, 'owner', None) and d.owner else 'Walk-in Customer'
        dt = datetime.combine(d.actual_completion, datetime.min.time()) if isinstance(d.actual_completion, date) else datetime.combine(datetime.now().date(), datetime.min.time())
        desc = d.device_type or 'Repair'

        # If fully paid, count full total. Otherwise count deposit as amount received (partial)
        if status_upper == 'Paid':
            amount = Decimal(d.total_cost or 0)
            is_partial = False
        else:
            amount = Decimal(d.deposit_paid or 0)
            is_partial = True if amount > 0 else False

        if is_partial:
            partial_payment_count += 1
            partial_payment_total += amount

        total_payments += amount

        records.append({
            'datetime': dt,
            'customer': cust,
            'type': 'Repair',
            'description': desc,
            'amount': float(amount),
            'payment_status': d.payment_status,
            'is_partial': is_partial,
            'receipt_id': d.id,
            'receipt_type': 'repair'
        })

    # sort newest first
    records.sort(key=lambda r: r['datetime'], reverse=True)

    # CSV export
    fmt = request.args.get('format', 'html')
    if fmt == 'csv':
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(["Date/Time", "Customer", "Type", "Description", "Amount", "Payment Status"])
        for r in records:
            dt = r['datetime']
            dt_str = dt.strftime('%Y-%m-%d %H:%M:%S') if hasattr(dt, 'strftime') else str(dt)
            cw.writerow([dt_str, r.get('customer',''), r.get('type',''), r.get('description',''), r.get('amount',0), r.get('payment_status','')])
        output = si.getvalue()
        return Response(output, mimetype='text/csv', headers={
            'Content-Disposition': f'attachment; filename="daily_sales_{selected_date.isoformat()}.csv"'
        })

    return render_template(
        'sales/daily_sales.html',
        sales_records=records,
        total_sales=float(total_payments),
        total_partial_count=partial_payment_count,
        total_partial_amount=float(partial_payment_total),
        report_date=selected_date,
        today=today_date.isoformat(),
        now=datetime.now()
    )


@sales_bp.route("/reports")
@login_required
@roles_required("ADMIN", "SALES")
def reports():
    """Sales analytics and reporting dashboard - includes repairs in sales reporting"""
    
    # Date range filter for KPIs and charts
    days_back = request.args.get('days', 30, type=int)
    if days_back < 1:
        days_back = 30
    start_date = datetime.now() - timedelta(days=days_back)

    # Query sales within date range (used by KPI calculations and trends)
    # eager load related items to prevent N+1 issues when iterating
    sales_period = (
        Sale.query.options(joinedload(Sale.items).joinedload(SaleItem.product))  # type: ignore[arg-type]
        .filter(Sale.created_at >= start_date)
        .all()
    )

    # Daily sales moved to dedicated route `/sales/daily-sales`.
    
    # Query devices completed within date range (use actual_completion) and repair parts for product-level aggregation
    # Convert start_date (datetime) to date for comparison against Device.actual_completion (Date)
    start_date_only = start_date.date()
    repairs_period_devices = Device.query.filter(Device.actual_completion != None, Device.actual_completion >= start_date_only).all()
    # Repair parts used in the selected period (by part created_at or by device completion)
    repair_parts_period = db.session.query(RepairPartUsed).join(
        Device, RepairPartUsed.device_id == Device.id
    ).filter(Device.actual_completion != None, Device.actual_completion >= start_date_only).all()
    
    # Calculate KPIs from sales
    total_revenue = Decimal("0.00")
    total_transactions = len(sales_period)
    total_items_sold = 0
    
    for sale in sales_period:
        total_revenue += sale.total or Decimal("0.00")
        total_items_sold += sum(item.qty for item in sale.items)

    # Add repair device transactions (use device.total_cost, not individual parts, to avoid double-counting)
    repair_transactions = len(repairs_period_devices) if repairs_period_devices else 0
    repairs_total = Decimal("0.00")
    for dev in repairs_period_devices:
        repairs_total += dev.total_cost or Decimal("0.00")
        total_revenue += dev.total_cost or Decimal("0.00")
        # count parts used as items sold
        total_items_sold += sum(p.qty for p in dev.parts_used_rows) if dev.parts_used_rows else 0

    # Total transactions include both sales and repair device completions
    total_transactions += repair_transactions
    
    avg_transaction = (total_revenue / total_transactions) if total_transactions > 0 else Decimal("0.00")
    
    # Sales by payment method (from regular sales only)
    payment_methods = db.session.query(
        SalePayment.method,
        func.count(SalePayment.id).label('count'),
        func.sum(SalePayment.amount).label('total')
    ).join(Sale).filter(Sale.created_at >= start_date).group_by(SalePayment.method).all()
    
    payment_data = [{
        'method': pm.method or 'Unknown',
        'count': pm.count,
        'total': float(pm.total or 0)
    } for pm in payment_methods]
    
    # Top 10 products sold - combine sales items and repair parts using Python aggregation
    product_sales = {}
    
    # Add sales items
    for sale in sales_period:
        for item in sale.items:
            product_name = item.product.name if item.product else "Unknown"
            if product_name not in product_sales:
                product_sales[product_name] = {'qty': 0, 'amount': 0}
            product_sales[product_name]['qty'] += item.qty
            product_sales[product_name]['amount'] += float(item.line_total or 0)
    
    # Add repair parts (use parts list for product-level aggregation)
    for part in repair_parts_period:
        product_name = part.product.name if part.product else "Unknown"
        if product_name not in product_sales:
            product_sales[product_name] = {'qty': 0, 'amount': 0}
        product_sales[product_name]['qty'] += part.qty
        product_sales[product_name]['amount'] += float(part.line_total or 0)
    
    # Sort by quantity and get top 10
    top_products_data = sorted(
        [{'name': name, 'qty': data['qty'], 'amount': data['amount']} for name, data in product_sales.items()],
        key=lambda x: x['qty'],
        reverse=True
    )[:10]
    
    # Daily sales trend - combine sales and repair parts
    daily_totals = {}
    
    # Add sales transactions
    for sale in sales_period:
        date_key = sale.created_at.date()
        if date_key not in daily_totals:
            daily_totals[date_key] = {'count': 0, 'total': 0}
        daily_totals[date_key]['count'] += 1
        daily_totals[date_key]['total'] += float(sale.total or 0)
    
    # Add repair device transactions (use actual_completion as date and device.total_cost as total)
    for dev in repairs_period_devices:
        date_key = dev.actual_completion if hasattr(dev.actual_completion, 'isoformat') else dev.created_at.date()
        if isinstance(date_key, datetime):
            date_key = date_key.date()
        if date_key not in daily_totals:
            daily_totals[date_key] = {'count': 0, 'total': 0}
        daily_totals[date_key]['count'] += 1
        daily_totals[date_key]['total'] += float(dev.total_cost or 0)
    
    # Convert to sorted list
    daily_trend = [
        {'date': str(date), 'count': data['count'], 'total': data['total']}
        for date, data in sorted(daily_totals.items())
    ]
    
    return render_template(
        "sales/reports.html",
        days_back=days_back,
        total_revenue=float(total_revenue),
        repairs_total=float(repairs_total),
        repair_transactions=repair_transactions,
        total_transactions=total_transactions,
        total_items_sold=total_items_sold,
        avg_transaction=float(avg_transaction),
        payment_data=payment_data,
        top_products=top_products_data,
        daily_trend=daily_trend,
    )


@sales_bp.route('/daily', methods=['GET'])
@login_required
@roles_required('ADMIN', 'SALES')
def daily_sales_cashflow():
    """Daily sales report showing cash flow based strictly on payments

    Only payments received on the selected date are included.  Future dates
    are not permitted.
    """
    # parse date parameter
    date_str = request.args.get('date')
    today = datetime.utcnow().date()
    if date_str:
        try:
            selected = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
            selected = today
    else:
        selected = today

    if selected > today:
        flash('Cannot select a future date for daily sales.', 'warning')
        selected = today

    # query payments and eager-load related sale + customer to avoid N+1
    payments_q = (
        SalePayment.query
        .options(joinedload(SalePayment.sale).joinedload(Sale.customer))  # type: ignore[arg-type]
        .filter(func.date(SalePayment.paid_at) == selected)
        .order_by(SalePayment.paid_at.desc())
    )
    payments = payments_q.all()

    # backend aggregate for total
    total_amount = db.session.query(
        func.coalesce(func.sum(SalePayment.amount), 0)
    ).filter(func.date(SalePayment.paid_at) == selected).scalar()
    total_amount = float(total_amount or 0)

    # build entries for template
    entries = []
    for p in payments:
        sale = p.sale
        cust = sale.customer
        cust_name = (cust.name if cust and cust.name else 'Walk-in Customer')
        comp_name = cust.business_name if cust and cust.business_name else ''
        entries.append({
            'customer_name': cust_name,
            'company_name': comp_name,
            'transaction_type': 'Purchase',
            'description': sale.invoice_no,
            'amount': float(p.amount or 0),
            'paid_at': p.paid_at,
        })

    today_str = datetime.utcnow().date().isoformat()
    return render_template(
        'sales/daily_sales.html',
        date=selected,
        entries=entries,
        total_amount=total_amount,
        today_str=today_str,
    )


@sales_bp.route("/reset", methods=["POST"])
@login_required
@roles_required("ADMIN")
def reset_sales():
    """Reset all sales data (ADMIN only)"""
    confirm = request.form.get("confirm", "").lower()
    
    if confirm != "yes":
        flash("Reset cancelled", "warning")
        return redirect(url_for("sales.reports"))
    
    try:
        # Count before deletion
        sale_count = Sale.query.count()
        
        # Delete in proper order (foreign key constraints)
        SalePayment.query.delete()
        SaleItem.query.delete()
        Sale.query.delete()
        
        db.session.commit()
        flash(f"Successfully deleted {sale_count} sales and all associated data", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error resetting sales: {str(e)}", "danger")
    
    return redirect(url_for("sales.reports"))


@sales_bp.route('/<int:sale_id>/delete', methods=['POST'])
@login_required
@roles_required('ADMIN')
def delete_sale(sale_id: int):
    """Delete a single sale and restore stock for sold items (ADMIN only)."""
    sale = Sale.query.get_or_404(sale_id)

    try:
        # Restore stock for each sale item (ignore service items)
        from app.services.stock import stock_in
        invoice_no = sale.invoice_no
        for item in sale.items:
            product = item.product
            if product and not product.is_service:
                try:
                    stock_in(product, item.qty, notes=f"Restore stock - deleted sale {invoice_no}")
                except Exception:
                    # ignore stock restore failures but continue to delete
                    pass

        db.session.delete(sale)
        db.session.commit()
        flash(f"Sale {invoice_no} deleted and stock restored.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting sale: {str(e)}", "danger")

    return redirect(url_for('sales.sales_list'))

@sales_bp.route("/bulk-delete", methods=["POST"])
@login_required
@roles_required("ADMIN")
def bulk_delete_sales():
    """Bulk delete multiple sales and restore stock (ADMIN only)."""
    data = request.get_json(silent=True) or {}
    sale_ids = data.get("sale_ids", [])

    if not sale_ids or not isinstance(sale_ids, list):
        return jsonify(success=False, message="No sales selected."), 400

    try:
        from app.services.stock import stock_in

        deleted_count = 0

        for sid in sale_ids:
            sale = Sale.query.get(sid)
            if not sale:
                continue

            invoice_no = sale.invoice_no

            # Restore stock
            for item in sale.items:
                product = item.product
                if product and not product.is_service:
                    try:
                        stock_in(
                            product,
                            item.qty,
                            notes=f"Restore stock - bulk deleted sale {invoice_no}"
                        )
                    except Exception:
                        pass

            db.session.delete(sale)
            deleted_count += 1

        db.session.commit()

        return jsonify(success=True, message=f"{deleted_count} sale(s) deleted.")

    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, message=str(e)), 500