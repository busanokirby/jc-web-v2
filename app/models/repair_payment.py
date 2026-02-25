"""
Repair Payment Model - Mirrors SalePayment structure for consistency
Tracks all repair payments with full audit trail
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from app.extensions import db
from app.models.base import BaseModel

# bring in related models for type hints
from app.models.repair import Device
from app.models.user import User


class RepairPayment(BaseModel, db.Model):
    """
    Individual payment transaction for a repair.
    
    Allows repairs to have multiple payment records, consistent with SalePayment.
    """
    __tablename__ = "repair_payment"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("device.id"), nullable=False, index=True)

    # Payment details
    amount = db.Column(db.Numeric(10, 2), nullable=False)  # Must be > 0
    method = db.Column(db.String(20), default="Cash")  # Cash, GCash, Bank Transfer, etc.
    
    # Payment timestamp (CRITICAL: this is when payment was actually received)
    paid_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Audit trail
    recorded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    # hints for static analysis
    device: "Device"
    recorded_by: "User"

    device = db.relationship("Device", backref="repair_payments", cascade="all")  # type: ignore[assignment]
    recorded_by = db.relationship("User")  # type: ignore[assignment]

    def __repr__(self) -> str:
        return f"<RepairPayment device={self.device_id} amount={self.amount} date={self.paid_at}>"


# Migration notes:
# 1. Create new repair_payment table
# 2. Run data migration:
#    - For each Device with deposit_paid > 0:
#      CREATE RepairPayment(device_id, amount=deposit_paid, paid_at=deposit_paid_at)
# 3. After migration, Device.deposit_paid and Device.deposit_paid_at become deprecated
#    (kept for backward compatibility, calculated from repair_payments)
# 4. Device.payment_status becomes calculated (not manual):
#    total_received = sum(repair_payments.amount)
#    status = "Paid" if total_received >= total_cost else "Partial" if total_received > 0 else "Pending"
