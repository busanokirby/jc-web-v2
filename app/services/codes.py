from __future__ import annotations

from datetime import datetime
from app.models.customer import Customer
from app.models.repair import Device
from app.models.sales import Sale


def generate_customer_code() -> str:
    """Return the next available `JC-CUST-###` code.

    - Ignores customer rows whose `customer_code` doesn't start with `JC-CUST-`.
    - Safely parses the numeric suffix and returns max+1.
    - Verifies the candidate isn't already present (simple retry loop).
    """
    # Prefer the highest `JC-CUST-` value; fall back to scanning all matching codes.
    last = (
        Customer.query
        .filter(Customer.customer_code.like('JC-CUST-%'))
        .order_by(Customer.customer_code.desc())
        .first()
    )

    if last:
        try:
            n = int(last.customer_code.rsplit('-', 1)[1]) + 1
        except Exception:
            # Defensive: scan all matching codes and compute max numeric suffix
            matches = Customer.query.with_entities(Customer.customer_code).filter(Customer.customer_code.like('JC-CUST-%')).all()
            max_n = 0
            for (code,) in matches:
                try:
                    num = int(code.rsplit('-', 1)[1])
                    if num > max_n:
                        max_n = num
                except Exception:
                    continue
            n = max_n + 1
    else:
        n = 1

    # Ensure uniqueness (handle rare race/edge cases by incrementing until free)
    candidate = f"JC-CUST-{n:03d}"
    while Customer.query.filter_by(customer_code=candidate).first():
        n += 1
        candidate = f"JC-CUST-{n:03d}"

    return candidate


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