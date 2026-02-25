from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from app.extensions import db
from app.models.base import BaseModel


class Sale(BaseModel, db.Model):
    __tablename__ = "sale"

    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(30), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))  # nullable for walk-in

    status = db.Column(db.String(20), default="PAID")  # DRAFT / PAID / PARTIAL / VOID

    # Allow sales to be marked as claimed_on_credit (released unpaid)
    claimed_on_credit = db.Column(db.Boolean, default=False, nullable=False)

    subtotal = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    discount = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    tax = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    total = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationship hints for static type checking
    customer: Optional["Customer"]
    items: List["SaleItem"]
    payments: List["SalePayment"]

    customer = db.relationship("Customer", back_populates="sales")
    items = db.relationship("SaleItem", backref="sale", cascade="all, delete-orphan")
    payments = db.relationship("SalePayment", back_populates="sale", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Sale {self.invoice_no} total={self.total} status={self.status}>"


class SaleItem(BaseModel, db.Model):
    __tablename__ = "sale_item"

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)

    qty = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    line_total = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))

    product: "Product"
    product = db.relationship("Product")

    def __repr__(self) -> str:
        return f"<SaleItem product={self.product_id} qty={self.qty}>"


class SalePayment(BaseModel, db.Model):
    __tablename__ = "sale_payment"

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"), nullable=False)

    # VALIDATION: amount must be > 0 to prevent negative/refund entries
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(20), default="Cash")
    # CRITICAL: paid_at is when payment was actually received (not sale.created_at)
    paid_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    # relationship hint
    sale: "Sale"
    sale = db.relationship("Sale", back_populates="payments")

    def __repr__(self) -> str:
        return f"<SalePayment sale={self.sale_id} amount={self.amount}>"
    
    @classmethod
    def create_validated(cls, sale_id: int, amount: Decimal, method: str = "Cash"):
        """
        Factory method to create validated payment.
        
        Ensures:
        - amount > 0 (no negative/refund without refund type)
        - sale exists
        - sale is not void/draft
        
        Raises:
            ValueError: If validation fails
        """
        amount = Decimal(str(amount))  # Ensure Decimal
        if amount <= 0:
            raise ValueError(f"Payment amount must be positive, got {amount}")
        
        sale = Sale.query.get(sale_id)
        if not sale:
            raise ValueError(f"Sale {sale_id} not found")
        
        if sale.status and sale.status.upper() in ['VOID', 'DRAFT']:
            raise ValueError(f"Cannot add payment to {sale.status} sale")
        
        return cls(sale_id=sale_id, amount=amount, method=method, paid_at=datetime.utcnow())