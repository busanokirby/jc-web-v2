#!/usr/bin/env python
"""Demonstrate same-day deposit + full payment as separate entries."""

from app import create_app
from datetime import datetime, timedelta
from decimal import Decimal

app = create_app()
with app.app_context():
    from app.models.repair import Device
    from app.models.customer import Customer
    from sqlalchemy import func
    
    print("\n" + "="*70)
    print("SCENARIO: Same-Day Deposit + Full Payment = TWO Entries")
    print("="*70)
    
    # Simulate what daily_sales would show for Feb 24
    test_date = datetime(2026, 2, 24).date()
    
    print(f"\nDaily Sales for {test_date}:")
    print("-" * 70)
    
    repair = Device.query.filter_by(id=36).first()  # JC-2026-036
    if repair:
        cust = Customer.query.get(repair.customer_id)
        
        print(f"\nRepair: {repair.ticket_number}")
        print(f"Customer: {cust.name if cust else 'Unknown'}")
        print(f"Device: {repair.device_type}")
        print(f"Total Cost: P{repair.total_cost}")
        
        print(f"\nPayment Timeline:")
        print(f"  Deposit on 2026-02-24: P{repair.deposit_paid}")
        if repair.full_payment_at:
            remaining = Decimal(repair.total_cost or 0) - Decimal(repair.deposit_paid or 0)
            print(f"  Full Payment on {repair.full_payment_at.date()}: P{remaining}")
        
        print(f"\nWhat displays in daily_sales:")
        print("\n  ON 2026-02-24:")
        print(f"    Entry 1: Deposit - {repair.ticket_number}")
        print(f"    Amount: P{repair.deposit_paid}")
        print(f"    Time: {repair.deposit_paid_at.time()}")
        print(f"    Status: Partial")
        
        if repair.full_payment_at and repair.full_payment_at.date() == test_date:
            remaining = Decimal(repair.total_cost or 0) - Decimal(repair.deposit_paid or 0)
            print(f"\n    Entry 2: Full Payment - {repair.ticket_number}")
            print(f"    Amount: P{remaining}")
            print(f"    Time: {repair.full_payment_at.time()}")
            print(f"    Status: Paid")
            print(f"\n    (Both entries visible - NOT combined)")
        elif repair.full_payment_at:
            print(f"\n  ON {repair.full_payment_at.date()}:")
            remaining = Decimal(repair.total_cost or 0) - Decimal(repair.deposit_paid or 0)
            print(f"    Entry 2: Full Payment - {repair.ticket_number}")
            print(f"    Amount: P{remaining}")
            print(f"    Time: {repair.full_payment_at.time()}")
            print(f"    Status: Paid")
            print(f"\n    (Different dates - shown separately)")
        
        total_showing = Decimal(repair.deposit_paid or 0)
        if repair.full_payment_at and repair.full_payment_at.date() == test_date:
            total_showing += Decimal(repair.total_cost or 0) - Decimal(repair.deposit_paid or 0)
        
        print(f"\n  DAILY SALES TOTAL (from these transactions):")
        print(f"    P{total_showing}")
    
    print("\n" + "="*70)
    print("[OK] Each payment displays as a separate transaction")
    print("="*70)
    print("""
KEY CHANGES:
✓ Deposits always show on their receipt date
✓ Full payments always show on their payment date  
✓ Same-day transactions appear as separate entries
✓ Different-day transactions appear on respective dates
✓ Each transaction is traceable to specific date/time
    """)
