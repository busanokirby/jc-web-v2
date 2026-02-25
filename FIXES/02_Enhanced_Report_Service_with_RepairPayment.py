"""
Enhanced Report Service with RepairPayment Support
Updates (app/services/report_service.py) to support the new RepairPayment model

MIGRATION GUIDE:
1. Create RepairPayment table
2. Run data migration to populate from Device.deposit_paid/deposit_paid_at
3. Keep Device.deposit_paid/deposit_paid_at for backward compatibility (calculated property)
4. Update this service to query RepairPayment records
"""

from __future__ import annotations

# imports required by the functions below
from datetime import date
from typing import Tuple, List, Dict
from decimal import Decimal
import logging

from app.extensions import db
from app.models.repair import Device
from app.models.sales import SalePayment, Sale

logger = logging.getLogger(__name__)

@staticmethod
def get_repairs_for_period(start_date: date, end_date: date) -> Tuple[List[Dict], Decimal, int]:
    """
    Get completed repairs with payments received in the period.
    
    Now queries RepairPayment table (consistent with SalePayment).
    Falls back to Device.deposit_paid if RepairPayment table not available.
    
    Returns:
        - List of repair dicts with payment info
        - Total revenue from repair payments
        - Repair transaction count
        
    Only includes:
        - Status: Completed
        - RepairPayment records with payment_date in period
        - Amount > 0
    """
    transactions = []
    total_revenue = Decimal("0.00")
    transaction_count = 0
    
    try:
        # Try to use RepairPayment table (new approach)
        from app.models.repair_payment import RepairPayment
        
        repair_payments = (
            RepairPayment.query
            .join(Device, RepairPayment.device_id == Device.id)
            .filter(
                RepairPayment.paid_at.isnot(None),
                db.func.date(RepairPayment.paid_at) >= start_date,
                db.func.date(RepairPayment.paid_at) <= end_date,
                RepairPayment.amount > 0,  # VALIDATION: Only positive payments
                Device.is_archived == True,  # Completed repairs
                ~Device.claimed_on_credit,  # Exclude credits
                ~Device.charge_waived,  # Exclude waived
            )
            .all()
        )
        
        for payment in repair_payments:
            repair = payment.device
            customer = repair.owner if hasattr(repair, 'owner') else None
            
            amount = Decimal(payment.amount or 0)
            if amount <= 0:
                continue
            
            transaction = {
                'ticket_number': repair.ticket_number,
                'customer_name': customer.display_name if customer else "Walk-in",
                'device_type': repair.device_type or "Device",
                'payment_method': payment.method or "Cash",
                'amount_paid': float(amount),
                'payment_date': payment.paid_at.date() if payment.paid_at else date.today(),
                'payment_status': 'Paid',  # RepairPayment means it's received
                'device_id': repair.id
            }
            
            transactions.append(transaction)
            total_revenue += amount
            transaction_count += 1
        
        return transactions, total_revenue, transaction_count
    
    except ImportError:
        # Fallback: RepairPayment table doesn't exist yet (migration pending)
        # Use legacy Device.deposit_paid approach
        logger.warning("RepairPayment table not available, using legacy Device.deposit_paid")
        
        repairs = (
            Device.query
            .filter(
                Device.is_archived == True,
                Device.actual_completion.isnot(None),
                Device.actual_completion >= start_date,
                Device.actual_completion <= end_date,
                ~Device.claimed_on_credit,
                ~Device.charge_waived,
                Device.deposit_paid > 0,  # Has deposit
            )
            .all()
        )
        
        for repair in repairs:
            amount_paid = Decimal(repair.deposit_paid or 0)
            if amount_paid <= 0:
                continue
            
            # Determine payment date
            if repair.deposit_paid_at:
                payment_date = repair.deposit_paid_at.date() if hasattr(repair.deposit_paid_at, 'date') else repair.deposit_paid_at
            else:
                payment_date = repair.actual_completion
            
            if not (start_date <= payment_date <= end_date):
                continue
            
            customer = repair.owner if hasattr(repair, 'owner') else None
            
            transaction = {
                'ticket_number': repair.ticket_number,
                'customer_name': customer.display_name if customer else "Walk-in",
                'device_type': repair.device_type or "Device",
                'payment_method': "Repair Payment",
                'amount_paid': float(amount_paid),
                'payment_date': payment_date,
                'payment_status': repair.payment_status,
                'device_id': repair.id
            }
            
            transactions.append(transaction)
            total_revenue += amount_paid
            transaction_count += 1
        
        return transactions, total_revenue, transaction_count


@staticmethod
def get_payment_breakdown(start_date: date, end_date: date) -> Dict[str, Dict]:
    """
    Get payment breakdown by method for the period.
    NOW INCLUDES REPAIRS!
    
    Returns: {
        'Cash': {'count': 10, 'total': 5000.00},
        'GCash': {'count': 5, 'total': 2500.00},
        'Repair Payment': {'count': 3, 'total': 1500.00},
        ...
    }
    """
    breakdown = {}
    
    # Get sales payments by method
    sales_by_method = (
        db.session.query(
            SalePayment.method,
            db.func.count(SalePayment.id).label('count'),
            db.func.sum(SalePayment.amount).label('total')
        )
        .join(Sale, SalePayment.sale_id == Sale.id)
        .filter(
            SalePayment.paid_at.isnot(None),
            db.func.date(SalePayment.paid_at) >= start_date,
            db.func.date(SalePayment.paid_at) <= end_date,
            SalePayment.amount > 0,
            Sale.status.in_(['PAID', 'PARTIAL']),
            ~Sale.claimed_on_credit
        )
        .group_by(SalePayment.method)
        .all()
    )
    
    for method_group in sales_by_method:
        method = method_group[0] or "Unknown"
        count = method_group[1] or 0
        total = Decimal(method_group[2] or 0)
        
        if method not in breakdown:
            breakdown[method] = {'count': 0, 'total': 0}
        breakdown[method]['count'] += count
        breakdown[method]['total'] += float(total)
    
    # Get repair payments by method (NEW)
    try:
        from app.models.repair_payment import RepairPayment
        
        repair_by_method = (
            db.session.query(
                RepairPayment.method,
                db.func.count(RepairPayment.id).label('count'),
                db.func.sum(RepairPayment.amount).label('total')
            )
            .join(Device, RepairPayment.device_id == Device.id)
            .filter(
                RepairPayment.paid_at.isnot(None),
                db.func.date(RepairPayment.paid_at) >= start_date,
                db.func.date(RepairPayment.paid_at) <= end_date,
                RepairPayment.amount > 0,
                Device.is_archived == True,
                ~Device.claimed_on_credit,
                ~Device.charge_waived,
            )
            .group_by(RepairPayment.method)
            .all()
        )
        
        for method_group in repair_by_method:
            method = method_group[0] or "Unknown"
            count = method_group[1] or 0
            total = Decimal(method_group[2] or 0)
            
            if method not in breakdown:
                breakdown[method] = {'count': 0, 'total': 0}
            breakdown[method]['count'] += count
            breakdown[method]['total'] += float(total)
    
    except ImportError:
        logger.debug("RepairPayment table not available for breakdown")
    
    return breakdown
