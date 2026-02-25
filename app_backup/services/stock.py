from __future__ import annotations

from app.extensions import db
from app.models.inventory import Product, StockMovement


class StockError(Exception):
    pass


def stock_in(product: Product, qty: int, notes: str = "") -> None:
    if qty <= 0:
        raise StockError("Quantity must be greater than 0.")
    if product.is_service:
        raise StockError("Cannot stock-in a service item.")

    product.stock_on_hand += qty
    db.session.add(StockMovement(
        product_id=product.id,
        movement_type="IN",
        qty=qty,
        reference_type="MANUAL",
        reference_id=None,
        notes=notes,
    ))


def adjust_stock(product: Product, delta: int, notes: str = "") -> None:
    """Adjust stock by positive or negative delta and record an ADJUST movement."""
    if delta == 0:
        raise StockError("Delta must be non-zero for adjust operation.")
    if product.is_service:
        raise StockError("Cannot adjust stock for a service item.")

    if delta < 0 and product.stock_on_hand < abs(delta):
        raise StockError(f"Not enough stock to reduce by {abs(delta)}. Available: {product.stock_on_hand}")

    product.stock_on_hand += delta
    db.session.add(StockMovement(
        product_id=product.id,
        movement_type="ADJUST",
        qty=abs(delta),
        reference_type="MANUAL",
        reference_id=None,
        notes=notes,
    ))


def stock_out(product: Product, qty: int, reference_type: str, reference_id: int | None, notes: str = "") -> None:
    if qty <= 0:
        raise StockError("Quantity must be greater than 0.")
    if product.is_service:
        return  # services do not affect stock

    if product.stock_on_hand < qty:
        raise StockError(f"Not enough stock for {product.name}. Available: {product.stock_on_hand}")

    product.stock_on_hand -= qty
    db.session.add(StockMovement(
        product_id=product.id,
        movement_type="OUT",
        qty=qty,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
    ))