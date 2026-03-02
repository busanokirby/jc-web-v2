"""
Report Generation Service - Payment-based reporting logic
Ensures revenue = money received (using payment_date and actual amounts paid)
"""
from __future__ import annotations
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Tuple, Optional

from sqlalchemy import func, or_, and_
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.sales import Sale, SaleItem, SalePayment
from app.models.repair import Device, RepairPartUsed
from app.models.customer import Customer

# Philippines timezone: UTC+8
PHILIPPINES_TZ = timezone(timedelta(hours=8))

def get_ph_now():
    """Get current datetime in Philippines timezone (UTC+8)"""
    return datetime.now(PHILIPPINES_TZ)

def get_ph_date():
    """Get current date in Philippines timezone (UTC+8)"""
    return get_ph_now().date()


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
            - amount > 0 (no negative/refund payments)
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
                SalePayment.amount > 0,  # VALIDATION: Only positive payments
                Sale.status.in_(['PAID', 'PARTIAL']),  # Exclude drafts/void
                ~Sale.claimed_on_credit  # Exclude credits
            )
            .all()
        )
        
        for payment in sale_payments:
            sale = payment.sale
            customer = sale.customer if sale.customer else None
            
            amount = Decimal(payment.amount or 0)
            # Double-check: amount must be positive (defensive programming)
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
    def build_daily_sales_context(selected_date: Optional[date]) -> Dict:
        """Return context data identical to what `/sales/daily-sales` expects.

        The selected_date can be None in some callers; we normalize to today.

        This consolidates the query logic so other consumers (email, tests)
        can reuse the same dataset without duplication.  The returned dict
        contains keys:
            sales_records, total_sales, total_partial_count,
            total_partial_amount, report_date, today, now
        """
        from datetime import datetime, date as _date
        import logging
        logger_ctx = logging.getLogger(__name__)
        
        # normalize selected_date; allow None
        today_date = get_ph_date()
        if selected_date is None:
            selected_date = today_date
        elif not isinstance(selected_date, _date):
            try:
                selected_date = datetime.fromisoformat(str(selected_date)).date()
            except Exception:
                selected_date = today_date

        # Prevent future dates
        if selected_date > today_date:
            selected_date = today_date

        start_dt = datetime.combine(selected_date, datetime.min.time())
        end_dt = datetime.combine(selected_date, datetime.max.time())
        
        logger_ctx.info(f"build_daily_sales_context: querying for date {selected_date} (start_dt={start_dt}, end_dt={end_dt})")

        records: list[dict] = []
        total_payments = Decimal("0.00")
        partial_count = 0
        partial_total = Decimal("0.00")

        # Sales logic (mirrors daily_sales route)
        # CRITICAL DEBUG: Fetch sales payments for the date with explicit filtering
        sale_payments = (
            SalePayment.query
            .join(Sale, SalePayment.sale_id == Sale.id)
            .options(
                joinedload(SalePayment.sale).joinedload(Sale.customer),  # type: ignore[arg-type]
                joinedload(SalePayment.sale).joinedload(Sale.items).joinedload(SaleItem.product),  # type: ignore[arg-type]
                joinedload(SalePayment.sale).joinedload(Sale.payments),  # type: ignore[arg-type]
            )
            .filter(
                SalePayment.paid_at.isnot(None),
                func.date(SalePayment.paid_at) == selected_date,
                Sale.status.in_(['PAID', 'PARTIAL']),
            )
            .order_by(SalePayment.paid_at.desc(), SalePayment.id.desc())
            .all()
        )
        
        logger_ctx.debug(f"build_daily_sales_context: found {len(sale_payments)} sale payments for {selected_date}")

        for pay in sale_payments:
            sale = pay.sale
            if not sale:
                continue
            cust_obj = sale.customer
            # convert to displayable string early to avoid <Model ...> repr issues
            if cust_obj:
                cust_name = cust_obj.display_name
            else:
                cust_name = 'Walk-in Customer'

            if (sale.status or "").upper() in ["VOID", "DRAFT"]:
                continue
            amount = Decimal(pay.amount or 0)
            if amount <= 0:
                continue
            desc = ""
            if sale.items:
                desc = ", ".join(
                    f"{it.qty}×{it.product.name if it.product else 'Unknown'}"
                    for it in sale.items
                )

            # Determine partial status using payments within report window
            sale_total = Decimal(sale.total or 0)
            def _payment_within_report(p):
                paid_at = getattr(p, "paid_at", None)
                sale_created_at = getattr(p.sale, "created_at", None) if getattr(p, 'sale', None) else None
                if paid_at:
                    return paid_at <= end_dt
                if sale_created_at:
                    return sale_created_at <= end_dt
                return False

            total_paid_upto = Decimal(sum((p.amount or 0) for p in (sale.payments or []) if _payment_within_report(p)))
            is_partial = total_paid_upto < sale_total
            if is_partial:
                partial_count += 1
                partial_total += amount

            total_payments += amount
            records.append({
                "datetime": pay.paid_at or getattr(pay.sale, 'created_at', None),
                "customer": cust_name,
                "type": "Purchase",
                "description": desc,
                "amount": float(amount),
                "payment_status": "PARTIAL" if is_partial else "PAID",
                "is_partial": is_partial,
                "receipt_id": sale.id,
                "receipt_type": "sale",
            })

        # Repairs logic - MATCHES daily_sales route exactly
        repair_query = (
            Device.query
            .options(joinedload(Device.owner))  # type: ignore[arg-type]
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

        for d in repairs:
            if getattr(d, "charge_waived", False):
                continue
            
            has_deposit = (d.deposit_paid or 0) > 0
            status_upper = (d.payment_status or "").capitalize()
            if (status_upper not in ['Partial', 'Paid']) and not has_deposit:
                continue

            cust = d.owner.display_name if getattr(d, 'owner', None) and d.owner else 'Walk-in Customer'
            desc = d.device_type or 'Repair'

            # SEPARATE TRANSACTION LOGIC: Show deposits and full payments on their respective dates
            
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
                    # Full payment amount = total_cost - deposit_paid
                    full_payment_amount = Decimal(d.total_cost or 0) - Decimal(d.deposit_paid or 0)
            
            # Show deposit if on selected date (as separate transaction)
            if deposit_on_selected:
                amount = Decimal(d.deposit_paid or 0)
                is_partial = True  # Has outstanding balance if not fully paid
                partial_count += 1
                partial_total += amount
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
                    'receipt_type': 'repair'
                })
            
            # Show full payment if on selected date (as separate transaction)
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
                    'receipt_type': 'repair'
                })
            
            # Legacy path: If repair completed on selected date but no deposits/payments on this date, show based on status
            if not deposit_on_selected and not full_payment_on_selected and d.actual_completion == selected_date:
                # Show the repair on its completion date with appropriate status
                if status_upper == 'Paid':
                    amount = Decimal(d.total_cost or 0)
                    is_partial = False
                else:
                    amount = Decimal(d.deposit_paid or 0) if d.deposit_paid and d.deposit_paid > 0 else Decimal(0)
                    is_partial = True if amount > 0 else False
                
                if is_partial or status_upper == 'Paid':
                    if is_partial:
                        partial_count += 1
                        partial_total += amount
                    
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
                        'receipt_type': 'repair'
                    })

        # sort newest first
        records.sort(key=lambda r: r['datetime'], reverse=True)
        
        # CRITICAL DEBUG: Log the final results for diagnostics
        logger_ctx.info(
            f"build_daily_sales_context completed for {selected_date}: "
            f"{len(records)} total records, ₱{total_payments:.2f} total revenue"
        )
        if len(records) == 0:
            logger_ctx.warning(
                f"WARNING: No sales/repair records found for {selected_date}. "
                f"Sale payment count: {len(sale_payments)}"
            )

        return {
            'sales_records': records,
            'total_sales': float(total_payments),
            'total_partial_count': partial_count,
            'total_partial_amount': float(partial_total),
            'report_date': selected_date,
            'today': today_date.isoformat(),
            'now': get_ph_now()
        }
    
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
            'start_date': start_date,
            'end_date': end_date,
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
    def _build_daily_report_data(daily_ctx: Dict, start_date: date, end_date: date, frequency: str) -> Dict:
        """
        Convert daily_sales_context into standardized report_data format for Excel/email.
        
        This ensures daily reports use the exact same transaction logic as the web page.
        
        Args:
            daily_ctx: Output from build_daily_sales_context
            start_date: Report period start
            end_date: Report period end
            frequency: 'daily'
        
        Returns: report_data dict matching generate_report_data format
        """
        sales_records = []
        repair_records = []
        sales_total = Decimal("0.00")
        repair_total = Decimal("0.00")
        
        # Convert daily_ctx sales_records to both formats
        # Keep original records for email, convert to export format for Excel
        all_transactions = daily_ctx.get('sales_records', [])
        
        for rec in all_transactions:
            if rec.get('receipt_type') == 'sale':
                # For Excel export
                sales_records.append({
                    'invoice_number': f"INV-{rec.get('receipt_id', '')}",
                    'customer_name': rec.get('customer', 'Walk-in'),
                    'payment_method': 'Payment',
                    'amount_paid': rec.get('amount', 0),
                    'payment_date': rec.get('datetime', start_date) if isinstance(rec.get('datetime'), date) else start_date,
                    'items_description': rec.get('description', ''),
                    'sale_id': rec.get('receipt_id'),
                    # Keep original for email display
                    '_original': rec
                })
                sales_total += Decimal(str(rec.get('amount', 0)))
            elif rec.get('receipt_type') == 'repair':
                # For Excel export
                repair_records.append({
                    'ticket_number': f"REP-{rec.get('receipt_id', '')}",
                    'customer_name': rec.get('customer', 'Walk-in'),
                    'device_type': rec.get('description', 'Repair'),
                    'payment_method': 'Repair Payment',
                    'amount_paid': rec.get('amount', 0),
                    'payment_date': rec.get('datetime', start_date) if isinstance(rec.get('datetime'), date) else start_date,
                    'payment_status': rec.get('payment_status'),
                    'device_id': rec.get('receipt_id'),
                    # Keep original for email display
                    '_original': rec
                })
                repair_total += Decimal(str(rec.get('amount', 0)))
        
        total_revenue = sales_total + repair_total
        total_transactions = len(sales_records) + len(repair_records)
        
        # Build payment breakdown from daily records
        breakdown = {}
        for rec in all_transactions:
            if rec.get('receipt_type') == 'sale':
                method = 'Sales'
                if method not in breakdown:
                    breakdown[method] = {'count': 0, 'total': 0}
                breakdown[method]['count'] += 1
                breakdown[method]['total'] += rec.get('amount', 0)
        
        # Format date range for display
        if start_date == end_date:
            date_range = start_date.strftime('%B %d, %Y')
        else:
            date_range = f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
        
        return {
            'date_range': date_range,
            'frequency': frequency,
            'start_date': start_date,
            'end_date': end_date,
            'total_revenue': float(total_revenue),
            'total_transactions': total_transactions,
            'total_sales_payments': float(sales_total),
            'total_repair_payments': float(repair_total),
            'payment_breakdown': breakdown,
            'sales_records': sales_records,
            'repair_records': repair_records,
            'all_transactions': all_transactions,  # Keep original for email display
            'report_period': {
                'start': start_date,
                'end': end_date
            }
        }
    
    @staticmethod
    def get_report_period(frequency: str, reference_date: Optional[date] = None) -> Tuple[date, date]:
        """
        Calculate report period based on frequency.
        
        Args:
            frequency: 'daily', 'every_3_days', 'weekly'
            reference_date: Optional reference date (defaults to today)
        
        Returns: (start_date, end_date)
        """
        if reference_date is None:
            reference_date = date.today()
    @staticmethod
    def verify_database_payments(report_date: date) -> Dict:
        """
        Diagnostic function to verify database contains valid payments for date.
        Helps identify why records might be empty.
        
        Args:
            report_date: Date to check
            
        Returns:
            Dict with diagnostic info
        """
        import logging
        logger_diag = logging.getLogger(__name__)
        
        start_dt = datetime.combine(report_date, datetime.min.time())
        end_dt = datetime.combine(report_date, datetime.max.time())
        
        diagnostics = {
            'report_date': report_date,
            'total_sale_payments': 0,
            'sale_payments_in_date_range': 0,
            'sale_payments_with_valid_status': 0,
            'sale_payments_with_positive_amount': 0,
            'total_repair_payments': 0,
            'repair_payments_in_date_range': 0,
            'issues': []
        }
        
        try:
            # Check all SalePayment records
            all_sale_payments = SalePayment.query.count()
            diagnostics['total_sale_payments'] = all_sale_payments
            
            # Get records with paid_at in range
            sale_payments_by_date = (
                SalePayment.query
                .filter(
                    SalePayment.paid_at.isnot(None),
                    func.date(SalePayment.paid_at) == report_date
                )
                .count()
            )
            diagnostics['sale_payments_in_date_range'] = sale_payments_by_date
            
            # Get records with valid sale status
            sale_payments_valid_status = (
                SalePayment.query
                .join(Sale, SalePayment.sale_id == Sale.id)
                .filter(
                    SalePayment.paid_at.isnot(None),
                    func.date(SalePayment.paid_at) == report_date,
                    Sale.status.in_(['PAID', 'PARTIAL'])
                )
                .count()
            )
            diagnostics['sale_payments_with_valid_status'] = sale_payments_valid_status
            
            # Get records with positive amount
            sale_payments_positive = (
                SalePayment.query
                .join(Sale, SalePayment.sale_id == Sale.id)
                .filter(
                    SalePayment.paid_at.isnot(None),
                    func.date(SalePayment.paid_at) == report_date,
                    Sale.status.in_(['PAID', 'PARTIAL']),
                    SalePayment.amount > 0
                )
                .count()
            )
            diagnostics['sale_payments_with_positive_amount'] = sale_payments_positive
            
            # Check Device records
            all_devices = Device.query.count()
            devices_on_date = Device.query.filter(
                Device.actual_completion == report_date
            ).count()
            repair_payments_on_date = Device.query.filter(
                or_(
                    Device.actual_completion == report_date,
                    and_(
                        Device.deposit_paid_at.isnot(None),
                        func.date(Device.deposit_paid_at) == report_date
                    ),
                    and_(
                        Device.full_payment_at.isnot(None),
                        func.date(Device.full_payment_at) == report_date
                    )
                )
            ).count()
            diagnostics['total_repair_payments'] = all_devices
            diagnostics['repair_payments_in_date_range'] = repair_payments_on_date
            
            # Log findings
            if sale_payments_by_date == 0:
                msg = f"No SalePayment records with paid_at = {report_date}"
                diagnostics['issues'].append(msg)
                logger_diag.warning(msg)
            
            if sale_payments_positive == 0 and sale_payments_valid_status > 0:
                msg = f"SalePayment records found but all have amount <= 0"
                diagnostics['issues'].append(msg)
                logger_diag.warning(msg)
            
            logger_diag.info(f"Database verification for {report_date}: {diagnostics}")
            
        except Exception as e:
            diagnostics['issues'].append(f"Query error: {str(e)}")
            logger_diag.error(f"Database verification failed: {e}", exc_info=True)
        
        return diagnostics
    
    @staticmethod
    def get_report_period(frequency: str, reference_date: Optional[date] = None) -> Tuple[date, date]:
        """
        Get start and end dates for report based on frequency.
        
        Args:
            frequency: 'daily', 'every_3_days', 'weekly'
            reference_date: Base date (defaults to today)
        
        Returns:
            (start_date, end_date)
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
