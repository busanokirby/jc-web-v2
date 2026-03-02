#!/usr/bin/env python3
"""
Diagnostic script for testing the SMTP email service functionality.

This script:
1. Verifies database connectivity and data
2. Tests the report generation pipeline
3. Validates email template rendering
4. Identifies data format issues

Usage:
    python test_email_service_diagnostics.py
"""

import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_and_report_generation():
    """Test report generation and data formatting"""
    print("\n" + "="*80)
    print("EMAIL SERVICE DIAGNOSTICS")
    print("="*80)
    
    # Initialize Flask app
    try:
        from app import create_app
        from app.extensions import db
        from app.models.sales import SalePayment, Sale
        from app.models.email_config import SMTPSettings
        from app.services.report_service import ReportService
        from app.services.email_service import EmailService
        
        app = create_app()
        with app.app_context():
            
            # Test 1: Check database connectivity
            print("\n[TEST 1] Database Connectivity")
            print("-" * 40)
            try:
                total_sales = Sale.query.count()
                total_payments = SalePayment.query.count()
                print(f"✓ Database connected")
                print(f"  - Total Sales: {total_sales}")
                print(f"  - Total SalePayments: {total_payments}")
            except Exception as e:
                print(f"✗ Database error: {e}")
                return False
            
            # Test 2: Check SMTP configuration
            print("\n[TEST 2] SMTP Configuration")
            print("-" * 40)
            smtp_config = SMTPSettings.get_active_config()
            if smtp_config:
                print(f"✓ SMTP config found")
                print(f"  - Server: {smtp_config.smtp_server}:{smtp_config.smtp_port}")
                print(f"  - Email: {smtp_config.email_address}")
                print(f"  - Enabled: {smtp_config.is_enabled}")
                print(f"  - Recipients: {smtp_config.get_recipients()}")
                print(f"  - Frequency: {smtp_config.frequency}")
            else:
                print("✗ No SMTP config found")
            
            # Test 3: Database verification for today
            print("\n[TEST 3] Database Verification for Today")
            print("-" * 40)
            today = date.today()
            diag = ReportService.verify_database_payments(today)
            print(f"Report date: {diag['report_date']}")
            print(f"Total SalePayments in DB: {diag['total_sale_payments']}")
            print(f"Payments with paid_at on date: {diag['sale_payments_in_date_range']}")
            print(f"Payments with valid Sale status: {diag['sale_payments_with_valid_status']}")
            print(f"Payments with positive amount: {diag['sale_payments_with_positive_amount']}")
            if diag['issues']:
                print(f"⚠ Issues detected:")
                for issue in diag['issues']:
                    print(f"  - {issue}")
            else:
                print(f"✓ No issues detected")
            
            # Test 4: Build daily context
            print("\n[TEST 4] Build Daily Sales Context")
            print("-" * 40)
            daily_ctx = ReportService.build_daily_sales_context(today)
            sales_records = daily_ctx.get('sales_records', [])
            print(f"Records returned: {len(sales_records)}")
            print(f"Total sales: ₱{daily_ctx.get('total_sales', 0):.2f}")
            print(f"Partial payments: {daily_ctx.get('total_partial_count', 0)}")
            
            if sales_records:
                print(f"\nFirst record sample:")
                rec = sales_records[0]
                for key, value in rec.items():
                    print(f"  - {key}: {value}")
            else:
                print("⚠ No records returned! Checking for recent sales...")
                
                # Check for recent sales
                recent_sales = Sale.query.order_by(Sale.created_at.desc()).limit(5).all()
                if recent_sales:
                    print(f"Recent sales in database: {len(recent_sales)}")
                    for sale in recent_sales:
                        print(f"  - {sale.invoice_no}: status={sale.status}, total={sale.total}")
                        payments = SalePayment.query.filter_by(sale_id=sale.id).all()
                        for p in payments:
                            print(f"    - Payment: ₱{p.amount}, paid_at={p.paid_at}")
                else:
                    print("No recent sales found in database")
            
            # Test 5: Build report data
            print("\n[TEST 5] Build Report Data for Email")
            print("-" * 40)
            report_data = ReportService._build_daily_report_data(daily_ctx, today, today, 'daily')
            print(f"Report data keys: {list(report_data.keys())}")
            print(f"Total revenue: ₱{report_data.get('total_revenue', 0):.2f}")
            print(f"Total transactions: {report_data.get('total_transactions', 0)}")
            print(f"All transactions: {len(report_data.get('all_transactions', []))}")
            
            # Test 6: Prepare email records
            print("\n[TEST 6] Prepare Email Records")
            print("-" * 40)
            display_records = EmailService._prepare_email_records(report_data)
            print(f"Display records prepared: {len(display_records)}")
            
            if display_records:
                print(f"Display record keys: {list(display_records[0].keys())}")
                print(f"First record sample:")
                rec = display_records[0]
                for key in ['customer', 'type', 'amount', 'is_partial', 'receipt_type']:
                    if key in rec:
                        print(f"  - {key}: {rec[key]}")
            else:
                print("⚠ No display records prepared")
            
            # Test 7: Generate HTML body
            print("\n[TEST 7] Generate HTML Email Body")
            print("-" * 40)
            try:
                html_body = EmailService.generate_html_body(report_data, smtp_config)
                print(f"✓ HTML body generated")
                print(f"  - Length: {len(html_body)} characters")
                
                # Check for content
                if "No sales records found" in html_body:
                    print("  ⚠ Email contains 'No sales records found' message")
                elif "<tr>" in html_body:
                    # Count table rows
                    row_count = html_body.count("<tr>")
                    print(f"  - Table rows: {row_count}")
                else:
                    print("  ⚠ No table rows found in HTML")
                
                # Save HTML for inspection
                html_file = "email_output_test.html"
                with open(html_file, 'w') as f:
                    f.write(html_body)
                print(f"  - Saved to: {html_file}")
                
            except Exception as e:
                print(f"✗ Error generating HTML: {e}")
                import traceback
                traceback.print_exc()
            
            # Test 8: Summary and recommendations
            print("\n[TEST 8] Summary and Recommendations")
            print("-" * 40)
            
            if not sales_records:
                print("⚠ ISSUE: No sales records found for today")
                print("\nPossible causes:")
                print("1. No SalePayment records with paid_at = today")
                print("2. All sales have status other than PAID or PARTIAL")
                print("3. All payments have amount <= 0")
                print("4. Database contains no sales for today")
                print("\nRecommendations:")
                print("1. Check the database directly for SalePayment records")
                print("2. Verify sale status values (should be PAID or PARTIAL)")
                print("3. Create test sales with today's date to verify the system")
                print("4. Check application logging for detailed error messages")
            else:
                print(f"✓ SUCCESS: {len(sales_records)} records found and formatted correctly")
                print("\nThe email service should work correctly.")
            
            print("\n" + "="*80)
            print("DIAGNOSTICS COMPLETE")
            print("="*80 + "\n")
            
            return True
            
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're running this script from the app root directory")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_database_and_report_generation()
    sys.exit(0 if success else 1)
