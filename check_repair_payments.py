#!/usr/bin/env python3
"""Check repair payment structure"""

from app import create_app
from app.models.repair import Device

app = create_app()
with app.app_context():
    repairs = Device.query.all()
    
    print('=== Repairs with Deposit ===')
    for r in repairs:
        if r.deposit_paid and r.deposit_paid > 0 and r.deposit_paid_at:
            print(f'Ticket: {r.ticket_number}')
            print(f'  Deposit: ₱{r.deposit_paid} at {r.deposit_paid_at}')
            print(f'  Total Cost: ₱{r.total_cost}')
            print(f'  Balance Due: ₱{r.balance_due}')
            print(f'  Payment Status: {r.payment_status}')
            print(f'  Has repair_payments: {hasattr(r, "repair_payments")}')
            if hasattr(r, 'repair_payments'):
                print(f'  Num payments: {len(r.repair_payments)}')
                for p in r.repair_payments:
                    print(f'    - ₱{p.amount} at {p.paid_at}')
            print()
