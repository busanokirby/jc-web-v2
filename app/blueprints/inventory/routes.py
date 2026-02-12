from __future__ import annotations

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.inventory import Category, Product
from app.services.authz import roles_required
from app.services.guards import require_inventory_edit_enabled
from app.services.stock import stock_in, StockError, adjust_stock
from app.services.financials import safe_decimal

from . import inventory_bp


@inventory_bp.route("/products")
@login_required
@roles_required("ADMIN", "SALES")
def products():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    query = Product.query.filter_by(is_active=True)
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    if category_id:
        query = query.filter_by(category_id=category_id)
    products_list = query.order_by(Product.name).all()

    categories = Category.query.order_by(Category.name).all()
    return render_template("inventory/products.html", products=products_list, categories=categories, q=q, selected_category=category_id)


@inventory_bp.route('/products/<int:product_id>/adjust', methods=['POST'])
@login_required
@roles_required('ADMIN', 'SALES')
@require_inventory_edit_enabled
def ajax_adjust_product(product_id):
    data = request.get_json() or {}
    try:
        delta = int(data.get('delta', 0))
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid delta value.'}), 400
    notes = data.get('notes', '')
    p = Product.query.get_or_404(product_id)
    try:
        adjust_stock(p, delta, notes=notes)
        db.session.commit()
    except StockError as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    return jsonify({'success': True, 'stock': p.stock_on_hand})


@inventory_bp.route('/products/add_quick', methods=['POST'])
@login_required
@roles_required('ADMIN', 'SALES')
@require_inventory_edit_enabled
def add_product_quick():
    data = request.get_json() or request.form
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Product name is required.'}), 400
    category_id = data.get('category_id') or None
    is_service = (data.get('is_service') == 'on') or (data.get('is_service') is True)
    opening_stock = int(data.get('opening_stock') or 0)
    p = Product(
        name=name,
        sku=(data.get('sku') or '').strip() or None,
        category_id=int(category_id) if category_id else None,
        is_service=is_service,
        cost_price=safe_decimal(data.get('cost_price'), '0.00'),
        sell_price=safe_decimal(data.get('sell_price'), '0.00'),
        stock_on_hand=0 if is_service else 0,
        reorder_threshold=int(data.get('reorder_threshold') or 5),
        reorder_to=int(data.get('reorder_to') or 20),
        is_active=True,
    )
    db.session.add(p)
    db.session.flush()

    # Opening stock is a stock-in movement (only if not service)
    if not is_service and opening_stock > 0:
        try:
            stock_in(p, opening_stock, notes='Opening stock')
        except StockError as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400

    db.session.commit()
    return jsonify({'success': True, 'product': {'id': p.id, 'name': p.name, 'sku': p.sku, 'stock': p.stock_on_hand, 'category': p.category.name if p.category else None}})


@inventory_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@login_required
@roles_required("ADMIN", "SALES")
@require_inventory_edit_enabled
def delete_category(category_id: int):
    cat = Category.query.get_or_404(category_id)
    count = Product.query.filter_by(category_id=cat.id, is_active=True).count()
    if count > 0:
        flash("Category has products. Reassign or disable products before deleting.", "warning")
        return redirect(url_for("inventory.categories"))
    db.session.delete(cat)
    db.session.commit()
    flash("Category deleted.", "success")
    return redirect(url_for("inventory.categories"))


@inventory_bp.route('/categories/add_quick', methods=['POST'])
@login_required
@roles_required('ADMIN', 'SALES')
@require_inventory_edit_enabled
def add_category_quick():
    data = request.get_json() or request.form
    name = (data.get('name') or '').strip()
    if not name:
        return (jsonify({'success': False, 'message': 'Type name is required.'}), 400)

    # case-insensitive check
    exists = Category.query.filter(Category.name.ilike(name)).first()
    if exists:
        return jsonify({'success': True, 'category': {'id': exists.id, 'name': exists.name}})

    c = Category(name=name, is_active=True)
    db.session.add(c)
    db.session.commit()
    return jsonify({'success': True, 'category': {'id': c.id, 'name': c.name}})


