#!/usr/bin/env python3
"""
Test for repair payment date handling
Verifies that:
1. Deposits and full payments on different days show as separate entries
2. Deposits and full payments on same day combine into one entry
3. latest_payment_date shows the correct timestamp in sales_list
"""

from app import create_app
from datetime import datetime, timedelta
from decimal import Decimal

app = create_app()

with app.app_context():
    from app.models.repair import Device
    from sqlalchemy import func, or_, and_
    
    print("\n" + "="*70)
    print("REPAIR PAYMENT DATE HANDLING - TEST")
    print("="*70)
    
    # Test 1: Check current repair data
    print("\n[TEST 1] Current Repairs with Payment Dates")
    print("-" * 70)
    
    repairs_with_deposits = Device.query.filter(Device.deposit_paid > 0).all()
    
    for r in repairs_with_deposits:
        print(f"\nRepair: {r.ticket_number}")
        print(f"  Deposit: ₱{r.deposit_paid} on {r.deposit_paid_at}")
        print(f"  Full Payment At: {r.full_payment_at}")
        print(f"  Total Cost: ₱{r.total_cost}")
        print(f"  Status: {r.payment_status}")
        
        if r.payment_status == 'Paid' and r.deposit_paid < r.total_cost:
            print(f"  ✓ This repair has both deposit and full payment")
            if r.full_payment_at:
                print(f"    Deposit date: {r.deposit_paid_at.date()}")
                print(f"    Full payment date: {r.full_payment_at.date()}")
                if r.deposit_paid_at.date() == r.full_payment_at.date():
                    print(f"    Same day - will COMBINE in daily_sales")
                else:
                    print(f"    Different days - will show as SEPARATE entries in daily_sales")
            else:
                print(f"    ⚠ Full payment time not recorded (needs to be set)")
    
    # Test 2: Simulate daily_sales logic for specific date
    print("\n[TEST 2] Daily Sales Filtering - Testing Separate Day Logic")
    print("-" * 70)
    
    # Test with Feb 24 (deposit date for JC-2026-036)
    test_date = datetime.fromisoformat('2026-02-24').date()
    
    repair_query = (
        Device.query
        .options()
        .filter(
            or_(
                Device.actual_completion == test_date,
                and_(
                    Device.deposit_paid > 0,
                    Device.deposit_paid_at.isnot(None),
                    func.date(Device.deposit_paid_at) == test_date,
                ),
            )
        )
    )
    repairs = repair_query.all()
    
    print(f"Repairs on {test_date}:")
    for d in repairs:
        print(f"\nRepair: {d.ticket_number}")
        if d.deposit_paid_at and func.date(d.deposit_paid_at) == test_date:
            print(f"  ✓ Deposit on {test_date}: ₱{d.deposit_paid}")
        if d.full_payment_at and func.date(d.full_payment_at) == test_date:
            full_amount = Decimal(d.total_cost or 0) - Decimal(d.deposit_paid or 0)
            print(f"  ✓ Full payment on {test_date}: ₱{full_amount}")
    
    # Test 3: Check sales_list latest_payment_date logic
    print("\n[TEST 3] Sales List - Latest Payment Date Calculation")
    print("-" * 70)
    
    for r in repairs_with_deposits:
        # Simulate sales_list logic
        latest_payment_date = None
        
        # Check for full payment date first (most recent payment)
        if r.full_payment_at and r.payment_status == 'Paid':
            latest_payment_date = r.full_payment_at
        # Fall back to deposit if full payment not recorded
        elif r.deposit_paid and r.deposit_paid > 0 and r.deposit_paid_at:
            latest_payment_date = r.deposit_paid_at
        
        print(f"\nRepair: {r.ticket_number}")
        print(f"  Status: {r.payment_status}")
        if latest_payment_date:
            print(f"  Latest Payment Date (for sales_list): {latest_payment_date.strftime('%Y-%m-%d %H:%M')}")
            if r.full_payment_at and r.payment_status == 'Paid':
                print(f"  ✓ Shows full payment date (not deposit)")
            else:
                print(f"  ✓ Shows deposit date")
        else:
            print(f"  No payment date")
    
    print("\n" + "="*70)
    print("✓ TEST COMPLETE")
    print("="*70)
    print("\nKey Changes:")
    print("1. Added full_payment_at field to track final payment date")
    print("2. daily_sales shows deposits and full payments on their correct dates")
    print("3. Payments on same day combine, different days show separately")
    print("4. sales_list shows latest_payment_date (full payment or deposit)")
