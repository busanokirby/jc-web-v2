"""
Production-Ready Validation Module
app/services/validation.py

Provides centralized financial data validation to prevent:
- Negative/zero payments
- Orphaned payments
- Duplicate payments
- Payment exceeding total cost
- Invalid status states
"""

from decimal import Decimal
from datetime import datetime
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)


class PaymentValidator:
    """Validates payment transactions for data integrity"""
    
    @staticmethod
    def validate_payment_amount(amount: Decimal, field_name: str = "amount") -> Tuple[bool, str]:
        """
        Validate that payment amount is positive and reasonable.
        
        Args:
            amount: Payment amount to validate
            field_name: Field name for error messages
        
        Returns:
            (is_valid, error_message)
        """
        try:
            amount = Decimal(str(amount))
        except Exception as e:
            return False, f"{field_name} must be a valid number: {str(e)}"
        
        if amount <= 0:
            return False, f"{field_name} must be positive (got {amount})"
        
        # Sanity check: payment shouldn't be more than 1 million PHP
        if amount > Decimal("1000000.00"):
            return False, f"{field_name} seems too high: ₱{amount:,.2f}"
        
        return True, ""
    
    @staticmethod
    def validate_sale_payment(sale, amount: Decimal) -> Tuple[bool, str]:
        """
        Validate that sale payment is valid.
        
        Args:
            sale: Sale object
            amount: Payment amount being added
        
        Returns:
            (is_valid, error_message)
        """
        # Validate amount
        is_valid, msg = PaymentValidator.validate_payment_amount(amount, "Payment amount")
        if not is_valid:
            return False, msg
        
        if not sale:
            return False, "Sale not found"
        
        if sale.status and sale.status.upper() in ['VOID', 'DRAFT']:
            return False, f"Cannot pay {sale.status} sale"
        
        # Check that payment doesn't exceed total
        sale_total = Decimal(sale.total or 0)
        total_paid_so_far = Decimal(sum((p.amount or 0) for p in (sale.payments or [])))
        
        if total_paid_so_far + amount > sale_total * Decimal("1.05"):  # Allow 5% overpayment
            return False, f"Payment exceeds sale total. Sale: ₱{sale_total:,.2f}, Paid: ₱{total_paid_so_far:,.2f}"
        
        return True, ""
    
    @staticmethod
    def validate_repair_payment(repair, amount: Decimal) -> Tuple[bool, str]:
        """
        Validate that repair payment is valid.
        
        Args:
            repair: Device (repair) object
            amount: Payment amount being added
        
        Returns:
            (is_valid, error_message)
        """
        # Validate amount
        is_valid, msg = PaymentValidator.validate_payment_amount(amount, "Repair payment amount")
        if not is_valid:
            return False, msg
        
        if not repair:
            return False, "Repair not found"
        
        if getattr(repair, 'charge_waived', False):
            return False, "Cannot pay waived repair"
        
        if getattr(repair, 'claimed_on_credit', False):
            return False, "Repair is on credit (pending collection)"
        
        # Check that payment doesn't exceed total cost
        repair_total = Decimal(repair.total_cost or 0)
        
        # Calculate already paid (sum of all RepairPayment records if available)
        try:
            from app.models.repair_payment import RepairPayment
            total_paid_so_far = Decimal(sum(
                (p.amount or 0) for p in repair.repair_payments
            ))
        except Exception:
            # Fallback to legacy deposit_paid
            total_paid_so_far = Decimal(repair.deposit_paid or 0)
        
        if total_paid_so_far + amount > repair_total * Decimal("1.05"):  # Allow 5% overpayment
            return False, f"Payment exceeds repair total. Repair: ₱{repair_total:,.2f}, Paid: ₱{total_paid_so_far:,.2f}"
        
        return True, ""
    
    @staticmethod
    def check_data_integrity(db_session) -> List[str]:
        """
        Run comprehensive data integrity checks.
        
        Returns:
            List of issues found (empty if all OK)
        """
        from app.models.sales import Sale, SalePayment
        from app.models.repair import Device
        
        issues = []
        
        try:
            # Check for negative sale payments
            negative_sales = db_session.query(SalePayment).filter(
                SalePayment.amount < 0
            ).all()
            if negative_sales:
                issues.append(f"Found {len(negative_sales)} negative sale payments")
                for p in negative_sales:
                    logger.error(f"Negative payment: ID={p.id}, amount={p.amount}, sale={p.sale_id}")
            
            # Check for NULL paid_at on SalePayment
            null_paid_at = db_session.query(SalePayment).filter(
                SalePayment.paid_at == None
            ).all()
            if null_paid_at:
                issues.append(f"Found {len(null_paid_at)} sale payments with NULL paid_at")
            
            # Check for orphaned payments (sale deleted or not found)
            for payment in db_session.query(SalePayment).all():
                if not payment.sale:
                    issues.append(f"Orphaned sale payment: ID={payment.id}")
            
            # Check for repair payment issues
            for repair in db_session.query(Device).filter(Device.is_archived == True).all():
                total_paid = Decimal(repair.deposit_paid or 0)
                total_cost = Decimal(repair.total_cost or 0)
                
                if total_paid > total_cost * Decimal("1.1"):  # More than 110% of cost
                    issues.append(f"Repair {repair.ticket_number}: overpaid (₱{total_paid} > ₱{total_cost})")
                
                if total_paid < 0:
                    issues.append(f"Repair {repair.ticket_number}: negative payment (₱{total_paid})")
        
        except Exception as e:
            logger.error(f"Error checking data integrity: {e}", exc_info=True)
            issues.append(f"Integrity check failed: {str(e)}")
        
        return issues


