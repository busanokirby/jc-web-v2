#!/usr/bin/env python
"""Test daily_sales query after fix."""

from app import create_app, db
from datetime import datetime
from sqlalchemy import func, or_, and_

app = create_app()
with app.app_context():
    from app.models.repair import Device
    from app.models.customer import Customer
    
    print("\n" + "="*70)
    print("DAILY SALES QUERY TEST - WITH FULL_PAYMENT_AT FILTERING")
    print("="*70)
    
    test_dates = [
        datetime(2026, 2, 24).date(),
        datetime(2026, 2, 26).date(),
    ]
    
    for test_date in test_dates:
        print(f"\n[{test_date}] Query Results:")
        print("-" * 70)
        
        # Use the exact query from daily_sales
        repair_query = (
            Device.query
            .filter(
                or_(
                    Device.actual_completion == test_date,
                    and_(
                        Device.deposit_paid > 0,
                        Device.deposit_paid_at.isnot(None),
                        func.date(Device.deposit_paid_at) == test_date,
                    ),
                    and_(
                        Device.full_payment_at.isnot(None),
                        func.date(Device.full_payment_at) == test_date,
                    ),
                )
            )
        )
        
        repairs = repair_query.all()
        print(f"Found {len(repairs)} repairs")
        
        for d in repairs:
            cust = Customer.query.get(d.customer_id)
            cust_name = cust.name if cust else 'Unknown'
            print(f"")
            print(f"  {d.ticket_number} | {cust_name}")
            print(f"    Deposit: {d.deposit_paid_at}")
            print(f"    Full Payment At: {d.full_payment_at}")
            print(f"    Status: {d.payment_status}")
            
            # Check what would be shown
            deposit_on_date = (
                d.deposit_paid_at and 
                d.deposit_paid_at.date() == test_date and 
                d.deposit_paid > 0
            )
            full_on_date = (
                d.full_payment_at and 
                d.full_payment_at.date() == test_date
            )
            
            if deposit_on_date:
                print(f"    -> DEPOSIT entry: P{d.deposit_paid}")
            if full_on_date:
                from decimal import Decimal
                full_amt = Decimal(d.total_cost or 0) - Decimal(d.deposit_paid or 0)
                print(f"    -> FULL PAYMENT entry: P{full_amt}")
            if not deposit_on_date and not full_on_date and d.payment_status == 'Paid':
                print(f"    -> PAID (legacy) entry: P{d.total_cost}")
    
    print("\n" + "="*70)
    print("EXPECTED RESULTS:")
    print("="*70)
    print("""
Feb 24:
  - JC-2026-036: Shows DEPOSIT (P500)
  - JC-2026-013: Shows PAID (legacy)

Feb 26:
  - JC-2026-036: Shows FULL PAYMENT (P750)
  - JC-2026-044: Shows DEPOSIT (P1000)
    """)
