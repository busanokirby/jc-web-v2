from __future__ import annotations

from datetime import datetime
from typing import List, TYPE_CHECKING
from app.extensions import db
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.repair import Device
    from app.models.sales import Sale


class Customer(BaseModel, db.Model):
    __tablename__ = "customer"

    id = db.Column(db.Integer, primary_key=True)
    customer_code = db.Column(db.String(20), unique=True, nullable=False, index=True)  # JC-CUST-001
    name = db.Column(db.String(100), nullable=False, index=True)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20), nullable=False, index=True)
    address = db.Column(db.Text)
    business_name = db.Column(db.String(100), index=True)
    customer_type = db.Column(db.String(20), default="Individual")  # Individual, Business, Government
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    loyalty_points = db.Column(db.Integer, default=0)

    # Relationships
    devices = db.relationship("Device", backref="owner", lazy=True, cascade="all, delete-orphan")
    sales = db.relationship("Sale", back_populates="customer", lazy=True, cascade="all, delete-orphan")
    created_by_user = db.relationship("User", foreign_keys=[created_by_user_id])

    @property
    def display_name(self) -> str:
        """Canonical display name used in templates (prefer person name, then business name)."""
        return (self.name or self.business_name or "")

    def __repr__(self) -> str:
        return f"<Customer {self.customer_code} {self.name}>"


class Department(BaseModel, db.Model):
    """Department model for organizing repairs and sales by department within a customer account.
    
    Primarily used for Business and Government customers that may have multiple departments
    or locations submitting repairs/sales. Allows proper categorization while keeping
    related customer records under one account to prevent duplicates.
    """
    __tablename__ = "department"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)  # e.g., "IT Department", "Main Office", "Makati Branch"
    contact_person = db.Column(db.String(100))  # Department contact person name
    phone = db.Column(db.String(20))  # Department-specific phone number
    email = db.Column(db.String(100))  # Department-specific email
    notes = db.Column(db.Text)  # Additional details or notes
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = db.relationship("Customer", backref=db.backref("departments", lazy=True, cascade="all, delete-orphan", foreign_keys=[customer_id]))
    devices = db.relationship("Device", back_populates="department", lazy=True, cascade="all, delete-orphan")
    sales = db.relationship("Sale", back_populates="department", lazy=True, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Department {self.name} customer_id={self.customer_id}>"