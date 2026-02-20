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

    # Query payments total (payments recorded)
    payments_query = db.session.query(func.coalesce(func.sum(SalePayment.amount), 0).label('total'))
    if 'from' in date_filter_obj:
        payments_query = payments_query.filter(SalePayment.paid_at >= date_filter_obj['from'])
    if 'to' in date_filter_obj:
        payments_query = payments_query.filter(SalePayment.paid_at <= date_filter_obj['to'])
    payments_total = float(payments_query.scalar() or 0)

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

    # CSV export
    if fmt == 'csv':
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(["Metric", "Amount"])
        cw.writerow(["Sales Total (sales only)", sales_total])
        cw.writerow(["Repairs Total", repairs_total])
        cw.writerow(["Sales + Repairs Total", combined_sales_total])
        cw.writerow(["Payments Total", payments_total])
        cw.writerow(["Outstanding", outstanding])
        output = si.getvalue()
        return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=financial_summary.csv"})

    return render_template('reports/financial.html', sales_total=sales_total, repairs_total=repairs_total, combined_sales_total=combined_sales_total, payments_total=payments_total, outstanding=outstanding, date_from=date_from, date_to=date_to)


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
