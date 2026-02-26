"""
Financial Test Suite - Comprehensive ACID-compliance validation.

Tests cover:
- Revenue aggregation (accrual vs cash basis)
- Credit handling (sales and repairs)
- Partial payment lifecycle
- Double-counting prevention
- Edge cases (voids, waived charges, orphaned records)
- Database integrity constraints
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.extensions import db
from app.models.sales import Sale, SaleItem, SalePayment
from app.models.repair import Device, RepairPartUsed
from app.models.repair_payment import RepairPayment
from app.models.inventory import Product
from app.models.customer import Customer
from app.services.financial_reconciliation import FinancialReconciliation
from app.services.integrity_constraints import IntegrityConstraints
from app.services.codes import generate_invoice_no


class TestFinancialReconciliation:
    """Test unified financial aggregation service"""

    @pytest.fixture
    def customer(self):
        """Create test customer"""
        c = Customer(name="Test Customer", phone="555-0001", customer_code="CUST001")
        db.session.add(c)
        db.session.commit()
        return c

    @pytest.fixture
    def product(self):
        """Create test product"""
        p = Product(name="Test Product", sku="TEST-001", category_id=None, 
                   sell_price=Decimal("100.00"), cost_price=Decimal("50.00"),
                   stock_on_hand=100, is_service=False, is_active=True)
        db.session.add(p)
        db.session.commit()
        return p

    def test_sales_revenue_received_basic(self, customer, product):
        """Test basic sales revenue aggregation"""
        today = date.today()
        
        # Create sale with payment
        sale = Sale(
            invoice_no=generate_invoice_no(),
            customer_id=customer.id,
            status="PAID",
            total=Decimal("1000.00"),
            created_at=datetime.combine(today, datetime.min.time())
        )
        db.session.add(sale)
        db.session.flush()
        
        payment = SalePayment(
            sale_id=sale.id,
            amount=Decimal("1000.00"),
            method="Cash",
            paid_at=datetime.combine(today, datetime.min.time())
        )
        db.session.add(payment)
        db.session.commit()
        
        # Test aggregation
        total, count, records = FinancialReconciliation.get_sales_revenue_received(today, today)
        
        assert total == Decimal("1000.00"), "Should aggregate payment amount"
        assert count == 1, "Should count 1 transaction"
        assert len(records) == 1, "Should return 1 record"

    def test_sales_revenue_excludes_credits(self, customer):
        """Test that credit sales are excluded from revenue"""
        today = date.today()
        
        # Create sale marked as credit
        sale = Sale(
            invoice_no=generate_invoice_no(),
            customer_id=customer.id,
            status="PARTIAL",
            total=Decimal("500.00"),
            claimed_on_credit=True,
            created_at=datetime.combine(today, datetime.min.time())
        )
        db.session.add(sale)
        db.session.commit()
        
        # Test aggregation
        total, count, records = FinancialReconciliation.get_sales_revenue_received(today, today)
        
        assert total == Decimal("0.00"), "Should exclude credit sales"
        assert count == 0, "Should not count credit sales"

    def test_sales_revenue_excludes_negative_amounts(self, customer):
        """Test that negative payments (refunds) are excluded"""
        today = date.today()
        
        sale = Sale(
            invoice_no=generate_invoice_no(),
            customer_id=customer.id,
            status="PAID",
            total=Decimal("100.00"),
            created_at=datetime.combine(today, datetime.min.time())
        )
        db.session.add(sale)
        db.session.flush()
        
        # Add negative payment (should be excluded)
        payment = SalePayment(
            sale_id=sale.id,
            amount=Decimal("-50.00"),  # Refund
            method="Cash",
            paid_at=datetime.combine(today, datetime.min.time())
        )
        db.session.add(payment)
        db.session.commit()
        
        total, count, records = FinancialReconciliation.get_sales_revenue_received(today, today)
        
        assert total == Decimal("0.00"), "Should exclude negative payments"
        assert count == 0, "Should not count negative payments"

    def test_repair_revenue_received_legacy(self, customer):
        """Test repair revenue aggregation from Device.deposit_paid_at"""
        today = date.today()
        
        device = Device(
            ticket_number="JC-2024-001",
            customer_id=customer.id,
            device_type="Laptop",
            issue_description="Test issue",
            total_cost=Decimal("500.00"),
            deposit_paid=Decimal("250.00"),
            deposit_paid_at=datetime.combine(today, datetime.min.time()),
            payment_status="Partial"
        )
        db.session.add(device)
        db.session.commit()
        
        total, count, records = FinancialReconciliation.get_repair_revenue_received(today, today)
        
        assert total == Decimal("250.00"), "Should aggregate repair deposits"
        assert count == 1, "Should count 1 repair transaction"

    def test_repair_revenue_excludes_credits(self, customer):
        """Test that credit repairs are excluded"""
        today = date.today()
        
        device = Device(
            ticket_number="JC-2024-002",
            customer_id=customer.id,
            device_type="Laptop",
            issue_description="Test issue",
            total_cost=Decimal("500.00"),
            deposit_paid=Decimal("0.00"),
            claimed_on_credit=True
        )
        db.session.add(device)
        db.session.commit()
        
        total, count, records = FinancialReconciliation.get_repair_revenue_received(today, today)
        
        assert total == Decimal("0.00"), "Should exclude credit repairs"
        assert count == 0, "Should not count credit repairs"

    def test_partial_payment_aggregation(self, customer):
        """Test partial payment tracking"""
        today = date.today()
        
        # Create sale with partial payment
        sale = Sale(
            invoice_no=generate_invoice_no(),
            customer_id=customer.id,
            status="PARTIAL",
            total=Decimal("1000.00"),
            created_at=datetime.combine(today, datetime.min.time())
        )
        db.session.add(sale)
        db.session.flush()
        
        # Payment 1
        p1 = SalePayment(
            sale_id=sale.id,
            amount=Decimal("400.00"),
            method="Cash",
            paid_at=datetime.combine(today, datetime.min.time())
        )
        db.session.add(p1)
        
        # Payment 2 (next day)
        p2 = SalePayment(
            sale_id=sale.id,
            amount=Decimal("600.00"),
            method="GCash",
            paid_at=datetime.combine(today + timedelta(days=1), datetime.min.time())
        )
        db.session.add(p2)
        db.session.commit()
        
        # Test today only
        total_today, count_today, _ = FinancialReconciliation.get_sales_revenue_received(today, today)
        assert total_today == Decimal("400.00"), "Should only count today's payment"
        
        # Test both days
        total_both, count_both, _ = FinancialReconciliation.get_sales_revenue_received(
            today, today + timedelta(days=1)
        )
        assert total_both == Decimal("1000.00"), "Should aggregate both payments"

    def test_revenue_invoiced_vs_received(self, customer):
        """Test distinction between invoiced (accrual) and received (cash)"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Create sale yesterday
        sale = Sale(
            invoice_no=generate_invoice_no(),
            customer_id=customer.id,
            status="PARTIAL",
            total=Decimal("1000.00"),
            created_at=datetime.combine(yesterday, datetime.min.time())
        )
        db.session.add(sale)
        db.session.flush()
        
        # Payment received today
        payment = SalePayment(
            sale_id=sale.id,
            amount=Decimal("1000.00"),
            method="Cash",
            paid_at=datetime.combine(today, datetime.min.time())
        )
        db.session.add(payment)
        db.session.commit()
        
        # Yesterday: invoiced but not received
        sales_inv_y, _, _ = FinancialReconciliation.get_revenue_invoiced(yesterday, yesterday)
        sales_rec_y, _, _ = FinancialReconciliation.get_sales_revenue_received(yesterday, yesterday)
        assert sales_inv_y == Decimal("1000.00"), "Should show invoiced total"
        assert sales_rec_y == Decimal("0.00"), "Should not show payment from future"
        
        # Today: received but not invoiced
        sales_inv_t, _, _ = FinancialReconciliation.get_revenue_invoiced(today, today)
        sales_rec_t, _, _ = FinancialReconciliation.get_sales_revenue_received(today, today)
        assert sales_inv_t == Decimal("0.00"), "Should not show invoiced from past"
        assert sales_rec_t == Decimal("1000.00"), "Should show received today"

    def test_outstanding_by_status(self, customer):
        """Test outstanding breakdown by status"""
        # Pending sale
        pending_sale = Sale(
            invoice_no=generate_invoice_no(),
            customer_id=customer.id,
            status="PARTIAL",
            total=Decimal("500.00"),
            created_at=datetime.utcnow()
        )
        db.session.add(pending_sale)
        
        # Partial sale (some payment)
        partial_sale = Sale(
            invoice_no=generate_invoice_no(),
            customer_id=customer.id,
            status="PARTIAL",
            total=Decimal("1000.00"),
            created_at=datetime.utcnow()
        )
        db.session.add(partial_sale)
        db.session.flush()
        
        payment = SalePayment(
            sale_id=partial_sale.id,
            amount=Decimal("400.00"),
            method="Cash",
            paid_at=datetime.utcnow()
        )
        db.session.add(payment)
        
        # Credit sale
        credit_sale = Sale(
            invoice_no=generate_invoice_no(),
            customer_id=customer.id,
            status="PARTIAL",
            total=Decimal("300.00"),
            claimed_on_credit=True,
            created_at=datetime.utcnow()
        )
        db.session.add(credit_sale)
        db.session.commit()
        
        # Get outstanding
        outstanding = FinancialReconciliation.get_outstanding_by_status()
        
        assert outstanding['pending_sales'] == Decimal("500.00"), "Should track pending sales"
        assert outstanding['sales_balance_due'] == Decimal("900.00"), "Should consolidate partial (600) + credit (300)"

    def test_no_double_counting(self, customer):
        """Test that transactions aren't double-counted across modules"""
        today = date.today()
        
        sale = Sale(
            invoice_no=generate_invoice_no(),
            customer_id=customer.id,
            status="PAID",
            total=Decimal("1000.00"),
            created_at=datetime.combine(today, datetime.min.time())
        )
        db.session.add(sale)
        db.session.flush()
        
        payment = SalePayment(
            sale_id=sale.id,
            amount=Decimal("1000.00"),
            method="Cash",
            paid_at=datetime.combine(today, datetime.min.time())
        )
        db.session.add(payment)
        db.session.commit()
        
        # Get comprehensive report
        summary = FinancialReconciliation.generate_financial_summary(today, today)
        
        # Should only count payment once
        assert summary['revenue_received']['sales'] == 1000.00, "Sales should have 1000"
        assert summary['revenue_received']['repairs'] == 0.00, "Repairs should have 0"
        assert summary['revenue_received']['total'] == 1000.00, "Total should be 1000 (not 2000)"


