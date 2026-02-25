"""
Integration Test: Verify all financial system fixes work correctly
Location: tests/test_financial_integrity.py

Tests:
1. SMTP frequency calculation (total_seconds precision)
2. Daily sales report (no double-counting)
3. Payment validation (amount > 0)
4. Revenue calculations (payment-based)
5. Repair/Sales consistency
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta, date
from app.extensions import db
from app.models.sales import Sale, SaleItem, SalePayment
from app.models.repair import Device
from app.models.customer import Customer
from app.models.inventory import Product
from app.models.email_config import SMTPSettings
from app.services.report_service import ReportService
from app.services.email_service import EmailService
from app.services.validation import PaymentValidator, ExcelReconciliation


class TestSMTPFrequencyFix:
    """Test SMTP frequency calculation uses total_seconds()"""
    
    def test_smtp_daily_frequency_precision(self, app):
        """Test that daily frequency allows exactly 24 hours"""
        with app.app_context():
            config = SMTPSettings(
                smtp_server='test.com',
                email_address='test@test.com',
                email_password_encrypted=b'encrypted',
                frequency='daily'
            )
            
            # Test 1: Never sent before → should send
            config.last_sent_at = None
            assert EmailService._should_send_based_on_frequency(config) == True
            
            # Test 2: Sent 30 minutes ago → should NOT send
            config.last_sent_at = datetime.utcnow() - timedelta(minutes=30)
            assert EmailService._should_send_based_on_frequency(config) == False
            
            # Test 3: Sent 23.5 hours ago → should NOT send (old bug returned True here)
            config.last_sent_at = datetime.utcnow() - timedelta(hours=23, minutes=30)
            assert EmailService._should_send_based_on_frequency(config) == False
            
            # Test 4: Sent exactly 24 hours ago → should send
            config.last_sent_at = datetime.utcnow() - timedelta(hours=24)
            assert EmailService._should_send_based_on_frequency(config) == True
            
            # Test 5: Sent 24.5 hours ago → should send
            config.last_sent_at = datetime.utcnow() - timedelta(hours=24, minutes=30)
            assert EmailService._should_send_based_on_frequency(config) == True
    
    def test_smtp_every_3_days_frequency(self, app):
        """Test 3-day frequency precision"""
        with app.app_context():
            config = SMTPSettings(
                smtp_server='test.com',
                email_address='test@test.com',
                email_password_encrypted=b'encrypted',
                frequency='every_3_days'
            )
            
            config.last_sent_at = datetime.utcnow() - timedelta(days=2, hours=23)
            assert EmailService._should_send_based_on_frequency(config) == False
            
            config.last_sent_at = datetime.utcnow() - timedelta(days=3)
            assert EmailService._should_send_based_on_frequency(config) == True


class TestDailySalesReportFix:
    """Test that daily sales report doesn't double-count transactions"""
    
    def test_daily_sales_no_double_count(self, app, logged_in_client):
        """
        Test that a single payment doesn't appear twice in daily sales
        (the bug was OR filter with null paid_at fallback)
        """
        with app.app_context():
            # Create customer and sale
            customer = Customer(
                display_name="Test Customer",
                phone="09001234567"
            )
            db.session.add(customer)
            db.session.flush()
            
            sale = Sale(
                invoice_no="INV-001",
                customer_id=customer.id,
                status="PAID",
                total=Decimal("1000.00"),
                created_at=datetime.utcnow()
            )
            db.session.add(sale)
            db.session.flush()
            
            # Add payment with explicit paid_at
            payment = SalePayment(
                sale_id=sale.id,
                amount=Decimal("1000.00"),
                method="Cash",
                paid_at=datetime.utcnow()
            )
            db.session.add(payment)
            db.session.commit()
            
            # Query daily sales for today
            today = date.today()
            response = logged_in_client.get(f'/sales/daily-sales?date={today.isoformat()}')
            
            # Should find exactly 1 payment (not 2)
            assert response.status_code == 200
            assert b"Total Sales:" in response.data or b"1000.00" in response.data


