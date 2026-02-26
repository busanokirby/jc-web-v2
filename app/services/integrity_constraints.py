"""
Database Integrity & Constraints - ACID-compliance utilities.

This module provides:
1. Validation hooks for financial transactions
2. Referential integrity checks
3. Orphaned record detection and cleanup
4. ACID property enforcement
"""

from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from typing import Tuple, Optional, List

from sqlalchemy import and_
from app.extensions import db
from app.models.sales import Sale, SalePayment
from app.models.repair import Device, RepairPartUsed
from app.models.repair_payment import RepairPayment


class IntegrityConstraints:
    """Database integrity validation and enforcement"""

    @staticmethod
    def validate_sale_payment(sale_id: int, amount: Decimal) -> Tuple[bool, Optional[str]]:
        """
        Validate before creating a sale payment.
        
        Returns:
            - (is_valid, error_message or None)
        """
        sale = Sale.query.get(sale_id)
        if not sale:
            return False, f"Sale {sale_id} not found"
        
        if sale.claimed_on_credit and amount > 0:
            # Partial payment is okay even if claimed_on_credit
            # but we're making a payment so clear the flag
            pass
        
        if sale.status and sale.status.upper() in ['VOID', 'DRAFT']:
            return False, f"Cannot add payment to {sale.status} sale"
        
        if amount <= 0:
            return False, f"Payment amount must be positive, got {amount}"
        
        # Check if payment would exceed sale total
        total_received = Decimal(sum((p.amount or 0) for p in (sale.payments or [])))
        if total_received + amount > (sale.total or 0) * Decimal("1.05"):  # Allow 5% overpayment tolerance
            return False, f"Payment would exceed sale total. Already received: {total_received}, Sale total: {sale.total}"
        
        return True, None

    @staticmethod
    def validate_repair_payment(device_id: int, amount: Decimal) -> Tuple[bool, Optional[str]]:
        """
        Validate before creating a repair payment.
        
        Returns:
            - (is_valid, error_message or None)
        """
        device = Device.query.get(device_id)
        if not device:
            return False, f"Device {device_id} not found"
        
        if device.charge_waived:
            return False, "Cannot add payment to waived-charge repair"
        
        if amount <= 0:
            return False, f"Payment amount must be positive, got {amount}"
        
        # Check if payment would exceed device total cost
        total_received = Decimal(device.deposit_paid or 0)
        if total_received + amount > (device.total_cost or 0) * Decimal("1.05"):  # Allow 5% overpayment tolerance
            return False, f"Payment would exceed device total. Already received: {total_received}, Device total: {device.total_cost}"
        
        return True, None

    @staticmethod
    def check_orphaned_payments() -> List[dict]:
        """
        Find orphaned payment records (payments with deleted sales/devices).
        
        Returns: List of orphaned payment records
        """
        orphaned = []
        
        # Check for orphaned sale payments
        try:
            orphaned_sale_payments = (
                db.session.query(SalePayment)
                .outerjoin(Sale)
                .filter(Sale.id.is_(None))
                .all()
            )
            for sp in orphaned_sale_payments:
                orphaned.append({
                    'type': 'sale_payment',
                    'id': sp.id,
                    'amount': float(sp.amount or 0),
                    'sale_id': sp.sale_id,
                })
        except Exception:
            pass
        
        # Check for orphaned repair payments
        try:
            orphaned_repair_payments = (
                db.session.query(RepairPayment)
                .outerjoin(Device)
                .filter(Device.id.is_(None))
                .all()
            )
            for rp in orphaned_repair_payments:
                orphaned.append({
                    'type': 'repair_payment',
                    'id': rp.id,
                    'amount': float(rp.amount or 0),
                    'device_id': rp.device_id,
                })
        except Exception:
            pass
        
        return orphaned

    @staticmethod
    def cleanup_orphaned_payments() -> int:
        """
        Delete orphaned payment records.
        
        Returns: Number of records deleted
        """
        count = 0
        
        # Delete orphaned sale payments
        try:
            orphaned_sale_payments = (
                SalePayment.query
                .outerjoin(Sale)
                .filter(Sale.id.is_(None))
                .all()
            )
            for sp in orphaned_sale_payments:
                db.session.delete(sp)
                count += 1
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error cleaning orphaned sale payments: {str(e)}")
        
        # Delete orphaned repair payments
        try:
            orphaned_repair_payments = (
                RepairPayment.query
                .outerjoin(Device)
                .filter(Device.id.is_(None))
                .all()
            )
            for rp in orphaned_repair_payments:
                db.session.delete(rp)
                count += 1
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error cleaning orphaned repair payments: {str(e)}")
        
        return count

    @staticmethod
    def reconcile_sale_status(sale_id: int) -> None:
        """
        Recalculate and update sale payment status based on actual payments.
        
        This MUST be called after any payment is added/removed.
        """
        sale = Sale.query.get(sale_id)
        if not sale:
            return
        
        total_paid = Decimal(sum((p.amount or 0) for p in (sale.payments or [])))
        sale_total = Decimal(sale.total or 0)
        
        # Determine status
        if sale_total <= 0:
            status = "PAID"
        elif total_paid >= sale_total:
            status = "PAID"
            sale.claimed_on_credit = False  # Clear credit flag if fully paid
        elif total_paid > 0:
            status = "PARTIAL"
        else:
            status = "PARTIAL" if sale.claimed_on_credit else "PARTIAL"  # Default to partial for non-paid
        
        sale.status = status
        db.session.add(sale)
        db.session.commit()

    @staticmethod
    def reconcile_device_status(device_id: int) -> None:
        """
        Recalculate and update device payment status based on actual payments.
        
        This MUST be called after any payment is added/removed.
        """
        from app.services.financials import recompute_repair_financials
        
        device = Device.query.get(device_id)
        if not device:
            return
        
        # Use existing financial computation service
        recompute_repair_financials(device)
        db.session.add(device)
        db.session.commit()

    @staticmethod
    def validate_financial_integrity() -> Tuple[bool, List[str]]:
        """
        Comprehensive integrity check across all financial data.
        
        Returns:
            - (is_valid, list_of_issues)
        """
        issues = []
        
        # Check 1: No negative payments
        try:
            neg_sales_payments = SalePayment.query.filter(SalePayment.amount < 0).all()
            if neg_sales_payments:
                issues.append(f"Found {len(neg_sales_payments)} negative sale payments (should be refunds)")
        except Exception as e:
            issues.append(f"Error checking negative sale payments: {str(e)}")
        
        try:
            neg_repair_payments = RepairPayment.query.filter(RepairPayment.amount < 0).all()
            if neg_repair_payments:
                issues.append(f"Found {len(neg_repair_payments)} negative repair payments (should be refunds)")
        except Exception as e:
            issues.append(f"Error checking negative repair payments: {str(e)}")
        
        # Check 2: Orphaned payments
        orphaned = IntegrityConstraints.check_orphaned_payments()
        if orphaned:
            issues.append(f"Found {len(orphaned)} orphaned payment records")
        
        # Check 3: Sales with payments but no status
        try:
            sales_without_status = Sale.query.filter(Sale.status.is_(None)).all()
            if sales_without_status:
                issues.append(f"Found {len(sales_without_status)} sales without status")
        except Exception as e:
            issues.append(f"Error checking sales without status: {str(e)}")
        
        # Check 4: Repairs with invalid payment status
        try:
            invalid_statuses = Device.query.filter(
                ~Device.payment_status.in_(['Pending', 'Partial', 'Paid', None])
            ).all()
            if invalid_statuses:
                issues.append(f"Found {len(invalid_statuses)} repairs with invalid payment status")
        except Exception as e:
            issues.append(f"Error checking repair payment status: {str(e)}")
        
        # Check 5: Devices with balance_due > total_cost
        try:
            over_balance = Device.query.filter(
                Device.balance_due > Device.total_cost
            ).all()
            if over_balance:
                issues.append(f"Found {len(over_balance)} repairs where balance_due > total_cost")
        except Exception as e:
            issues.append(f"Error checking device balances: {str(e)}")
        
        return len(issues) == 0, issues

    @staticmethod
    def generate_integrity_report() -> dict:
        """
        Generate full integrity report for audit purposes.
        
        Returns: Comprehensive report dict
        """
        is_valid, issues = IntegrityConstraints.validate_financial_integrity()
        orphaned = IntegrityConstraints.check_orphaned_payments()
        
        # Count totals
        try:
            sale_count = Sale.query.count()
            sale_payment_count = SalePayment.query.count()
            sale_payment_total = Decimal(sum((p.amount or 0) for p in SalePayment.query.all()) or 0)
        except Exception:
            sale_count = sale_payment_count = 0
            sale_payment_total = Decimal("0")
        
        try:
            device_count = Device.query.count()
            repair_payment_count = RepairPayment.query.count() if RepairPayment else 0
            repair_payment_total = Decimal(sum((p.amount or 0) for p in RepairPayment.query.all()) or 0) if RepairPayment else Decimal("0")
        except Exception:
            device_count = repair_payment_count = 0
            repair_payment_total = Decimal("0")
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'is_valid': is_valid,
            'issues': issues,
            'orphaned_records': orphaned,
            'statistics': {
                'sales_count': sale_count,
                'sale_payments_count': sale_payment_count,
                'sale_payments_total': float(sale_payment_total),
                'devices_count': device_count,
                'repair_payments_count': repair_payment_count,
                'repair_payments_total': float(repair_payment_total),
            },
            'recommendations': IntegrityConstraints._get_recommendations(is_valid, issues, orphaned)
        }

    @staticmethod
    def _get_recommendations(is_valid: bool, issues: List[str], orphaned: List[dict]) -> str:
        """Generate recommendations based on integrity report"""
        if is_valid and not orphaned:
            return "✓ All systems nominal. No integrity issues detected."
        
        recs = []
        if orphaned:
            recs.append(f"URGENT: Run IntegrityConstraints.cleanup_orphaned_payments() to delete {len(orphaned)} orphaned records")
        if issues:
            recs.append("Review and fix the following issues: " + "; ".join(issues))
        
        return "\n".join(recs) if recs else "No recommendations."