class TestIntegrityConstraints:
    """Test database integrity validation"""

    @pytest.fixture
    def customer(self):
        """Create test customer"""
        c = Customer(name="Test Customer", phone="555-0001", customer_code="CUST001")
        db.session.add(c)
        db.session.commit()
        return c

    def test_validate_sale_payment_positive_only(self, customer):
        """Test that negative payments are rejected"""
        sale = Sale(
            invoice_no=generate_invoice_no(),
            customer_id=customer.id,
            total=Decimal("100.00"),
            created_at=datetime.utcnow()
        )
        db.session.add(sale)
        db.session.commit()
        
        valid, msg = IntegrityConstraints.validate_sale_payment(sale.id, Decimal("-50.00"))
        
        assert not valid, "Should reject negative payment"
        assert "positive" in msg.lower(), "Error message should mention positive"

    def test_validate_sale_payment_not_exceed_total(self, customer):
        """Test that overpayments are detected"""
        sale = Sale(
            invoice_no=generate_invoice_no(),
            customer_id=customer.id,
            total=Decimal("100.00"),
            created_at=datetime.utcnow()
        )
        db.session.add(sale)
        db.session.commit()
        
        # Try to pay more than 5% overage
        valid, msg = IntegrityConstraints.validate_sale_payment(sale.id, Decimal("200.00"))
        
        assert not valid, "Should reject overpayment"

    def test_validate_repair_payment_valid(self, customer):
        """Test valid repair payment validation"""
        device = Device(
            ticket_number="JC-2024-001",
            customer_id=customer.id,
            device_type="Laptop",
            issue_description="Test",
            total_cost=Decimal("500.00")
        )
        db.session.add(device)
        db.session.commit()
        
        valid, msg = IntegrityConstraints.validate_repair_payment(device.id, Decimal("250.00"))
        
        assert valid, "Should accept valid repair payment"
        assert msg is None, "Should have no error message"

    def test_integrity_report_generation(self):
        """Test integrity report generation"""
        report = IntegrityConstraints.generate_integrity_report()
        
        assert 'is_valid' in report
        assert 'issues' in report
        assert 'orphaned_records' in report
        assert 'statistics' in report
        assert 'recommendations' in report


