from __future__ import annotations

from flask import render_template, request, redirect, url_for, flash, Response
from flask_login import login_required
from app.services.authz import roles_required
from app.extensions import db
from app.models.inventory import Product, StockMovement
from app.services.stock import adjust_stock
from . import inventory_bp
from datetime import datetime
import csv
from io import StringIO


@inventory_bp.route('/movements')
@login_required
@roles_required('ADMIN', 'SALES')
def movements():
    q = request.args.get('q', '').strip()
    product_id = request.args.get('product_id', type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = StockMovement.query.join(Product, StockMovement.product_id == Product.id)

    if product_id:
        query = query.filter(StockMovement.product_id == product_id)
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))

    if date_from:
        try:
            df = datetime.fromisoformat(date_from).date()
            query = query.filter(StockMovement.created_at >= df)
        except Exception:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to).date()
            query = query.filter(StockMovement.created_at <= dt)
        except Exception:
            pass

    rows = query.order_by(StockMovement.created_at.desc()).limit(200).all()
    products = Product.query.order_by(Product.name).all()
    return render_template('inventory/movements.html', rows=rows, products=products, q=q, product_id=product_id, date_from=date_from, date_to=date_to)


@inventory_bp.route('/low-stock')
@login_required
@roles_required('ADMIN', 'SALES')
def low_stock():
    fmt = request.args.get('format', 'html')
    low_threshold = request.args.get('low', None, type=int)

    products = Product.query.order_by(Product.name).all()
    rows = []
    for p in products:
        threshold = low_threshold if low_threshold is not None else p.reorder_threshold
        low = p.stock_on_hand <= threshold
        reorder_qty = max(0, p.reorder_to - p.stock_on_hand) if low else 0
        rows.append({'product': p, 'low': low, 'threshold': threshold, 'reorder_qty': reorder_qty})

    if fmt == 'csv':
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['SKU', 'Name', 'Stock', 'Threshold', 'Reorder To', 'Reorder Qty'])
        for r in rows:
            cw.writerow([r['product'].sku or '', r['product'].name, r['product'].stock_on_hand, r['threshold'], r['product'].reorder_to, r['reorder_qty']])
        return Response(si.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=low_stock.csv'})

    return render_template('inventory/low_stock.html', rows=rows)


@inventory_bp.route('/adjust', methods=['GET', 'POST'])
@login_required
@roles_required('ADMIN')
def adjust_stock_page():
    products = Product.query.order_by(Product.name).all()
    if request.method == 'POST':
        product_id = int(request.form.get('product_id'))
        delta = int(request.form.get('delta') or 0)
        notes = (request.form.get('notes') or '').strip()

        product = Product.query.get_or_404(product_id)
        try:
            adjust_stock(product, delta, notes=notes)
            db.session.commit()
            flash('Stock adjusted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(str(e), 'danger')
        return redirect(url_for('inventory.adjust_stock_page'))

    return render_template('inventory/adjust_stock.html', products=products)
