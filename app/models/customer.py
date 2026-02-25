from __future__ import annotations

from datetime import datetime
from typing import List
from app.extensions import db
from app.models.base import BaseModel


class Customer(BaseModel, db.Model):
    __tablename__ = "customer"

    id = db.Column(db.Integer, primary_key=True)
    customer_code = db.Column(db.String(20), unique=True, nullable=False)  # JC-CUST-001
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20), nullable=False, index=True)
    address = db.Column(db.Text)
    business_name = db.Column(db.String(100))
    customer_type = db.Column(db.String(20), default="Individual")  # Individual, Business, Government
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    loyalty_points = db.Column(db.Integer, default=0)

    # type hints for relationships so the static analyser can see them
    devices: List["Device"]
    sales: List["Sale"]
    created_by_user: "User"

    devices = db.relationship("Device", backref="owner", lazy=True, cascade="all, delete-orphan")
    sales = db.relationship("Sale", back_populates="customer", lazy=True, cascade="all, delete-orphan")
    created_by_user = db.relationship("User", foreign_keys=[created_by_user_id])

    @property
    def display_name(self) -> str:
        """Canonical display name used in templates (prefer person name, then business name)."""
        return (self.name or self.business_name or "")

    def __repr__(self) -> str:
        return f"<Customer {self.customer_code} {self.name}>"