from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from app.extensions import db


class Sale(db.Model):
    __tablename__ = "sale"

    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(30), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))  # nullable for walk-in

    status = db.Column(db.String(20), default="PAID")  # DRAFT / PAID / PARTIAL / VOID

    subtotal = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    discount = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    tax = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    total = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("SaleItem", backref="sale", cascade="all, delete-orphan")
    payments = db.relationship("SalePayment", backref="sale", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Sale {self.invoice_no} total={self.total} status={self.status}>"


class SaleItem(db.Model):
    __tablename__ = "sale_item"

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)

    qty = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    line_total = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))

    product = db.relationship("Product")

    def __repr__(self) -> str:
        return f"<SaleItem product={self.product_id} qty={self.qty}>"


class SalePayment(db.Model):
    __tablename__ = "sale_payment"

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"), nullable=False)

    amount = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    method = db.Column(db.String(20), default="Cash")
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<SalePayment sale={self.sale_id} amount={self.amount}>"