@inventory_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
@roles_required('ADMIN')
@require_inventory_edit_enabled
def delete_product(product_id: int):
    p = Product.query.get_or_404(product_id)
    # Soft delete (mark inactive)
    p.is_active = False
    db.session.commit()
    flash('Product deleted (disabled).', 'success')
    return redirect(url_for('inventory.products'))





@inventory_bp.route("/products/add", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN", "SALES")
@require_inventory_edit_enabled
def add_product():
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Product name is required.", "danger")
            return redirect(url_for("inventory.add_product"))

        category_id = request.form.get("category_id") or None
        is_service = request.form.get("is_service") == "on"

        cost_price = safe_decimal(request.form.get("cost_price"), "0.00")
        sell_price = safe_decimal(request.form.get("sell_price"), "0.00")
        opening_stock = int(request.form.get("opening_stock") or 0)

        p = Product(
            name=name,
            sku=(request.form.get("sku") or "").strip() or None,
            category_id=int(category_id) if category_id else None,
            is_service=is_service,
            cost_price=cost_price,
            sell_price=sell_price,
            stock_on_hand=0 if is_service else 0,
            reorder_threshold=int(request.form.get('reorder_threshold') or 5),
            reorder_to=int(request.form.get('reorder_to') or 20),
            is_active=True,
        )

        db.session.add(p)
        db.session.flush()

        # Opening stock is a stock-in movement (only if not service)
        if not is_service and opening_stock > 0:
            try:
                stock_in(p, opening_stock, notes="Opening stock")
            except StockError as e:
                db.session.rollback()
                flash(str(e), "danger")
                return redirect(url_for("inventory.add_product"))

        db.session.commit()
        flash("Product added successfully!", "success")
        return redirect(url_for("inventory.products"))

    return render_template("inventory/add_product.html", categories=categories)


@inventory_bp.route("/stock-in", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN", "SALES")
@require_inventory_edit_enabled
def stock_in_page():
    products_list = Product.query.filter_by(is_active=True, is_service=False).order_by(Product.name).all()
    selected_product_id = request.args.get('product_id', type=int)

    if request.method == "POST":
        try:
            product_id_val = request.form.get("product_id")
            if not product_id_val:
                flash("Please select a product.", "danger")
                return redirect(url_for("inventory.stock_in_page"))
            product_id = int(product_id_val)
        except Exception:
            flash("Please select a valid product.", "danger")
            return redirect(url_for("inventory.stock_in_page"))

        qty = int(request.form.get("qty") or 0)
        notes = (request.form.get("notes") or "").strip()

        product = Product.query.get_or_404(product_id)

        try:
            stock_in(product, qty, notes=notes)
            db.session.commit()
            flash("Stock updated successfully!", "success")
        except StockError as e:
            db.session.rollback()
            flash(str(e), "danger")

        return redirect(url_for("inventory.stock_in_page"))

    return render_template("inventory/stock_in.html", products=products_list, selected_product_id=selected_product_id)


@inventory_bp.route("/categories", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN", "SALES")
@require_inventory_edit_enabled
def categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Category name is required.", "danger")
            return redirect(url_for("inventory.categories"))

        exists = Category.query.filter_by(name=name).first()
        if exists:
            flash("Category already exists.", "warning")
            return redirect(url_for("inventory.categories"))

        db.session.add(Category(name=name, is_active=True))
        db.session.commit()
        flash("Category added.", "success")
        return redirect(url_for("inventory.categories"))

    cats = Category.query.order_by(Category.name).all()
    return render_template("inventory/categories.html", categories=cats)


@inventory_bp.route("/categories/<int:category_id>/disable", methods=["POST"])
@login_required
@roles_required("ADMIN", "SALES")
@require_inventory_edit_enabled
def disable_category(category_id: int):
    cat = Category.query.get_or_404(category_id)
    cat.is_active = False
    db.session.commit()
    flash("Category disabled.", "success")
    return redirect(url_for("inventory.categories"))