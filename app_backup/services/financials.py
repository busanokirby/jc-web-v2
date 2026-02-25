from __future__ import annotations

from decimal import Decimal, InvalidOperation
from app.models.repair import Device


def safe_decimal(value, default: str = "0.00") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    try:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def recompute_repair_financials(device: Device) -> None:
    diagnostic = safe_decimal(device.diagnostic_fee, "0.00")
    repair = safe_decimal(device.repair_cost, "0.00")
    parts = safe_decimal(device.parts_cost, "0.00")
    deposit = safe_decimal(device.deposit_paid, "0.00")

    device.total_cost = diagnostic + repair + parts
    device.balance_due = device.total_cost - deposit

    if device.total_cost > 0 and device.balance_due <= 0:
        device.payment_status = "Paid"
        device.balance_due = Decimal("0.00")
    elif deposit > 0:
        device.payment_status = "Partial"
    else:
        device.payment_status = "Pending"