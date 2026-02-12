from __future__ import annotations

from decimal import Decimal
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from datetime import datetime, timedelta
import json

from app.extensions import db
from app.models.inventory import Product
from app.models.sales import Sale, SaleItem, SalePayment
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
    POS with multi-item cart support
    """
    products_list = Product.query.filter_by(is_active=True).order_by(Product.name).all()

    if request.method == "POST":
        try:
            items_json = request.form.get("items", "[]")
            items = json.loads(items_json)
            if not items:
                flash("Cart is empty", "danger")
                return redirect(url_for("sales.pos"))
            discount = safe_decimal(request.form.get("discount") or "0", "0.00")
            payment_method = request.form.get("payment_method", "Cash")
            subtotal = Decimal("0.00")
            items_with_products = []
            for item in items:
                product_id = int(item.get("product_id"))
                qty = int(item.get("qty"))
                if qty <= 0:
                    flash("Invalid quantity", "danger")
                    return redirect(url_for("sales.pos"))
                product = Product.query.get_or_404(product_id)
                if qty > product.stock_on_hand:
                    flash(f"Insufficient stock for {product.name}", "danger")
                    return redirect(url_for("sales.pos"))
                unit_price = safe_decimal(product.sell_price, "0.00")
                line_total = unit_price * Decimal(qty)
                subtotal += line_total
                items_with_products.append({"product": product, "qty": qty, "unit_price": unit_price, "line_total": line_total})
            total = max(Decimal("0.00"), subtotal - discount)
            sale = Sale(invoice_no=generate_invoice_no(), status="PAID", subtotal=subtotal, discount=discount, tax=Decimal("0.00"), total=total)
            db.session.add(sale)
            db.session.flush()
            for item_data in items_with_products:
                product = item_data["product"]
                qty = item_data["qty"]
                unit_price = item_data["unit_price"]
                line_total = item_data["line_total"]
                sale_item = SaleItem(sale_id=sale.id, product_id=product.id, qty=qty, unit_price=unit_price, line_total=line_total)
                db.session.add(sale_item)
                try:
                    stock_out(product, qty, reference_type="SALE", reference_id=sale.id, notes=f"Invoice {sale.invoice_no}")
                except StockError as e:
                    db.session.rollback()
                    flash(str(e), "danger")
                    return redirect(url_for("sales.pos"))
            db.session.add(SalePayment(sale_id=sale.id, amount=total, method=payment_method))
            db.session.commit()
            flash(f"Sale recorded! Invoice: {sale.invoice_no}", "success")
            return redirect(url_for("sales.invoice", sale_id=sale.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("sales.pos"))

        if qty <= 0:
            flash("Quantity must be greater than 0.", "danger")
            return redirect(url_for("sales.pos"))

        product = Product.query.get_or_404(product_id)
        unit_price = safe_decimal(product.sell_price, "0.00")
        line_total = unit_price * Decimal(qty)

        sale = Sale(
            invoice_no=generate_invoice_no(),
            status="PAID",
            subtotal=line_total,
            discount=Decimal("0.00"),
            tax=Decimal("0.00"),
            total=line_total,
        )

        db.session.add(sale)
        db.session.flush()

        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            qty=qty,
            unit_price=unit_price,
            line_total=line_total,
        )
        db.session.add(sale_item)

        # Strict stock deduction (services don’t reduce stock)
        try:
            stock_out(product, qty, reference_type="SALE", reference_id=sale.id, notes=f"Invoice {sale.invoice_no}")
        except StockError as e:
            db.session.rollback()
            flash(str(e), "danger")
            return redirect(url_for("sales.pos"))

        # Payment record
        if paid_amount <= 0:
            paid_amount = line_total  # default full pay if not provided

        db.session.add(SalePayment(
            sale_id=sale.id,
            amount=paid_amount,
            method=payment_method,
        ))

        db.session.commit()
        flash(f"Sale recorded! Invoice: {sale.invoice_no}", "success")
        return redirect(url_for("sales.invoice", sale_id=sale.id))

    # Convert products to JSON for frontend
    products_json = [{
        "id": p.id,
        "name": p.name,
        "sku": p.sku,
        "sell_price": float(p.sell_price),
        "stock_on_hand": p.stock_on_hand,
        "is_service": p.is_service
    } for p in products_list]
    
    return render_template("sales/pos.html", products=products_json)


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
    """Sales analytics and reporting dashboard"""
    
    # Date range filter
    days_back = request.args.get('days', 30, type=int)
    if days_back < 1:
        days_back = 30
    start_date = datetime.now() - timedelta(days=days_back)
    
    # Query sales within date range
    sales_period = Sale.query.filter(Sale.created_at >= start_date).all()
    
    # Calculate KPIs
    total_revenue = Decimal("0.00")
    total_transactions = len(sales_period)
    total_items_sold = 0
    
    for sale in sales_period:
        total_revenue += sale.total or Decimal("0.00")
        total_items_sold += sum(item.qty for item in sale.items)
    
    avg_transaction = (total_revenue / total_transactions) if total_transactions > 0 else Decimal("0.00")
    
    # Sales by payment method
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
    
    # Top 10 products sold
    top_products = db.session.query(
        Product.name,
        func.sum(SaleItem.qty).label('total_qty'),
        func.sum(SaleItem.line_total).label('total_amount')
    ).join(SaleItem).join(Sale).filter(
        Sale.created_at >= start_date
    ).group_by(Product.id, Product.name).order_by(
        func.sum(SaleItem.qty).desc()
    ).limit(10).all()
    
    top_products_data = [{
        'name': tp.name,
        'qty': tp.total_qty,
        'amount': float(tp.total_amount or 0)
    } for tp in top_products]
    
    # Daily sales trend (last 30 days)
    daily_sales = db.session.query(
        func.date(Sale.created_at).label('date'),
        func.count(Sale.id).label('transaction_count'),
        func.sum(Sale.total).label('daily_total')
    ).filter(Sale.created_at >= start_date).group_by(
        func.date(Sale.created_at)
    ).order_by(func.date(Sale.created_at)).all()
    
    daily_trend = [{
        'date': str(ds.date),
        'count': ds.transaction_count,
        'total': float(ds.daily_total or 0)
    } for ds in daily_sales]
    
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