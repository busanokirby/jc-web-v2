#!/usr/bin/env python
"""Fix existing repairs with deposits that should be marked as Partial"""

import sys
from app import create_app
from app.extensions import db
from app.models.repair import Device
from app.services.financials import recompute_repair_financials
from decimal import Decimal

app = create_app()

with app.app_context():
    print("=" * 60)
    print("Fixing Repair Payment Status for Repairs with Deposits")
    print("=" * 60)
    
    # Find all repairs with deposits but wrong status
    repairs_with_deposits = Device.query.filter(Device.deposit_paid > 0).all()
    
    print(f"\nFound {len(repairs_with_deposits)} repairs with deposits")
    
    updated = 0
    for dev in repairs_with_deposits:
        print(f"\nTicket: {dev.ticket_number}")
        print(f"  Deposit: ₱{dev.deposit_paid}")
        print(f"  Total Cost: ₱{dev.total_cost}")
        print(f"  Status Before: {dev.payment_status}")
        
        # Recompute to fix status
        recompute_repair_financials(dev)
        
        print(f"  Status After: {dev.payment_status}")
        updated += 1
    
    # Commit changes
    db.session.commit()
    
    print(f"\n" + "=" * 60)
    print(f"Updated {updated} repairs")
    print("=" * 60)
    
    # Show summary
    print("\nSummary after update:")
    partial = Device.query.filter(Device.payment_status == 'Partial').all()
    pending = Device.query.filter(Device.payment_status == 'Pending').all()
    paid = Device.query.filter(Device.payment_status == 'Paid').all()
    
    print(f"  Partial: {len(partial)} repairs")
    partial_balance = sum((d.balance_due or Decimal("0.00")) for d in partial)
    print(f"    Total balance due: ₱{partial_balance}")
    
    print(f"  Pending: {len(pending)} repairs")
    pending_balance = sum((d.balance_due or Decimal("0.00")) for d in pending)
    print(f"    Total balance due: ₱{pending_balance}")
    
    print(f"  Paid: {len(paid)} repairs")
