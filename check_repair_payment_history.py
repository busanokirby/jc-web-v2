#!/usr/bin/env python3
"""Check repair payment history and identify the bug"""

from app import create_app
from datetime import datetime

app = create_app()
with app.app_context():
    from app.models.repair import Device
    
    # Check if RepairPayment table exists and has data
    try:
        from app.models.repair_payment import RepairPayment
        payments = RepairPayment.query.all()
        print(f'RepairPayment records found: {len(payments)}')
        for p in payments:
            print(f'  Device {p.device_id}: ₱{p.amount} on {p.paid_at}')
    except Exception as e:
        print(f'RepairPayment check failed: {str(e)}')
    
    # Check a specific repair to see its payment history
    repair = Device.query.filter(Device.ticket_number == 'JC-2026-036').first()
    if repair:
        print(f'\n=== Repair JC-2026-036 Full Payment History ===')
        print(f'Deposit: ₱{repair.deposit_paid} on {repair.deposit_paid_at}')
        print(f'Total Cost: ₱{repair.total_cost}')
        print(f'Status: {repair.payment_status}')
        
        # The issue: if status is Paid but deposit != total_cost
        # Then there must be another payment made after the deposit
        if repair.payment_status == 'Paid' and repair.deposit_paid < repair.total_cost:
            additional = repair.total_cost - repair.deposit_paid
            print(f'\nAdditional payment needed: ₱{additional}')
            print('But we do not know WHEN this additional payment was made!')
            print('This is the bug - we are treating deposit_paid_at as the latest payment')
            print('\nWhat the user wants:')
            print('- If both payments on same day: combine as one entry in daily_sales')
            print('- If on different days: show as SEPARATE entries in daily_sales')
