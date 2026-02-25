from __future__ import annotations

from datetime import datetime
from app.models.customer import Customer
from app.models.repair import Device
from app.models.sales import Sale


def generate_customer_code() -> str:
    last = Customer.query.order_by(Customer.id.desc()).first()
    if last and last.customer_code.startswith("JC-CUST-"):
        n = int(last.customer_code.split("-")[-1]) + 1
    else:
        n = 1
    return f"JC-CUST-{n:03d}"


def generate_ticket_number() -> str:
    year = datetime.now().year
    last = (
        Device.query.filter(Device.ticket_number.like(f"JC-{year}-%"))
        .order_by(Device.id.desc())
        .first()
    )
    if last:
        n = int(last.ticket_number.split("-")[-1]) + 1
    else:
        n = 1
    return f"JC-{year}-{n:03d}"


def generate_invoice_no() -> str:
    year = datetime.now().year
    last = (
        Sale.query.filter(Sale.invoice_no.like(f"INV-{year}-%"))
        .order_by(Sale.id.desc())
        .first()
    )
    if last:
        n = int(last.invoice_no.split("-")[-1]) + 1
    else:
        n = 1
    return f"INV-{year}-{n:05d}"