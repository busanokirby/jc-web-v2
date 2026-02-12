from __future__ import annotations

from datetime import datetime
from app.extensions import db


class Customer(db.Model):
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

    devices = db.relationship("Device", backref="owner", lazy=True, cascade="all, delete-orphan")
    sales = db.relationship("Sale", backref="customer", lazy=True, cascade="all, delete-orphan")
    created_by_user = db.relationship("User", foreign_keys=[created_by_user_id])

    def __repr__(self) -> str:
        return f"<Customer {self.customer_code} {self.name}>"