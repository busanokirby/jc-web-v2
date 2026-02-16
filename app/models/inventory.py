from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from app.extensions import db


class Category(db.Model):
    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship("Product", backref="category", lazy=True)

    def __repr__(self) -> str:
        return f"<Category {self.name}>"


class Product(db.Model):
    __tablename__ = "product"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True)  # optional
    name = db.Column(db.String(150), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))

    is_service = db.Column(db.Boolean, default=False, nullable=False)  # e.g., labor/installation

    cost_price = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    sell_price = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))

    stock_on_hand = db.Column(db.Integer, default=0, nullable=False)  # strict stock
    # Reorder settings
    reorder_threshold = db.Column(db.Integer, default=5, nullable=False)
    reorder_to = db.Column(db.Integer, default=20, nullable=False)

    specs_json = db.Column(db.Text)  # optional flexible specs
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Product {self.name} (stock={self.stock_on_hand})>"


class StockMovement(db.Model):
    __tablename__ = "stock_movement"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id", ondelete="CASCADE"), nullable=False)

    movement_type = db.Column(db.String(10), nullable=False)  # IN / OUT / ADJUST
    qty = db.Column(db.Integer, nullable=False)  # always positive
    reference_type = db.Column(db.String(10), nullable=False)  # SALE / REPAIR / MANUAL
    reference_id = db.Column(db.Integer)  # sale_id or device_id
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product", backref="movements", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<StockMovement {self.movement_type} {self.qty} {self.reference_type}:{self.reference_id}>"