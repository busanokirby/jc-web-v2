from __future__ import annotations

from datetime import datetime
from io import StringIO
import csv

from flask import render_template, request, Response
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models.repair import Device
from app.models.sales import Sale
from app.services.authz import roles_required

from . import reports_bp


@reports_bp.route("/repairs")
@login_required
@roles_required("ADMIN")
def repairs_report():
    """Repairs summary report (group by status) with optional CSV export"""
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    fmt = request.args.get("format", "html")

    query = db.session.query(
        Device.status.label("status"),
        func.count(Device.id).label("count"),
        func.coalesce(func.sum(Device.total_cost), 0).label("total_cost")
    )

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

    query = query.group_by(Device.status).order_by(Device.status)
    rows = query.all()

    # CSV export
    if fmt == "csv":
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(["Status", "Count", "Total Cost"])
        for r in rows:
            cw.writerow([r.status, int(r.count), float(r.total_cost or 0)])
        output = si.getvalue()
        return Response(output, mimetype="text/csv", headers={
            "Content-Disposition": "attachment; filename=repairs_by_status.csv"
        })

    # Render HTML
    return render_template("reports/repairs.html", rows=rows, date_from=date_from, date_to=date_to)


@reports_bp.route("/financial")
@login_required
@roles_required("ADMIN")
def financial_report():
    """Financial summary: sales totals, payments, outstanding balances"""
    from app.models.sales import Sale, SalePayment
    
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    fmt = request.args.get("format", "html")

    # Build date filters
    date_filter_obj = {}
    if date_from:
        try:
            df = datetime.fromisoformat(date_from).date()
            date_filter_obj['from'] = df
        except Exception:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to).date()
            date_filter_obj['to'] = dt
        except Exception:
            pass

    # Query sales total (sales transactions)
    sales_query = db.session.query(func.coalesce(func.sum(Sale.total), 0).label('total'))
    if 'from' in date_filter_obj:
        sales_query = sales_query.filter(Sale.created_at >= date_filter_obj['from'])
    if 'to' in date_filter_obj:
        sales_query = sales_query.filter(Sale.created_at <= date_filter_obj['to'])
    sales_total = float(sales_query.scalar() or 0)

    # Query payments total (payments recorded from sales)
    payments_query = db.session.query(func.coalesce(func.sum(SalePayment.amount), 0).label('total'))
    if 'from' in date_filter_obj:
        payments_query = payments_query.filter(SalePayment.paid_at >= date_filter_obj['from'])
    if 'to' in date_filter_obj:
        payments_query = payments_query.filter(SalePayment.paid_at <= date_filter_obj['to'])
    sales_payments_total = float(payments_query.scalar() or 0)

    # Query repair payments (deposits received on repairs, tracked by deposit_paid_at)
    repair_payments_query = db.session.query(func.coalesce(func.sum(Device.deposit_paid), 0).label('total'))
    if 'from' in date_filter_obj:
        repair_payments_query = repair_payments_query.filter(Device.deposit_paid_at >= date_filter_obj['from'])
    if 'to' in date_filter_obj:
        repair_payments_query = repair_payments_query.filter(Device.deposit_paid_at <= date_filter_obj['to'])
    repair_payments_total = float(repair_payments_query.scalar() or 0)

    # Total payments: sales payments + repair deposits
    payments_total = sales_payments_total + repair_payments_total

    # Include repair transactions completed within the date range (use actual_completion)
    repairs_query = db.session.query(func.coalesce(func.sum(Device.total_cost), 0).label('total'))
    if 'from' in date_filter_obj:
        repairs_query = repairs_query.filter(Device.actual_completion >= date_filter_obj['from'])
    if 'to' in date_filter_obj:
        repairs_query = repairs_query.filter(Device.actual_completion <= date_filter_obj['to'])
    repairs_total = float(repairs_query.scalar() or 0)

    # Add repairs total into sales_total for a full picture of revenue
    combined_sales_total = sales_total + repairs_total

    # Outstanding: combined sales (sales + repairs) minus payments recorded
    outstanding = max(0.0, combined_sales_total - payments_total)

    # Calculate partial/credit breakdown for repairs
    # Repairs with partial payment (some deposit made, balance still due)
    partial_repairs_query = db.session.query(func.coalesce(func.sum(Device.balance_due), 0).label('total'))
    partial_repairs_query = partial_repairs_query.filter(Device.payment_status == 'Partial')
    if 'from' in date_filter_obj:
        partial_repairs_query = partial_repairs_query.filter(Device.actual_completion >= date_filter_obj['from'])
    if 'to' in date_filter_obj:
        partial_repairs_query = partial_repairs_query.filter(Device.actual_completion <= date_filter_obj['to'])
    partial_repairs_total = float(partial_repairs_query.scalar() or 0)

    # Repairs claimed on credit (released without payment)
    credit_repairs_query = db.session.query(func.coalesce(func.sum(Device.total_cost), 0).label('total'))
    credit_repairs_query = credit_repairs_query.filter(Device.claimed_on_credit == True)
    if 'from' in date_filter_obj:
        credit_repairs_query = credit_repairs_query.filter(Device.actual_completion >= date_filter_obj['from'])
    if 'to' in date_filter_obj:
        credit_repairs_query = credit_repairs_query.filter(Device.actual_completion <= date_filter_obj['to'])
    credit_repairs_total = float(credit_repairs_query.scalar() or 0)

    # CSV export
    if fmt == 'csv':
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(["Metric", "Amount"])
        cw.writerow(["Sales Total (sales only)", sales_total])
        cw.writerow(["Repairs Total", repairs_total])
        cw.writerow(["Sales + Repairs Total", combined_sales_total])
        cw.writerow(["Payments from Sales", sales_payments_total])
        cw.writerow(["Payments from Repairs (Deposits)", repair_payments_total])
        cw.writerow(["Payments Total", payments_total])
        cw.writerow(["Outstanding (Pending)", outstanding])
        cw.writerow(["Repairs with Partial Payment (Balance Due)", partial_repairs_total])
        cw.writerow(["Repairs Claimed on Credit", credit_repairs_total])
        output = si.getvalue()
        return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=financial_summary.csv"})

    return render_template('reports/financial.html', sales_total=sales_total, repairs_total=repairs_total, combined_sales_total=combined_sales_total, payments_total=payments_total, sales_payments_total=sales_payments_total, repair_payments_total=repair_payments_total, outstanding=outstanding, partial_repairs_total=partial_repairs_total, credit_repairs_total=credit_repairs_total, date_from=date_from, date_to=date_to)


