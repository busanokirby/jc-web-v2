#!/usr/bin/env python
"""Test that deposits and full payments display separately on their own dates"""
import os
from datetime import datetime

os.environ['SECRET_KEY'] = 'dev-secret'
os.environ['FLASK_ENV'] = 'development'

from app import create_app, db
from app.models import Device

app = create_app()

with app.app_context():
    print("\n=== CHECKING REPAIR 36 (Feb 24 deposit, Feb 26 payment) ===")
    
    repair_36 = Device.query.filter_by(id=36).first()
    
    if repair_36:
        print(f"Repair ID: {repair_36.id}")
        print(f"Ticket: JC-{repair_36.received_date.year}-{repair_36.id:03d}")
        print(f"Total Cost: P{repair_36.total_cost}")
        print(f"Deposit Status:")
        print(f"  - Paid: P{repair_36.deposit_paid}")
        print(f"  - Paid At: {repair_36.deposit_paid_at}")
        print(f"Full Payment Status:")
        print(f"  - full_payment_at: {repair_36.full_payment_at}")
        print(f"  - Payment Status: {repair_36.payment_status}")
        print()
        
        # Verify dates are different
        if repair_36.deposit_paid_at and repair_36.full_payment_at:
            deposit_date = repair_36.deposit_paid_at.date()
            payment_date = repair_36.full_payment_at.date()
            print(f"Deposit Date: {deposit_date}")
            print(f"Payment Date: {payment_date}")
            
            if deposit_date != payment_date:
                print("SUCCESS: Deposit and payment are on DIFFERENT dates")
                print("  -> Should display deposit on Feb 24")
                print("  -> Should display payment on Feb 26")
            else:
                print("Same-day transaction (no separation needed)")
    else:
        print("Repair 36 not found")
    
    print("\n=== CHECKING OTHER REPAIRS WITH Feb 26 PAYMENTS ===")
    
    repairs_feb26 = Device.query.filter_by(payment_status='Paid').all()
    for r in repairs_feb26[:5]:
        if r.full_payment_at and r.full_payment_at.date() == datetime(2026, 2, 26).date():
            print(f"JC-{r.received_date.year}-{r.id:03d}: Payment on {r.full_payment_at.date()}")

print("\nTest complete.")
