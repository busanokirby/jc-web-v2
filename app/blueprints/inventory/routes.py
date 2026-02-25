from __future__ import annotations

from flask import render_template, request, redirect, url_for, flash, jsonify, current_app as app
from flask_login import login_required
from app.extensions import db
from app.models.inventory import Category, Product
from app.services.authz import roles_required
from app.services.guards import require_inventory_edit_enabled
from app.services.stock import stock_in, StockError, adjust_stock
from app.services.financials import safe_decimal
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from . import inventory_bp


@inventory_bp.route("/products")
@login_required
@roles_required("ADMIN", "SALES")
def products():
    from app.services.pagination import get_page_args

    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    page, per_page = get_page_args()

    query = Product.query.filter_by(is_active=True)

    # apply search filter if provided
    if q:
        pattern = f"%{q}%"
        app.logger.debug("Inventory search q=%s page=%s per_page=%s", q, page, per_page)
        query = (
            query.outerjoin(Category)
            .options(joinedload(Product.category))  # type: ignore[arg-type]
            .filter(
                or_(
                    Product.name.ilike(pattern),
                    Product.sku.ilike(pattern),
                    Product.specs_json.ilike(pattern),
                    Category.name.ilike(pattern),
                )
            )
            .distinct()
        )
    else:
        query = query.options(joinedload(Product.category))  # type: ignore[arg-type]

    if category_id:
        # ``filter_by`` misbehaves after an outerjoin because it resolves
        # the attribute against the most recent entity.  in the search case
        # we've joined the ``Category`` table, so SQLAlchemy was looking for
        # ``Category.category_id`` which doesn't exist.  use a concrete
        # comparison against the Product column to avoid the confusion.
        query = query.filter(Product.category_id == category_id)

    products_pagination = query.order_by(Product.name).paginate(page=page, per_page=per_page, error_out=False)
    categories = Category.query.order_by(Category.name).all()
    return render_template("inventory/products.html", products=products_pagination, categories=categories, q=q, selected_category=category_id)


@inventory_bp.route("/api/search-suggestions")
@login_required
@roles_required("ADMIN", "SALES")
def search_suggestions():
    """Return up to 10 active products matching ``q`` in name or SKU.

    The endpoint is used by the autocomplete widget on the products page.
    """
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    if not q:
        return jsonify([])

    pattern = f"%{q}%"
    query = Product.query.filter(Product.is_active == True)
    if category_id:
        query = query.filter_by(category_id=category_id)

    matches = (
        query
        .filter(
            or_(
                Product.name.ilike(pattern),
                Product.sku.ilike(pattern),
            )
        )
        .order_by(Product.name)
        .limit(10)
        .all()
    )

    return jsonify([
        {"id": p.id, "name": p.name, "sku": p.sku}
        for p in matches
    ])



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
    # Only perform a stock adjustment when delta is non-zero.
    if delta != 0:
        try:
            adjust_stock(p, delta, notes=notes)
            db.session.commit()
        except StockError as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400

    # If a sell_price was provided, update it independently of stock adjustments.
    sell_price_raw = data.get('sell_price')
    if sell_price_raw is not None and str(sell_price_raw).strip() != '':
        try:
            p.sell_price = safe_decimal(sell_price_raw, "0.00")
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Invalid price format.'}), 400

    return jsonify({'success': True, 'stock': p.stock_on_hand, 'sell_price': float(p.sell_price) if p.sell_price is not None else None})


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
@roles_required("ADMIN")
@require_inventory_edit_enabled
def delete_category(category_id: int):
    """Delete a category and cascade-delete all associated products.

    - Enforces CSRF when app config enables it
    - Returns JSON for AJAX requests and redirects for normal form posts
    - Restricted to ADMIN role for safety
    - Will delete all products in the category as well
    """
    from flask import current_app, session, request, abort

    # Optional CSRF enforcement (disabled in tests by default)
    if current_app.config.get('WTF_CSRF_ENABLED', True):
        token = (request.form.get('csrf_token') or request.headers.get('X-CSRF-Token'))
        if not token or token != session.get('_csrf_token'):
            abort(403)

    cat = Category.query.get_or_404(category_id)

    try:
        # Count products being deleted for feedback
        product_count = Product.query.filter_by(category_id=cat.id).count()
        
        # Delete all products in this category
        Product.query.filter_by(category_id=cat.id).delete()
        
        # Delete the category itself
        db.session.delete(cat)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        msg = f"Error deleting category: {str(e)}"
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': msg}), 500
        flash(msg, 'danger')
        return redirect(url_for('inventory.categories'))

    # Success — support AJAX and normal form post
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True, 
            'id': cat.id,
            'products_deleted': product_count
        }), 200

    msg = f"Category deleted along with {product_count} product(s)."
    flash(msg, 'success')
    return redirect(url_for('inventory.categories'))


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
    from app.models.inventory import StockMovement
    from flask import current_app, session, abort

    # CSRF Check: Crucial for security
    if current_app.config.get('WTF_CSRF_ENABLED', True):
        token = (request.form.get('csrf_token') or request.headers.get('X-CSRF-Token'))
        if not token or token != session.get('_csrf_token'):
            abort(403)
    
    p = Product.query.get_or_404(product_id)
    
    try:
        # PERMANENT DESTRUCTION: Purge history first
        StockMovement.query.filter_by(product_id=product_id).delete()
        
        # Now delete the product record
        db.session.delete(p)
        db.session.commit()
        
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Product and history permanently deleted.'}), 200
        
        flash('Product and history destroyed.', 'success')
    except Exception as e:
        db.session.rollback()
        msg = f'Error deleting product: {str(e)}'
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': msg}), 500
        flash(msg, 'danger')
    
    return redirect(url_for('inventory.products'))


