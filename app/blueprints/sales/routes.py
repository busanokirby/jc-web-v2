from __future__ import annotations

from decimal import Decimal
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from datetime import datetime, timedelta
import json

from app.extensions import db
from app.models.customer import Customer
from app.models.inventory import Product
from app.models.sales import Sale, SaleItem, SalePayment
from app.models.repair import RepairPartUsed, Device
from app.services.authz import roles_required
from app.services.guards import require_pos_enabled
from app.services.codes import generate_invoice_no
from app.services.stock import stock_out, StockError
from app.services.financials import safe_decimal
from sqlalchemy import func

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
            
            subtotal = Decimal("0.00")
            items_with_products = []
            
            for item in items:
                product_id = int(item.get("product_id"))
                qty = int(item.get("qty"))
                item_price = safe_decimal(item.get("price"), None)  # Allow price override
                
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
            
            # Create sale with optional customer
            sale = Sale(
                invoice_no=generate_invoice_no(),
                customer_id=customer_id,
                status="PAID",
                subtotal=subtotal,
                discount=discount,
                tax=Decimal("0.00"),
                total=total
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
            
            # Record payment
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
    sales = Sale.query.order_by(Sale.id.desc()).limit(200).all()
    return render_template("sales/sales_list.html", sales=sales)


@sales_bp.route("/<int:sale_id>/invoice")
@login_required
@roles_required("ADMIN", "SALES")
def invoice(sale_id: int):
    sale = Sale.query.get_or_404(sale_id)
    return render_template("sales/invoice.html", sale=sale)


@sales_bp.route("/reports")
@login_required
@roles_required("ADMIN", "SALES")
def reports():
    """Sales analytics and reporting dashboard - includes repairs in sales reporting"""
    
    # Date range filter
    days_back = request.args.get('days', 30, type=int)
    if days_back < 1:
        days_back = 30
    start_date = datetime.now() - timedelta(days=days_back)
    
    # Query sales within date range
    sales_period = Sale.query.filter(Sale.created_at >= start_date).all()
    
    # Query repair parts used within date range
    repair_parts_period = db.session.query(RepairPartUsed).join(
        Device, RepairPartUsed.device_id == Device.id
    ).filter(Device.created_at >= start_date).all()
    
    # Calculate KPIs from sales
    total_revenue = Decimal("0.00")
    total_transactions = len(sales_period)
    total_items_sold = 0
    
    for sale in sales_period:
        total_revenue += sale.total or Decimal("0.00")
        total_items_sold += sum(item.qty for item in sale.items)
    
    # Add repair parts to totals
    repair_transactions = len(repair_parts_period) if repair_parts_period else 0
    for part in repair_parts_period:
        total_revenue += part.line_total or Decimal("0.00")
        total_items_sold += part.qty
    
    # Total transactions include both sales and repair part additions
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
    
    # Top 10 products sold - combine sales and repair parts using Python aggregation
    product_sales = {}
    
    # Add sales items
    for sale in sales_period:
        for item in sale.items:
            product_name = item.product.name if item.product else "Unknown"
            if product_name not in product_sales:
                product_sales[product_name] = {'qty': 0, 'amount': 0}
            product_sales[product_name]['qty'] += item.qty
            product_sales[product_name]['amount'] += float(item.line_total or 0)
    
    # Add repair parts
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
    
    # Add repair part transactions
    for part in repair_parts_period:
        dev = db.session.query(Device).filter(Device.id == part.device_id).first()
        if dev:
            date_key = dev.created_at.date()
            if date_key not in daily_totals:
                daily_totals[date_key] = {'count': 0, 'total': 0}
            daily_totals[date_key]['count'] += 1
            daily_totals[date_key]['total'] += float(part.line_total or 0)
    
    # Convert to sorted list
    daily_trend = [
        {'date': str(date), 'count': data['count'], 'total': data['total']}
        for date, data in sorted(daily_totals.items())
    ]
    
    return render_template(
        "sales/reports.html",
        days_back=days_back,
        total_revenue=float(total_revenue),
        total_transactions=total_transactions,
        total_items_sold=total_items_sold,
        avg_transaction=float(avg_transaction),
        payment_data=payment_data,
        top_products=top_products_data,
        daily_trend=daily_trend
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