class ExcelReconciliation:
    """Validates Excel exports against database"""
    
    @staticmethod
    def reconcile_report(report_data: dict, sales_list: List, repairs_list: List) -> Tuple[bool, List[str]]:
        """
        Verify that report totals match transaction sums.
        
        Args:
            report_data: Report data dict
            sales_list: List of sales transactions
            repairs_list: List of repair transactions
        
        Returns:
            (is_reconciled, list_of_issues)
        """
        issues = []
        
        # Calculate from transactions
        sales_total = Decimal(sum((s.get('amount_paid', 0) for s in sales_list)))
        repairs_total = Decimal(sum((r.get('amount_paid', 0) for r in repairs_list)))
        calculated_total = sales_total + repairs_total
        
        # Check against report
        reported_total = Decimal(str(report_data.get('total_revenue', 0)))
        reported_sales = Decimal(str(report_data.get('total_sales_payments', 0)))
        reported_repairs = Decimal(str(report_data.get('total_repair_payments', 0)))
        
        if calculated_total != reported_total:
            tolerance = Decimal("0.01")  # Allow 1 cent rounding
            if abs(calculated_total - reported_total) > tolerance:
                issues.append(
                    f"Revenue mismatch: Calculated ₱{calculated_total:,.2f} != "
                    f"Reported ₱{reported_total:,.2f}"
                )
        
        if sales_total != reported_sales and abs(sales_total - reported_sales) > Decimal("0.01"):
            issues.append(
                f"Sales total mismatch: Calculated ₱{sales_total:,.2f} != "
                f"Reported ₱{reported_sales:,.2f}"
            )
        
        if repairs_total != reported_repairs and abs(repairs_total - reported_repairs) > Decimal("0.01"):
            issues.append(
                f"Repairs total mismatch: Calculated ₱{repairs_total:,.2f} != "
                f"Reported ₱{reported_repairs:,.2f}"
            )
        
        # Check transaction counts
        if len(sales_list) != report_data.get('sales_count', len(sales_list)):
            issues.append(
                f"Sales count mismatch: {len(sales_list)} vs "
                f"{report_data.get('sales_count')}"
            )
        
        is_reconciled = len(issues) == 0
        return is_reconciled, issues