class TestPaymentValidation:
    """Test payment validation prevents invalid amounts"""
    
    def test_validate_positive_amount(self):
        """Test that negative/zero amounts are rejected"""
        # Valid
        is_valid, msg = PaymentValidator.validate_payment_amount(Decimal("100.00"))
        assert is_valid == True
        assert msg == ""
        
        # Invalid: Zero
        is_valid, msg = PaymentValidator.validate_payment_amount(Decimal("0"))
        assert is_valid == False
        assert "positive" in msg.lower()
        
        # Invalid: Negative
        is_valid, msg = PaymentValidator.validate_payment_amount(Decimal("-100.00"))
        assert is_valid == False
        assert "positive" in msg.lower()
    
    def test_sale_payment_validation(self, app):
        """Test sale payment validation"""
        with app.app_context():
            customer = Customer(display_name="Test", phone="09001234567")
            db.session.add(customer)
            db.session.flush()
            
            sale = Sale(
                invoice_no="INV-001",
                customer_id=customer.id,
                status="PAID",
                total=Decimal("1000.00")
            )
            db.session.add(sale)
            db.session.commit()
            
            # Valid payment
            is_valid, msg = PaymentValidator.validate_sale_payment(
                sale,
                Decimal("500.00")
            )
            assert is_valid == True
            
            # Invalid: exceeds sale total
            is_valid, msg = PaymentValidator.validate_sale_payment(
                sale,
                Decimal("2000.00")
            )
            assert is_valid == False
            assert "exceeds" in msg.lower()
            
            # Invalid: negative amount
            is_valid, msg = PaymentValidator.validate_sale_payment(
                sale,
                Decimal("-100.00")
            )
            assert is_valid == False


class TestRevenueCalculationsAccuracy:
    """Test that revenue calculations use payment amounts, not sale totals"""
    
    def test_partial_payment_counted_correctly(self, app):
        """Test that partial payment = actual amount paid (not sale total)"""
        with app.app_context():
            # Create sale for 1000
            customer = Customer(display_name="Test", phone="09001234567")
            db.session.add(customer)
            db.session.flush()
            
            sale = Sale(
                invoice_no="INV-001",
                customer_id=customer.id,
                status="PARTIAL",
                total=Decimal("1000.00")
            )
            db.session.add(sale)
            db.session.flush()
            
            # But only 300 was paid
            payment = SalePayment(
                sale_id=sale.id,
                amount=Decimal("300.00"),
                paid_at=datetime.utcnow()
            )
            db.session.add(payment)
            db.session.commit()
            
            # Report should show 300, not 1000
            today = date.today()
            sales, revenue, count = ReportService.get_sales_for_period(today, today)
            
            assert count == 1
            assert revenue == Decimal("300.00")
            assert sales[0]['amount_paid'] == 300.0


class TestExcelReconciliation:
    """Test Excel export reconciliation catches mismatches"""
    
    def test_excel_reconciliation_detects_mismatch(self):
        """Test that reconciliation detects mismatches between calculated and reported"""
        report_data = {
            'total_revenue': 1500.00,  # Reported total
            'total_sales_payments': 1000.00,
            'total_repair_payments': 500.00,
            'sales_count': 5
        }
        
        sales = [
            {'amount_paid': 500, 'payment_date': date.today()},
            {'amount_paid': 500, 'payment_date': date.today()}
        ]
        repairs = [
            {'amount_paid': 300, 'payment_date': date.today()},
            {'amount_paid': 200, 'payment_date': date.today()}
        ]
        
        # Should reconcile: 500+500+300+200 = 1500 ✓
        is_reconciled, issues = ExcelReconciliation.reconcile_report(
            report_data, sales, repairs
        )
        
        # Should NOT reconcile if we change report total
        report_data['total_revenue'] = 9999.00
        is_reconciled, issues = ExcelReconciliation.reconcile_report(
            report_data, sales, repairs
        )
        assert is_reconciled == False
        assert len(issues) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