class TestEdgeCases:
    """Test edge cases and special scenarios"""

    @pytest.fixture
    def customer(self):
        """Create test customer"""
        c = Customer(name="Test Customer", phone="555-0001", customer_code="CUST001")
        db.session.add(c)
        db.session.commit()
        return c

    def test_void_sales_excluded(self, customer):
        """Test that void sales are excluded from revenue"""
        today = date.today()
        
        void_sale = Sale(
            invoice_no=generate_invoice_no(),
            customer_id=customer.id,
            status="VOID",
            total=Decimal("1000.00"),
            created_at=datetime.combine(today, datetime.min.time())
        )
        db.session.add(void_sale)
        db.session.flush()
        
        # Try to add payment (should be invalid)
        valid, msg = IntegrityConstraints.validate_sale_payment(void_sale.id, Decimal("500.00"))
        
        assert not valid, "Should not allow payments on void sales"

    def test_waived_repair_no_payment(self, customer):
        """Test that waived repairs cannot receive payments"""
        device = Device(
            ticket_number="JC-2024-001",
            customer_id=customer.id,
            device_type="Laptop",
            issue_description="Test",
            total_cost=Decimal("500.00"),
            charge_waived=True
        )
        db.session.add(device)
        db.session.commit()
        
        valid, msg = IntegrityConstraints.validate_repair_payment(device.id, Decimal("100.00"))
        
        assert not valid, "Should reject payment on waived repair"

    def test_mixed_transaction_no_double_count(self, customer):
        """Test that mixed sales/repair transactions don't double-count"""
        today = date.today()
        
        # Create sale
        sale = Sale(
            invoice_no=generate_invoice_no(),
            customer_id=customer.id,
            status="PAID",
            total=Decimal("500.00"),
            created_at=datetime.combine(today, datetime.min.time())
        )
        db.session.add(sale)
        db.session.flush()
        
        sp = SalePayment(
            sale_id=sale.id,
            amount=Decimal("500.00"),
            paid_at=datetime.combine(today, datetime.min.time())
        )
        db.session.add(sp)
        
        # Create repair
        device = Device(
            ticket_number="JC-2024-001",
            customer_id=customer.id,
            device_type="Laptop",
            issue_description="Test",
            total_cost=Decimal("300.00"),
            deposit_paid=Decimal("300.00"),
            deposit_paid_at=datetime.combine(today, datetime.min.time()),
            payment_status="Paid"
        )
        db.session.add(device)
        db.session.commit()
        
        summary = FinancialReconciliation.generate_financial_summary(today, today)
        
        # Should be 500 + 300 = 800, not double-counted
        assert summary['revenue_received']['total'] == 800.00, "Should aggregate correctly"

    def test_zero_amount_transactions_excluded(self, customer):
        """Test that zero-amount transactions are excluded"""
        today = date.today()
        
        sale = Sale(
            invoice_no=generate_invoice_no(),
            customer_id=customer.id,
            status="PAID",
            total=Decimal("100.00"),
            created_at=datetime.combine(today, datetime.min.time())
        )
        db.session.add(sale)
        db.session.flush()
        
        # Zero payment
        payment = SalePayment(
            sale_id=sale.id,
            amount=Decimal("0.00"),
            paid_at=datetime.combine(today, datetime.min.time())
        )
        db.session.add(payment)
        db.session.commit()
        
        total, count, records = FinancialReconciliation.get_sales_revenue_received(today, today)
        
        assert count == 0, "Should exclude zero payments"


# Module-level pytest fixtures
@pytest.fixture(scope="module")
def app_context():
    """Create app context for testing"""
    from app import create_app
    app = create_app('testing')
    with app.app_context():
        yield app
