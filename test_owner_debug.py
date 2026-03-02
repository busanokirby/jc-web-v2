#!/usr/bin/env python
"""Debug owner access issue."""

from app import create_app, db
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func, or_, and_

app = create_app()
with app.app_context():
    from app.models.repair import Device
    
    selected_date = datetime(2026, 2, 26).date()
    
    repair_query = (
        Device.query
        .filter(
            or_(
                Device.actual_completion == selected_date,
                and_(
                    Device.deposit_paid > 0,
                    Device.deposit_paid_at.isnot(None),
                    func.date(Device.deposit_paid_at) == selected_date,
                ),
                and_(
                    Device.full_payment_at.isnot(None),
                    func.date(Device.full_payment_at) == selected_date,
                ),
            )
        )
    )
    
    repairs = repair_query.all()
    
    for d in repairs:
        print(f"\n{d.ticket_number}:")
        print(f"  Has 'owner' attr? {hasattr(d, 'owner')}")
        
        if hasattr(d, 'owner'):
            print(f"    d.owner = {d.owner}")
            if d.owner:
                print(f"    d.owner.display_name = {d.owner.display_name}")
            else:
                print(f"    d.owner is None")
        
        # Also check customer relationship
        print(f"  customer_id: {d.customer_id}")
        if d.customer_id:
            from app.models.customer import Customer
            cust = Customer.query.get(d.customer_id)
            if cust:
                print(f"    customer name: {cust.name}")