@reports_bp.route('/inventory')
@login_required
@roles_required('ADMIN')
def inventory_report():
    """Inventory report: stock levels and value. CSV export supported."""
    low_threshold = request.args.get('low', 5, type=int)
    fmt = request.args.get('format', 'html')

    from app.models.inventory import Product
    products = Product.query.order_by(Product.name).all()

    rows = []
    total_value = 0.0
    for p in products:
        value = float((p.cost_price or 0) * (p.stock_on_hand or 0))
        total_value += value
        reorder_qty = max(0, p.reorder_to - p.stock_on_hand) if p.stock_on_hand <= low_threshold else 0
        rows.append({'id': p.id, 'name': p.name, 'sku': p.sku, 'category': p.category.name if p.category else None, 'stock': p.stock_on_hand, 'cost': float(p.cost_price or 0), 'value': value, 'low': p.stock_on_hand <= low_threshold, 'reorder_qty': reorder_qty, 'reorder_to': p.reorder_to})

    if fmt == 'csv':
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['SKU', 'Name', 'Category', 'Stock', 'Cost', 'Value', 'Reorder To', 'Reorder Qty'])
        for r in rows:
            cw.writerow([r['sku'] or '', r['name'], r['category'] or '', r['stock'], r['cost'], r['value'], r['reorder_to'], r['reorder_qty']])
        output = si.getvalue()
        return Response(output, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=inventory_report.csv'})

    return render_template('reports/inventory.html', rows=rows, total_value=total_value, low_threshold=low_threshold)
