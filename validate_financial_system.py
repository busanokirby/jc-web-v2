"""
Financial Systems - Quick Validation & Testing Guide

Use this script to quickly validate the financial systems are working correctly.
"""

import sys
from datetime import date, datetime, timedelta
from decimal import Decimal

def test_financial_system():
    """Quick validation of financial system"""
    print("=" * 70)
    print("FINANCIAL SYSTEMS - VALIDATION SUITE")
    print("=" * 70)
    
    try:
        from app import create_app
        from app.extensions import db
        from app.services.financial_reconciliation import FinancialReconciliation
        from app.services.integrity_constraints import IntegrityConstraints
        from app.models.sales import Sale, SalePayment
        from app.models.customer import Customer
        from app.services.codes import generate_invoice_no
        
        app = create_app('development')
        
        with app.app_context():
            print("\n✓ App initialized successfully")
            
            # Test 1: Integrity Report
            print("\n" + "=" * 70)
            print("TEST 1: Database Integrity Check")
            print("=" * 70)
            
            report = IntegrityConstraints.generate_integrity_report()
            print(f"  Valid: {report['is_valid']}")
            print(f"  Issues: {len(report['issues'])}")
            print(f"  Orphaned Records: {len(report['orphaned_records'])}")
            print(f"  Sales Count: {report['statistics']['sales_count']}")
            print(f"  Sale Payments Count: {report['statistics']['sale_payments_count']}")
            print(f"  Devices Count: {report['statistics']['devices_count']}")
            
            if not report['is_valid']:
                print("\n  ⚠️  WARNING: Issues found:")
                for issue in report['issues']:
                    print(f"    - {issue}")
            
            if report['orphaned_records']:
                print("\n  ⚠️  WARNING: Orphaned records:")
                print(f"    {report['orphaned_records']}")
            
            # Test 2: Financial Summary
            print("\n" + "=" * 70)
            print("TEST 2: Financial Summary Generation")
            print("=" * 70)
            
            today = date.today()
            summary = FinancialReconciliation.generate_financial_summary(today, today)
            
            print(f"  Period: {today} to {today}")
            print(f"  Revenue Received (Today): ₱{summary['revenue_received']['total']:.2f}")
            print(f"    - Sales: ₱{summary['revenue_received']['sales']:.2f}")
            print(f"    - Repairs: ₱{summary['revenue_received']['repairs']:.2f}")
            print(f"  Revenue Invoiced (Today): ₱{summary['revenue_invoiced']['total']:.2f}")
            print(f"    - Sales: ₱{summary['revenue_invoiced']['sales']:.2f}")
            print(f"    - Repairs: ₱{summary['revenue_invoiced']['repairs']:.2f}")
            print(f"  Total Outstanding (Current): ₱{summary['outstanding']['total_outstanding']:.2f}")
            print(f"    - Pending Sales: ₱{summary['outstanding']['pending_sales']:.2f}")
            print(f"    - Partial Sales: ₱{summary['outstanding']['partial_sales']:.2f}")
            print(f"    - Credit Sales: ₱{summary['outstanding']['credit_sales']:.2f}")
            print(f"    - Pending Repairs: ₱{summary['outstanding']['pending_repairs']:.2f}")
            print(f"    - Partial Repairs: ₱{summary['outstanding']['partial_repairs']:.2f}")
            print(f"    - Credit Repairs: ₱{summary['outstanding']['credit_repairs']:.2f}")
            
            # Test 3: Payment Breakdown
            print("\n" + "=" * 70)
            print("TEST 3: Payment Method Breakdown")
            print("=" * 70)
            
            breakdown = FinancialReconciliation.get_payment_breakdown(today, today)
            if breakdown:
                for method, data in breakdown.items():
                    print(f"  {method}:")
                    print(f"    - Count: {data['count']}")
                    print(f"    - Total: ₱{data['total']:.2f}")
                    print(f"    - Sales: ₱{data.get('sales', 0):.2f}")
                    print(f"    - Repairs: ₱{data.get('repairs', 0):.2f}")
            else:
                print("  (No payments recorded today)")
            
            # Test 4: Sample Transaction Validation
            print("\n" + "=" * 70)
            print("TEST 4: Transaction Validation Rules")
            print("=" * 70)
            
            # Get or create a test customer
            customer = Customer.query.first()
            if not customer:
                customer = Customer(name="System Test", phone="555-0000", customer_code="TEST")
                db.session.add(customer)
                db.session.commit()
                print("  ✓ Created test customer")
            
            # Create test sale
            test_sale = Sale(
                invoice_no=generate_invoice_no(),
                customer_id=customer.id,
                status="PARTIAL",
                total=Decimal("1000.00"),
                created_at=datetime.utcnow()
            )
            db.session.add(test_sale)
            db.session.commit()
            print(f"  ✓ Created test sale: {test_sale.invoice_no}")
            
            # Test validation - positive payment
            valid, msg = IntegrityConstraints.validate_sale_payment(test_sale.id, Decimal("500.00"))
            print(f"  ✓ Positive payment: {'VALID' if valid else f'INVALID - {msg}'}")
            
            # Test validation - negative payment
            valid, msg = IntegrityConstraints.validate_sale_payment(test_sale.id, Decimal("-100.00"))
            expected_invalid = not valid
            print(f"  ✓ Negative payment: {'INVALID (as expected)' if expected_invalid else 'VALID (unexpected!)'}")
            
            # Test validation - overpayment
            valid, msg = IntegrityConstraints.validate_sale_payment(test_sale.id, Decimal("2000.00"))
            expected_invalid = not valid
            print(f"  ✓ Overpayment: {'INVALID (as expected)' if expected_invalid else 'VALID (unexpected!)'}")
            
            # Cleanup
            db.session.delete(test_sale)
            db.session.commit()
            
            # Test 5: Summary Report
            print("\n" + "=" * 70)
            print("TEST 5: Overall System Status")
            print("=" * 70)
            
            if report['is_valid'] and not report['orphaned_records']:
                print("  ✅ SYSTEM HEALTHY - No integrity issues detected")
            else:
                print("  ⚠️  SYSTEM ISSUES - Review above details")
            
            print(f"  Recommendations: {report['recommendations']}")
            
            print("\n" + "=" * 70)
            print("VALIDATION COMPLETE")
            print("=" * 70)
            
            return report['is_valid']
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_financial_system()
    sys.exit(0 if success else 1)
