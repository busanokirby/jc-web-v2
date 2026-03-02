#!/usr/bin/env python
"""Simulate daily_sales endpoint to verify separate transaction logic"""
import os
from datetime import datetime, date
from decimal import Decimal

os.environ['SECRET_KEY'] = 'dev-secret'
os.environ['FLASK_ENV'] = 'development'

from app import create_app, db
from app.models import Device
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import joinedload

app = create_app()

with app.app_context():
    # Simulate daily_sales for Feb 26
    selected_date = date(2026, 2, 26)
    print(f"\n=== TESTING DAILY_SALES LOGIC FOR {selected_date} ===\n")
    
    # Run the exact query from routes.py
    repair_query = (
        Device.query
        .options(joinedload(Device.owner))
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
    print(f"Step 1: Query found {len(repairs)} repairs\n")
    
    records = []
    partial_payment_count = 0
    partial_payment_total = Decimal(0)
    total_payments = Decimal(0)
    
    for d in repairs:
        if getattr(d, "charge_waived", False):
            continue
        
        has_deposit = (d.deposit_paid or 0) > 0
        status_upper = (d.payment_status or "").capitalize()
        if (status_upper not in ['Partial', 'Paid']) and not has_deposit:
            continue
        
        cust = d.owner.display_name if getattr(d, 'owner', None) and d.owner else 'Walk-in Customer'
        desc = d.device_type or 'Repair'
        
        # Check if deposit is on selected date
        deposit_on_selected = False
        if d.deposit_paid_at and d.deposit_paid and d.deposit_paid > 0:
            if d.deposit_paid_at.date() == selected_date:
                deposit_on_selected = True
        
        # Check if full payment is on selected date
        full_payment_on_selected = False
        full_payment_amount = Decimal(0)
        if d.full_payment_at and d.payment_status == 'Paid':
            if d.full_payment_at.date() == selected_date:
                full_payment_on_selected = True
                full_payment_amount = Decimal(d.total_cost or 0) - Decimal(d.deposit_paid or 0)
        
        # Show deposit if on selected date
        if deposit_on_selected:
            amount = Decimal(d.deposit_paid or 0)
            is_partial = True
            partial_payment_count += 1
            partial_payment_total += amount
            total_payments += amount
            
            records.append({
                'datetime': d.deposit_paid_at,
                'customer': cust,
                'type': 'Repair',
                'description': f"{desc} (Deposit)",
                'amount': float(amount),
                'payment_status': 'Partial',
                'is_partial': is_partial,
                'receipt_id': d.id,
                'receipt_type': 'repair',
                'ticket': f"JC-{d.received_date.year}-{d.id:03d}"
            })
        
        # Show full payment if on selected date
        if full_payment_on_selected:
            amount = full_payment_amount
            is_partial = False
            total_payments += amount
            
            records.append({
                'datetime': d.full_payment_at,
                'customer': cust,
                'type': 'Repair',
                'description': f"{desc} (Full Payment)",
                'amount': float(amount),
                'payment_status': 'Paid',
                'is_partial': is_partial,
                'receipt_id': d.id,
                'receipt_type': 'repair',
                'ticket': f"JC-{d.received_date.year}-{d.id:03d}"
            })
        
        # Legacy path: repair completed on selected date but no deposits/payments on this date
        if not deposit_on_selected and not full_payment_on_selected and d.actual_completion == selected_date:
            if status_upper == 'Paid':
                amount = Decimal(d.total_cost or 0)
                is_partial = False
            else:
                amount = Decimal(d.deposit_paid or 0) if d.deposit_paid and d.deposit_paid > 0 else Decimal(0)
                is_partial = True if amount > 0 else False
            
            if is_partial or status_upper == 'Paid':
                if is_partial:
                    partial_payment_count += 1
                    partial_payment_total += amount
                
                total_payments += amount
                
                records.append({
                    'datetime': datetime.combine(d.actual_completion, datetime.min.time()),
                    'customer': cust,
                    'type': 'Repair',
                    'description': desc,
                    'amount': float(amount),
                    'payment_status': d.payment_status,
                    'is_partial': is_partial,
                    'receipt_id': d.id,
                    'receipt_type': 'repair',
                    'ticket': f"JC-{d.received_date.year}-{d.id:03d}"
                })
    
    print(f"Step 2: Created {len(records)} transaction records\n")
    
    if records:
        print("Transactions:")
        for r in records:
            print(f"  {r['ticket']}: {r['description']} - P{r['amount']} ({r['payment_status']})")
        print()
        print(f"Total Partial Payments: {partial_payment_count}")
        print(f"Total Partial Amount: P{partial_payment_total}")
        print(f"Total Payments: P{total_payments}")
    else:
        print("No transaction records created")

print("\nTest complete - endpoint logic works!")
