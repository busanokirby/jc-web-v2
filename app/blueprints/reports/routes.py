from __future__ import annotations

from datetime import datetime, timedelta
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


@reports_bp.route("")
@reports_bp.route("/")
@login_required
@roles_required("ADMIN")
def reports_hub():
    """Reports hub - organized access to all available report templates"""
    return render_template("reports/hub.html")


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
    """Financial summary: revenue received, accounts receivable, outstanding balances"""
    from app.services.financial_reconciliation import FinancialReconciliation
    from datetime import date
    
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    fmt = request.args.get("format", "html")

    # Parse date filters - default to showing all data if no dates provided
    start_date = None
    end_date = None
    
    if date_from:
        try:
            start_date = datetime.fromisoformat(date_from).date()
        except Exception:
            pass
    
    if date_to:
        try:
            end_date = datetime.fromisoformat(date_to).date()
        except Exception:
            pass
    
    # If dates not provided, use reasonable defaults (last 90 days)
    if not start_date or not end_date:
        end_date = date.today()
        start_date = end_date - timedelta(days=90)

    # Generate comprehensive financial summary using unified reconciliation service
    summary = FinancialReconciliation.generate_financial_summary(start_date, end_date)
    
    # Extract and ensure all values are properly formatted floats
    revenue_received = float(summary['revenue_received']['total'])
    sales_total = float(summary['revenue_invoiced']['sales'])
    repairs_total = float(summary['revenue_invoiced']['repairs'])
    combined_sales_total = float(summary['revenue_invoiced']['total'])
    
    sales_payments_total = float(summary['revenue_received']['sales'])
    repair_payments_total = float(summary['revenue_received']['repairs'])
    payments_total = revenue_received
    
    # Outstanding breakdown (current, not period-filtered) - consolidated structure
    outstanding_detail = {
        'pending_sales': float(summary['outstanding'].get('pending_sales', 0)),
        'sales_balance_due': float(summary['outstanding'].get('sales_balance_due', 0)),
        'total_sales_outstanding': float(summary['outstanding'].get('total_sales_outstanding', 0)),
        'pending_repairs': float(summary['outstanding'].get('pending_repairs', 0)),
        'repairs_balance_due': float(summary['outstanding'].get('repairs_balance_due', 0)),
        'total_repairs_outstanding': float(summary['outstanding'].get('total_repairs_outstanding', 0)),
        'total_outstanding': float(summary['outstanding'].get('total_outstanding', 0)),
    }
    
    # For backward compatibility and CSV export
    outstanding = outstanding_detail['total_outstanding']
    
    # These are now consolidated into sales_balance_due and repairs_balance_due
    # Keep for CSV and other compatibility needs
    partial_repairs_total = outstanding_detail['repairs_balance_due']  # consolidated
    credit_repairs_total = outstanding_detail['repairs_balance_due']   # same as above (for compatibility)
    credit_sales_total = outstanding_detail['sales_balance_due']       # consolidated
    partial_sales_total = outstanding_detail['sales_balance_due']      # same as above (for compatibility)

    # CSV export
    if fmt == 'csv':
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(["Financial Summary Report", f"{start_date} to {end_date}"])
        cw.writerow([])
        
        cw.writerow(["REVENUE INVOICED (Period)", "Amount"])
        cw.writerow(["Sales Total", sales_total])
        cw.writerow(["Repairs Total", repairs_total])
        cw.writerow(["Total Revenue Invoiced", combined_sales_total])
        cw.writerow([])
        
        cw.writerow(["REVENUE RECEIVED (Period)", "Amount"])
        cw.writerow(["Sales Payments", sales_payments_total])
        cw.writerow(["Repair Payments", repair_payments_total])
        cw.writerow(["Total Revenue Received", payments_total])
        cw.writerow([])
        
        cw.writerow(["ACCOUNTS RECEIVABLE (Current)", "Amount"])
        cw.writerow(["Pending Sales", outstanding_detail['pending_sales']])
        cw.writerow(["Sales Balance Due", outstanding_detail['sales_balance_due']])
        cw.writerow(["Total Sales Outstanding", outstanding_detail['total_sales_outstanding']])
        cw.writerow([])
        
        cw.writerow(["Pending Repairs", outstanding_detail['pending_repairs']])
        cw.writerow(["Repairs Balance Due", outstanding_detail['repairs_balance_due']])
        cw.writerow(["Total Repairs Outstanding", outstanding_detail['total_repairs_outstanding']])
        cw.writerow([])
        
        cw.writerow(["TOTAL OUTSTANDING (Current)", outstanding_detail['total_outstanding']])
        
        output = si.getvalue()
        return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=financial_summary.csv"})

    return render_template(
        'reports/financial.html',
        # Revenue Invoiced (accrual basis)
        sales_total=sales_total,
        repairs_total=repairs_total,
        combined_sales_total=combined_sales_total,
        # Revenue Received (cash basis)
        payments_total=payments_total,
        sales_payments_total=sales_payments_total,
        repair_payments_total=repair_payments_total,
        # Outstanding Breakdown (current state, not period-bound)
        outstanding=outstanding,
        partial_repairs_total=partial_repairs_total,
        credit_repairs_total=credit_repairs_total,
        credit_sales_total=credit_sales_total,
        partial_sales_total=partial_sales_total,
        # Summary for display
        outstanding_detail=outstanding_detail,
        date_from=date_from,
        date_to=date_to,
    )


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
