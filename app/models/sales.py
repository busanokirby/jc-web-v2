from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from app.extensions import db
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.customer import Customer, Department
    from app.models.inventory import Product


class Sale(BaseModel, db.Model):
    __tablename__ = "sale"

    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(30), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))  # nullable for walk-in
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=True)  # Department within customer

    status = db.Column(db.String(20), default="PAID")  # DRAFT / PAID / PARTIAL / VOID

    # Allow sales to be marked as claimed_on_credit (released unpaid)
    claimed_on_credit = db.Column(db.Boolean, default=False, nullable=False)

    # Notes/remarks for the sale
    notes = db.Column(db.Text, nullable=True, default=None)

    subtotal = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    discount = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    tax = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    total = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    customer = db.relationship("Customer", back_populates="sales")
    department = db.relationship("Department", back_populates="sales")
    items = db.relationship("SaleItem", backref="sale", cascade="all, delete-orphan")
    payments = db.relationship("SalePayment", back_populates="sale", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Sale {self.invoice_no} total={self.total} status={self.status}>"

    @property
    def active_items(self) -> List[SaleItem]:
        """Return only non-revoked items."""
        return [item for item in (self.items or []) if not item.is_revoked]

    @property
    def revoked_items(self) -> List[SaleItem]:
        """Return only revoked items."""
        return [item for item in (self.items or []) if item.is_revoked]

    def calculate_totals_excluding_revoked(self):
        """
        Calculate new subtotal and total excluding revoked items.
        Returns (new_subtotal, new_discount, new_total) as Decimal tuples.
        """
        active_items = self.active_items
        new_subtotal = sum(
            (item.line_total or Decimal("0.00")) for item in active_items
        ) if active_items else Decimal("0.00")
        
        # Discount stays the same (proportional discount remains as originally specified)
        # but could be adjusted if needed - for now keeping original discount
        discount_to_apply = self.discount or Decimal("0.00")
        new_total = max(Decimal("0.00"), new_subtotal - discount_to_apply)
        
        return new_subtotal, discount_to_apply, new_total


class SaleItem(BaseModel, db.Model):
    __tablename__ = "sale_item"

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)

    qty = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    line_total = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))

    # Revocation tracking for audit trail
    revoked_at = db.Column(db.DateTime, nullable=True, default=None)
    revoke_reason = db.Column(db.Text, nullable=True, default=None)
    revoked_by = db.Column(db.String(100), nullable=True, default=None)  # username who revoked it

    product: Product = None
    product = db.relationship("Product")

    def __repr__(self) -> str:
        status = " (REVOKED)" if self.revoked_at else ""
        return f"<SaleItem product={self.product_id} qty={self.qty}{status}>"

    @property
    def is_revoked(self) -> bool:
        """Check if this item has been revoked."""
        return self.revoked_at is not None

    def revoke(self, reason: str = None, revoked_by: str = None):
        """
        Mark this item as revoked.
        
        Args:
            reason: Optional reason for revocation
            revoked_by: Username of who revoked it
        """
        self.revoked_at = datetime.utcnow()
        self.revoke_reason = reason
        self.revoked_by = revoked_by


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
    sale: Sale = None
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