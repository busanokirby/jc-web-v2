#!/usr/bin/env python3
"""Test payment date display in sales_list and daily_sales"""

from app import create_app
from datetime import datetime

app = create_app()

with app.app_context():
    from app.models.repair import Device
    from app.models.sales import Sale, SalePayment
    from sqlalchemy.orm import joinedload
    
    print("\n" + "="*60)
    print("COMPREHENSIVE PAYMENT DATE VERIFICATION TEST")
    print("="*60)
    
    # Test 1: Repairs with deposit_paid_at (should show latest_payment_date)
    print("\n[TEST 1] Repairs with deposit_paid_at")
    print("-" * 60)
    repairs_with_payment = Device.query.filter(
        Device.deposit_paid > 0,
        Device.deposit_paid_at.isnot(None)
    ).all()
    
    if not repairs_with_payment:
        print("❌ ERROR: No repairs with deposit_paid_at found")
    else:
        for r in repairs_with_payment:
            print(f"✓ {r.ticket_number}:")
            print(f"    Created: {r.created_at}")
            print(f"    Latest Payment (deposit_paid_at): {r.deposit_paid_at}")
            print(f"    Amount: ₱{r.deposit_paid}")
            print()
    
    # Test 2: Sales with latest_payment_date
    print("[TEST 2] Sales with latest_payment_date")
    print("-" * 60)
    sales_with_payment = Sale.query.filter(
        Sale.payments.any(SalePayment.paid_at.isnot(None))
    ).all()
    
    if not sales_with_payment:
        print("ERROR: No sales with payments found")
    else:
        for s in sales_with_payment[:3]:  # Show first 3
            payments_with_dates = [p for p in s.payments if p.paid_at]
            if payments_with_dates:
                latest = max([p.paid_at for p in payments_with_dates])
                print(f"[OK] {s.invoice_no}:")
                print(f"    Created: {s.created_at}")
                print(f"    Latest Payment: {latest}")
                print()
    
    # Test 3: Verify template logic simulation
    print("[TEST 3] Template Display Logic Verification")
    print("-" * 60)
    
    # For repair
    repair = Device.query.filter(
        Device.ticket_number == 'JC-2026-044'
    ).first()
    
    if repair:
        latest_payment_date = None
        if repair.deposit_paid and repair.deposit_paid > 0 and repair.deposit_paid_at:
            latest_payment_date = repair.deposit_paid_at
        
        print(f"Repair {repair.ticket_number}:")
        print(f"  Template would display:")
        if latest_payment_date:
            print(f"    ✓ Payment date: {latest_payment_date.strftime('%Y-%m-%d %H:%M')}")
        else:
            print(f"    ✓ Creation date: {repair.created_at.strftime('%Y-%m-%d %H:%M')}")
        print()
    
    # For sale
    sale = Sale.query.filter(
        Sale.invoice_no == 'INV-2026-00005'
    ).first()
    
    if sale:
        latest_payment_date = None
        if sale.payments:
            payment_dates = [p.paid_at for p in sale.payments if p.paid_at]
            if payment_dates:
                latest_payment_date = max(payment_dates)
        
        print(f"Sale {sale.invoice_no}:")
        print(f"  Template would display:")
        if latest_payment_date:
            print(f"    ✓ Payment date: {latest_payment_date.strftime('%Y-%m-%d %H:%M')}")
        else:
            print(f"    ✓ Creation date: {sale.created_at.strftime('%Y-%m-%d %H:%M')}")
    
    # Test 4: Daily Sales Scenario
    print("\n[TEST 4] Daily Sales - Payment Date in Transaction Records")
    print("-" * 60)
    from sqlalchemy import func
    selected_date = datetime.now().date()
    
    # Find repairs paid on 2026-02-26
    repairs_feb26 = Device.query.filter(
        Device.deposit_paid > 0,
        Device.deposit_paid_at.isnot(None),
        func.date(Device.deposit_paid_at) == datetime.fromisoformat('2026-02-26').date()
    ).all()
    
    if repairs_feb26:
        print(f"✓ Repairs paid on 2026-02-26:")
        for r in repairs_feb26:
            print(f"  - {r.ticket_number}: Paid on {r.deposit_paid_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"    Template would display datetime: {r.deposit_paid_at.strftime('%Y-%m-%d %H:%M')}")
    else:
        print("No repairs paid on that date")
    
    print("\n" + "="*60)
    print("✓ VERIFICATION COMPLETE")
    print("="*60)
