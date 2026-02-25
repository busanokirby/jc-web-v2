"""
Report Generation Service - Payment-based reporting logic
Ensures revenue = money received (using payment_date and actual amounts paid)
"""
from __future__ import annotations
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from app.extensions import db
from app.models.sales import Sale, SaleItem, SalePayment
from app.models.repair import Device, RepairPartUsed
from app.models.customer import Customer


class ReportService:
    """Service for generating payment-based sales and repair reports"""
    
    @staticmethod
    def get_sales_for_period(start_date: date, end_date: date) -> Tuple[List[Dict], Decimal, int]:
        """
        Get completed sales with payments received in the period.
        
        Returns:
            - List of sale dicts with payment info
            - Total revenue from payments
            - Transaction count
            
        Only includes:
            - Status: Paid or Partially Paid
            - payment_date within period
            - actual amount_paid  
        """
        transactions = []
        total_revenue = Decimal("0.00")
        transaction_count = 0
        
        # Query SalePayment records within date range
        sale_payments = (
            SalePayment.query
            .join(Sale, SalePayment.sale_id == Sale.id)
            .filter(
                SalePayment.paid_at.isnot(None),
                db.func.date(SalePayment.paid_at) >= start_date,
                db.func.date(SalePayment.paid_at) <= end_date,
                Sale.status.in_(['PAID', 'PARTIAL']),
                ~Sale.claimed_on_credit  # Exclude credits
            )
            .all()
        )
        
        for payment in sale_payments:
            sale = payment.sale
            customer = sale.customer if sale.customer else None
            
            amount = Decimal(payment.amount or 0)
            if amount <= 0:
                continue
            
            # Build item description
            items_desc = ""
            if sale.items:
                items_desc = ", ".join(
                    f"{item.qty}×{item.product.name}" 
                    for item in sale.items if item.product
                )
            
            transaction = {
                'invoice_number': sale.invoice_no,
                'customer_name': customer.display_name if customer else "Walk-in",
                'payment_method': payment.method or "Cash",
                'amount_paid': float(amount),
                'payment_date': payment.paid_at.date() if payment.paid_at else date.today(),
                'items_description': items_desc,
                'sale_id': sale.id,
                'payment_status': sale.status
            }
            
            transactions.append(transaction)
            total_revenue += amount
            transaction_count += 1
        
        return transactions, total_revenue, transaction_count
    
    @staticmethod
    def get_repairs_for_period(start_date: date, end_date: date) -> Tuple[List[Dict], Decimal, int]:
        """
        Get completed repairs with payments received in the period.
        
        Returns:
            - List of repair dicts with payment info
            - Total revenue from repair payments
            - Repair transaction count
            
        Only includes:
            - Status: Completed
            - Payment received (deposit_paid > 0 or payment_status = Paid)
            - Payment date within period
        """
        transactions = []
        total_revenue = Decimal("0.00")
        transaction_count = 0
        
        # Query repairs completed with payments
        repairs = (
            Device.query
            .filter(
                Device.is_archived == True,  # Completed repairs are archived
                Device.actual_completion.isnot(None),
                Device.actual_completion >= start_date,
                Device.actual_completion <= end_date,
                ~Device.claimed_on_credit,  # Exclude credits
                ~Device.charge_waived,  # Exclude waived charges
            )
            .all()
        )
        
        for repair in repairs:
            # Only include repairs with payments
            amount_paid = Decimal(repair.deposit_paid or 0)
            if amount_paid <= 0:
                # Check if fully paid
                if repair.payment_status != 'Paid':
                    continue
                amount_paid = Decimal(repair.total_cost or 0)
            
            # Determine payment date (prioritize deposit_paid_at, fallback to actual_completion)
            if repair.deposit_paid_at:
                payment_date = repair.deposit_paid_at.date() if hasattr(repair.deposit_paid_at, 'date') else repair.deposit_paid_at
            else:
                payment_date = repair.actual_completion
            
            # Check if payment date is in period
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
        
        Returns: {
            'Cash': {'count': 10, 'total': 5000.00},
            'GCash': {'count': 5, 'total': 2500.00},
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
        
        return breakdown
    
    @staticmethod
    def generate_report_data(start_date: date, end_date: date, frequency: str = 'daily') -> Dict:
        """
        Generate complete report data for the period.
        
        Args:
            start_date: Report period start
            end_date: Report period end
            frequency: 'daily', 'every_3_days', 'weekly'
        
        Returns: {
            'date_range': 'Feb 25, 2026',
            'frequency': 'daily',
            'total_revenue': 12500.00,
            'total_transactions': 15,
            'total_sales_payments': 10000.00,
            'total_repair_payments': 2500.00,
            'payment_breakdown': {...},
            'sales_records': [...],
            'repair_records': [...]
        }
        """
        sales, sales_revenue, sales_count = ReportService.get_sales_for_period(start_date, end_date)
        repairs, repair_revenue, repair_count = ReportService.get_repairs_for_period(start_date, end_date)
        breakdown = ReportService.get_payment_breakdown(start_date, end_date)
        
        total_revenue = sales_revenue + repair_revenue
        total_transactions = sales_count + repair_count
        
        # Format date range for display
        if start_date == end_date:
            date_range = start_date.strftime('%B %d, %Y')
        else:
            date_range = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
        
        return {
            'date_range': date_range,
            'frequency': frequency,
            'total_revenue': float(total_revenue),
            'total_transactions': total_transactions,
            'total_sales_payments': float(sales_revenue),
            'total_repair_payments': float(repair_revenue),
            'payment_breakdown': breakdown,
            'sales_records': sales,
            'repair_records': repairs,
            'report_period': {
                'start': start_date,
                'end': end_date
            }
        }
    
    @staticmethod
    def get_report_period(frequency: str, reference_date: date = None) -> Tuple[date, date]:
        """
        Calculate report period based on frequency.
        
        Args:
            frequency: 'daily', 'every_3_days', 'weekly'
            reference_date: Optional reference date (defaults to today)
        
        Returns: (start_date, end_date)
        """
        if reference_date is None:
            reference_date = date.today()
        
        if frequency == 'daily':
            return reference_date, reference_date
        elif frequency == 'every_3_days':
            start = reference_date - timedelta(days=2)
            return start, reference_date
        elif frequency == 'weekly':
            start = reference_date - timedelta(days=6)
            return start, reference_date
        else:
            return reference_date, reference_date
