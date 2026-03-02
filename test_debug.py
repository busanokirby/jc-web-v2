#!/usr/bin/env python
"""Debug why records aren't being created."""

from app import create_app, db
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func, or_, and_

app = create_app()
with app.app_context():
    from app.models.repair import Device
    from app.models.customer import Customer
    
    selected_date = datetime(2026, 2, 26).date()
    
    # Get repairs
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
    
    print("Debugging records creation:")
    print(f"Found {len(repairs)} repairs\n")
    
    for d in repairs:
        print(f"Repair: {d.ticket_number}")
        print(f"  charge_waived: {getattr(d, 'charge_waived', False)}")
        print(f"  deposit_paid: {d.deposit_paid}")
        print(f"  payment_status: {d.payment_status}")
        
        if getattr(d, "charge_waived", False):
            print(f"  -> SKIP: charge_waived is True")
            continue
        
        has_deposit = (d.deposit_paid or 0) > 0
        status_upper = (d.payment_status or "").capitalize()
        print(f"  has_deposit: {has_deposit}")
        print(f"  status_upper: '{status_upper}'")
        print(f"  status check: in ['Partial', 'Paid']? {status_upper in ['Partial', 'Paid']}")
        
        if (status_upper not in ['Partial', 'Paid']) and not has_deposit:
            print(f"  -> SKIP: status not in list AND no deposit")
            continue
        
        print(f"  -> PASS: Will process this repair")
        
        # Check deposit and full payment on selected date
        deposit_on_selected = False
        if d.deposit_paid_at and d.deposit_paid and d.deposit_paid > 0:
            dep_date = d.deposit_paid_at.date() if hasattr(d.deposit_paid_at, 'date') else d.deposit_paid_at
            print(f"  deposit_paid_at: {d.deposit_paid_at} -> date: {dep_date}")
            print(f"  selected_date: {selected_date}")
            if dep_date == selected_date:
                deposit_on_selected = True
        
        print(f"  deposit_on_selected: {deposit_on_selected}")
        
        full_payment_on_selected = False
        if d.full_payment_at and d.payment_status == 'Paid':
            fp_date = d.full_payment_at.date() if hasattr(d.full_payment_at, 'date') else d.full_payment_at
            print(f"  full_payment_at: {d.full_payment_at} -> date: {fp_date}")
            if fp_date == selected_date:
                full_payment_on_selected = True
        
        print(f"  full_payment_on_selected: {full_payment_on_selected}")
        print()