@inventory_bp.route('/products/bulk-delete', methods=['POST'])
@login_required
@roles_required('ADMIN')
@require_inventory_edit_enabled
def bulk_delete_products():
    """Delete multiple products at once.
    
    Expects JSON payload with 'product_ids' list and optional 'csrf_token'.
    Enforces CSRF protection when enabled.
    """
    from app.models.inventory import StockMovement
    from flask import current_app, session, abort

    # Extract data first
    data = request.get_json() or {}
    
    # Optional CSRF enforcement - check multiple sources
    if current_app.config.get('WTF_CSRF_ENABLED', True):
        # Try to get token from header first, then JSON body
        token = request.headers.get('X-CSRF-Token') or data.get('csrf_token')
        session_token = session.get('_csrf_token')
        
        if not token or not session_token or token != session_token:
            app.logger.warning(
                f'CSRF validation failed: token={bool(token)}, '
                f'session_token={bool(session_token)}, match={token == session_token if token and session_token else None}'
            )
            abort(403)
    
    product_ids = data.get('product_ids', [])

    if not product_ids or not isinstance(product_ids, list):
        return jsonify({'success': False, 'message': 'Invalid product_ids'}), 400

    # Convert to integers and validate
    try:
        product_ids = [int(pid) for pid in product_ids]
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid product IDs'}), 400

    try:
        # Delete stock movements for all products first
        StockMovement.query.filter(StockMovement.product_id.in_(product_ids)).delete(synchronize_session=False)
        
        # Delete all specified products
        deleted_count = Product.query.filter(Product.id.in_(product_ids)).delete(synchronize_session=False)
        db.session.commit()

        return jsonify({
            'success': True, 
            'message': f'Successfully deleted {deleted_count} product(s).',
            'deleted_count': deleted_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        msg = f'Error deleting products: {str(e)}'
        app.logger.error(f'Bulk delete error: {msg}')
        return jsonify({'success': False, 'message': msg}), 500





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


@inventory_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('ADMIN', 'SALES')
@require_inventory_edit_enabled
def edit_product(product_id: int):
    p = Product.query.get_or_404(product_id)
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        if not name:
            flash('Product name is required.', 'danger')
            return redirect(url_for('inventory.edit_product', product_id=product_id))

        # Update all fields
        p.name = name
        p.sku = (request.form.get('sku') or '').strip() or None
        p.is_service = request.form.get('is_service') == 'on'
        
        cat_val = request.form.get('category_id') or ''
        p.category_id = int(cat_val) if cat_val.isdigit() else None
        
        # Financials and thresholds
        p.cost_price = safe_decimal(request.form.get('cost_price'), "0.00")
        p.sell_price = safe_decimal(request.form.get('sell_price'), "0.00")
        p.reorder_threshold = int(request.form.get('reorder_threshold') or 5)
        p.reorder_to = int(request.form.get('reorder_to') or 20)

        try:
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('inventory.products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'danger')
    
    return render_template('inventory/add_product.html', categories=categories, product=p)

# Note: ajax_adjust_product is already mostly correct, 
# ensure it returns 'stock' so the JS can update the UI.


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


@inventory_bp.route("/adjust-stock", methods=["GET", "POST"])
@login_required
@roles_required("ADMIN", "SALES")
@require_inventory_edit_enabled
def adjust_stock_page():
    products_list = Product.query.filter_by(is_active=True, is_service=False).order_by(Product.name).all()
    selected_product_id = request.args.get('product_id', type=int)

    if request.method == "POST":
        try:
            product_id_val = request.form.get("product_id")
            if not product_id_val:
                flash("Please select a product.", "danger")
                return redirect(url_for("inventory.adjust_stock_page"))
            product_id = int(product_id_val)
        except Exception:
            flash("Please select a valid product.", "danger")
            return redirect(url_for("inventory.adjust_stock_page"))

        product = Product.query.get_or_404(product_id)

        # Adjust stock only when a non-zero delta is provided
        delta = int(request.form.get("delta") or 0)
        notes = (request.form.get("notes") or "").strip()

        if delta != 0:
            try:
                adjust_stock(product, delta, notes=notes)
            except StockError as e:
                db.session.rollback()
                flash(str(e), "danger")
                return redirect(url_for("inventory.adjust_stock_page"))

        # Adjust price if provided (allow price-only updates)
        new_price = (request.form.get("sell_price") or "").strip()
        if new_price:
            try:
                product.sell_price = safe_decimal(new_price, "0.00")
            except Exception:
                db.session.rollback()
                flash("Invalid price format.", "danger")
                return redirect(url_for("inventory.adjust_stock_page"))

        try:
            db.session.commit()
            flash("Product updated successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating product: {str(e)}", "danger")

        return redirect(url_for("inventory.adjust_stock_page"))

    return render_template("inventory/adjust_stock.html", products=products_list, selected_product_id=selected_product_id)


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