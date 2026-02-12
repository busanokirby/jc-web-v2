from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from app.extensions import db


class Device(db.Model):
    __tablename__ = "device"

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False)  # JC-2026-001
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)

    device_type = db.Column(db.String(50), nullable=False)  # printer/laptop/desktop
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))

    issue_description = db.Column(db.Text, nullable=False)
    symptoms = db.Column(db.Text)
    password = db.Column(db.String(100))
    
    # Intake form fields
    device_age = db.Column(db.String(100))  # e.g., "2 years", "1-3 years"
    accessories = db.Column(db.Text)  # What accessories came with the device

    status = db.Column(db.String(50), default="Received")
    priority = db.Column(db.String(20), default="Normal")
    received_date = db.Column(db.Date, default=date.today)
    estimated_completion = db.Column(db.Date)
    actual_completion = db.Column(db.Date)
    warranty_expiry = db.Column(db.Date)

    diagnostic_fee = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    repair_cost = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    parts_cost = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    total_cost = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    deposit_paid = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    balance_due = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    payment_status = db.Column(db.String(20), default="Pending")  # Pending/Partial/Paid

    technician_notes = db.Column(db.Text)
    solution_applied = db.Column(db.Text)
    parts_used_text = db.Column(db.Text)  # legacy free-text (optional to keep)

    service_type = db.Column(db.String(50), default="Repair")
    pickup_method = db.Column(db.String(50), default="Walk-in")
    is_warranty_repair = db.Column(db.String(20), default="no")  # yes/no/unsure

    # Printer-specific
    printer_type = db.Column(db.String(50))
    is_color = db.Column(db.Boolean, default=False)
    is_scanner = db.Column(db.Boolean, default=False)

    # Laptop-specific
    screen_size = db.Column(db.String(20))
    ram = db.Column(db.String(20))
    storage = db.Column(db.String(20))
    os_version = db.Column(db.String(50))

    # Desktop-specific
    cpu = db.Column(db.String(100))
    gpu = db.Column(db.String(100))
    motherboard = db.Column(db.String(100))
    power_supply = db.Column(db.String(50))

    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    technician_name_override = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_user = db.relationship("User", foreign_keys=[created_by_user_id])


class Technician(db.Model):
    __tablename__ = "technician"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(100))
    status = db.Column(db.String(20), default="Available")

    assigned_devices = db.relationship("DeviceAssignment", backref="technician", lazy=True)


class DeviceAssignment(db.Model):
    __tablename__ = "device_assignment"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("device.id"), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey("technician.id"), nullable=False)
    assigned_date = db.Column(db.DateTime, default=datetime.utcnow)
    completed_date = db.Column(db.DateTime)

    device = db.relationship("Device", backref="assignments")


class RepairPartUsed(db.Model):
    __tablename__ = "repair_part_used"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("device.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)

    qty = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))
    line_total = db.Column(db.Numeric(10, 2), default=Decimal("0.00"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    device = db.relationship("Device", backref="parts_used_rows")
    product = db.relationship("Product")